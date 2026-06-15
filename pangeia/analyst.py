from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import httpx

API_BASE_URL = os.environ.get("PANGEIA_API_URL", "http://localhost:8000")
HTTP_TIMEOUT = 30.0

LLM_PROVIDER: Literal["ollama", "gemini"] = os.environ.get("LLM_PROVIDER", "gemini")  # type: ignore[assignment]
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

SYSTEM_PROMPT = """You are the Pangeia Analyst, a specialized intelligence agent for the Pangeia civilization simulator.

You receive structured JSON data from an active simulation and answer questions about the civilization's state, dynamics, risks, and trajectories.

Your analysis must:
- Ground every claim in the simulation data provided
- Identify non-obvious patterns and emergent dynamics
- Flag risks and instabilities with estimated severity (Low/Medium/High/Critical)
- Distinguish correlation from causation when possible
- Produce structured Markdown reports with clear sections

Report structure:
## Executive Summary
## Current State (tick N)
## Analysis
## Identified Risks
## Projections (next 50 ticks)
## Recommendations
## Data Sources Used

Be precise about what the data shows vs what you are inferring.
Use [DATA] tag for direct observations, [INFERENCE] for reasoning."""


_ENDPOINTS = [
    "/status",
    "/summary",
    "/economy",
    "/metrics/history?n=50",
    "/governance",
    "/culture",
    "/ideologies",
    "/civilization",
    "/collective_memory",
    "/collective_memory/myths",
    "/collective_memory/volatility",
    "/technology",
    "/technology/tree",
    "/diplomacy",
    "/stratification",
    "/news/latest?n=20",
]


class PangeiaContext:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=HTTP_TIMEOUT)

    async def _fetch_one(self, path: str) -> tuple[str, Any]:
        try:
            resp = await self.client.get(path)
            if resp.status_code >= 400:
                return path, {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            return path, resp.json()
        except httpx.TimeoutException:
            return path, {"error": "timeout"}
        except httpx.ConnectError:
            return path, {"error": "connection_refused"}
        except Exception as e:
            return path, {"error": str(e)}

    async def collect(self) -> dict[str, Any]:
        results = await asyncio.gather(*[self._fetch_one(ep) for ep in _ENDPOINTS])
        data: dict[str, Any] = {}
        for path, value in results:
            key = path.split("?")[0].lstrip("/").replace("/", "_").replace("-", "_") or "root"
            data[key] = value

        sim_offline = any(
            isinstance(data.get(k), dict) and data[k].get("error") == "connection_refused"
            for k in data
        )
        data["simulation_offline"] = sim_offline

        status = data.get("status", {})
        tick = status.get("tick", 0) if isinstance(status, dict) else 0
        data["_tick"] = tick
        return data

    async def close(self):
        await self.client.aclose()


class ReportWriter:
    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)

    def save(self, question: str, report: str, tick: int) -> Path:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        words = question.lower().split()[:5]
        slug = "_".join(w.strip(".,!?;:()[]\"'") for w in words if w.strip(".,!?;:()[]\"'"))
        filename = f"{now}_tick{tick}_{slug}.md"
        path = self.reports_dir / filename
        path.write_text(report, encoding="utf-8")
        return path

    @staticmethod
    def print_report(report: str):
        sep = "─" * 60
        print(f"\n{sep}")
        print(report)
        print(f"{sep}")


class PangeiaAnalyst:
    def __init__(self):
        self.context = PangeiaContext()
        self.last_tick: int = 0

    async def _call_ollama(self, user_message: str) -> str:
        import ollama as _ollama
        async_client = _ollama.AsyncClient(host=OLLAMA_BASE_URL)
        response = await async_client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            options={"num_predict": 4000},
        )
        return response["message"]["content"]

    async def analyze(self, question: str) -> str:
        context_data = await self.context.collect()
        self.last_tick = context_data.get("_tick", 0)

        user_message = (
            f"Question: {question}\n\n"
            f"Simulation data (collected at tick {self.last_tick}):\n"
            f"{json.dumps(context_data, indent=2, ensure_ascii=False)}\n\n"
            f"Produce a complete analysis report in Markdown.\n"
            f"If the data suggests the simulation is not running, say so clearly\n"
            f"and explain what data would be needed to answer the question."
        )

        if LLM_PROVIDER == "ollama":
            return await self._call_ollama(user_message)

        if not os.environ.get("GEMINI_API_KEY"):
            raise EnvironmentError(
                "Set GEMINI_API_KEY environment variable. "
                "Get your key at https://aistudio.google.com/apikey"
            )

        from google import genai
        from google.genai import types as genai_types

        client = genai.Client()

        response = await asyncio.to_thread(
            client.models.generate_content,
            model=GEMINI_MODEL,
            config=genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=4000,
                temperature=0.3,
            ),
            contents=user_message,
        )
        return response.text


async def main():
    if len(sys.argv) < 2:
        print("Usage: python -m pangeia.analyst \"sua pergunta aqui\"")
        sys.exit(1)

    question = " ".join(sys.argv[1:])

    print("Pangeia Analyst")
    print(f"Provider: {LLM_PROVIDER}")
    print(f"Question: {question}")
    print("Collecting simulation context...")

    analyst = PangeiaAnalyst()
    try:
        report = await analyst.analyze(question)
        writer = ReportWriter()
        path = writer.save(question, report, tick=analyst.last_tick)
        writer.print_report(report)
        print(f"Report saved: {path}")
    finally:
        await analyst.context.close()


if __name__ == "__main__":
    asyncio.run(main())
