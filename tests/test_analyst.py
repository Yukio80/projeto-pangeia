from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock, ANY

import pytest
import httpx

from pangeia.analyst import (
    PangeiaContext,
    PangeiaAnalyst,
    ReportWriter,
    main,
    _ENDPOINTS,
)


# ─── Sample data ───────────────────────────────────────────────

SAMPLE_STATUS = {"running": True, "tick": 150, "alive_count": 280, "dead_count": 20, "agent_count": 300}
SAMPLE_SUMMARY = {"tick": 150, "economy": {"gdp": 15000}, "governance": {"stability": 0.72}, "technology": {"era": "Industrial"}}
SAMPLE_ECONOMY = {"gdp": 15000.0, "inflation": 0.03, "employment": 0.88, "companies": 42, "inequality": 0.35}
SAMPLE_METRICS = [{"gdp": 14000 + i * 50} for i in range(50)]
SAMPLE_GOVERNANCE = {"government_type": "democracy", "laws": 12, "stability": 0.72, "legitimacy": 0.65, "tax_rate": 0.10}
SAMPLE_CULTURE = {"religion": {"religions": [{"name": "Order of the Sun", "followers": 120}]}, "memes": {"memes": []}}
SAMPLE_IDEOLOGIES = {"progressivism": {"share": 0.45}}
SAMPLE_CIVILIZATION = {"religiosity": 0.25, "militarism": 0.45, "individualism": 0.70, "traditionalism": 0.55, "innovation": 0.60, "pluralism": 0.80}
SAMPLE_COLLECTIVE_MEMORY = {"by_narrative_type": {"foundational": [], "reformist": [], "myth": []}, "volatility": {"score": 0.22, "regime": "instavel"}}
SAMPLE_MYTHS = []
SAMPLE_VOLATILITY = {"score": 0.22, "regime": "instavel"}
SAMPLE_TECH = {"era": "Industrial", "discovered_count": 8, "total_count": 26}
SAMPLE_TREE = [
    {"id": "t1", "name": "Agriculture", "discovered": True, "era": "Tribal"},
    {"id": "t2", "name": "Steam Engine", "discovered": False, "era": "Industrial"},
]
SAMPLE_DIPLOMACY = {"factions": [{"name": "Faction1", "members": 50}], "alliances": [], "conflicts": []}
SAMPLE_STRATIFICATION = {"classes": [{"name": "upper", "share": 0.2}], "mobility": 0.1}
SAMPLE_NEWS = {"total": 2, "articles": [{"id": "n1", "headline": "GDP rises", "tick": 148}]}

ENDPOINT_RESPONSES: dict[str, dict] = {
    "/status": SAMPLE_STATUS,
    "/summary": SAMPLE_SUMMARY,
    "/economy": SAMPLE_ECONOMY,
    "/metrics/history?n=50": SAMPLE_METRICS,
    "/governance": SAMPLE_GOVERNANCE,
    "/culture": SAMPLE_CULTURE,
    "/ideologies": SAMPLE_IDEOLOGIES,
    "/civilization": SAMPLE_CIVILIZATION,
    "/collective_memory": SAMPLE_COLLECTIVE_MEMORY,
    "/collective_memory/myths": SAMPLE_MYTHS,
    "/collective_memory/volatility": SAMPLE_VOLATILITY,
    "/technology": SAMPLE_TECH,
    "/technology/tree": SAMPLE_TREE,
    "/diplomacy": SAMPLE_DIPLOMACY,
    "/stratification": SAMPLE_STRATIFICATION,
    "/news/latest?n=20": SAMPLE_NEWS,
}

SAMPLE_CONTEXT = {
    "status": SAMPLE_STATUS,
    "summary": SAMPLE_SUMMARY,
    "economy": SAMPLE_ECONOMY,
    "governance": SAMPLE_GOVERNANCE,
    "culture": SAMPLE_CULTURE,
    "ideologies": SAMPLE_IDEOLOGIES,
    "civilization": SAMPLE_CIVILIZATION,
    "collective_memory": SAMPLE_COLLECTIVE_MEMORY,
    "technology": SAMPLE_TECH,
    "diplomacy": SAMPLE_DIPLOMACY,
    "stratification": SAMPLE_STRATIFICATION,
    "news_latest": SAMPLE_NEWS,
    "_tick": 150,
}


def _mock_httpx_get(url: str) -> httpx.Response:
    data = ENDPOINT_RESPONSES.get(url)
    if data is not None:
        return httpx.Response(200, json=data, request=httpx.Request("GET", url))
    return httpx.Response(404, json={"detail": "Not found"}, request=httpx.Request("GET", url))


# ─── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.collect = AsyncMock(return_value=dict(SAMPLE_CONTEXT))
    ctx.close = AsyncMock()
    return ctx


# ─── PangeiaContext tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_context_collect_returns_all_expected_keys():
    async def mock_get(url: str):
        return _mock_httpx_get(url)

    with patch("httpx.AsyncClient.get", AsyncMock(side_effect=mock_get)):
        ctx = PangeiaContext()
        data = await ctx.collect()
        await ctx.close()

    assert "status" in data
    assert data["status"]["tick"] == 150
    assert "economy" in data
    assert "governance" in data
    assert "culture" in data
    assert "collective_memory" in data
    assert "technology" in data
    assert "diplomacy" in data
    assert "stratification" in data
    assert "news_latest" in data
    assert "_tick" in data
    assert data["_tick"] == 150


@pytest.mark.asyncio
async def test_context_collect_runs_all_endpoints():
    called = set()

    async def tracking_get(url: str):
        called.add(url)
        return _mock_httpx_get(url)

    with patch("httpx.AsyncClient.get", AsyncMock(side_effect=tracking_get)):
        ctx = PangeiaContext()
        await ctx.collect()
        await ctx.close()

    for ep in _ENDPOINTS:
        assert ep in called, f"Endpoint {ep} was not called"


@pytest.mark.asyncio
async def test_context_collect_records_error_on_failure():
    async def failing_get(url: str):
        if url == "/status":
            return httpx.Response(200, json={"running": True, "tick": 100})
        return httpx.Response(200, json={"error": "failed"})

    with patch("httpx.AsyncClient.get", AsyncMock(side_effect=failing_get)):
        ctx = PangeiaContext()
        data = await ctx.collect()
        await ctx.close()

    assert data["status"]["tick"] == 100
    assert data["_tick"] == 100


@pytest.mark.asyncio
async def test_context_collect_connection_refused_sets_offline_flag():
    async def refuse_get(url: str):
        raise httpx.ConnectError("Connection refused")

    with patch("httpx.AsyncClient.get", AsyncMock(side_effect=refuse_get)):
        ctx = PangeiaContext()
        data = await ctx.collect()
        await ctx.close()

    assert data["simulation_offline"] is True


# ─── Gemini provider tests ─────────────────────────────────────


@pytest.mark.asyncio
async def test_analyst_calls_gemini_with_system_prompt(mock_context):
    mock_response = MagicMock()
    mock_response.text = "# Relatório de Análise\n\nConteúdo do relatório."

    with patch("google.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = mock_response

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            analyst = PangeiaAnalyst()
            analyst.context = mock_context
            report = await analyst.analyze("Pergunta de teste")

        call_kwargs = mock_client.models.generate_content.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs.args[1]
        assert "Pangeia Analyst" in config.system_instruction
        assert report == "# Relatório de Análise\n\nConteúdo do relatório."


@pytest.mark.asyncio
async def test_analyst_includes_context_in_message(mock_context):
    mock_response = MagicMock()
    mock_response.text = "Relatório."

    with patch("google.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value = mock_response

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            analyst = PangeiaAnalyst()
            analyst.context = mock_context
            await analyst.analyze("Pergunta de teste")

        contents = mock_client.models.generate_content.call_args.kwargs.get("contents")
        assert "Pergunta de teste" in contents
        assert "tick" in contents


@pytest.mark.asyncio
async def test_analyst_raises_on_missing_api_key(mock_context):
    with patch.dict(os.environ, {}, clear=True):
        analyst = PangeiaAnalyst()
        analyst.context = mock_context
        with pytest.raises(EnvironmentError, match="GEMINI_API_KEY"):
            await analyst.analyze("Test")


# ─── Ollama provider tests ─────────────────────────────────────


@pytest.mark.asyncio
async def test_ollama_called_when_provider_is_ollama():
    async def mock_chat(model=None, messages=None, options=None, **kw):
        return {"message": {"content": "# Ollama Report\n\nAnalysis from local model."}}

    async def mock_get(url: str):
        return _mock_httpx_get(url)

    with (
        patch("pangeia.analyst.LLM_PROVIDER", "ollama"),
        patch("httpx.AsyncClient.get", AsyncMock(side_effect=mock_get)),
        patch("ollama.AsyncClient.chat", AsyncMock(side_effect=mock_chat)),
    ):
        analyst = PangeiaAnalyst()
        report = await analyst.analyze("Analyze the economy")

    assert "Ollama Report" in report


@pytest.mark.asyncio
async def test_ollama_sends_system_and_user_messages():
    call_args_list = []

    async def capture_chat(model=None, messages=None, options=None, **kw):
        call_args_list.append((model, messages, options))
        return {"message": {"content": "# Report"}}

    async def mock_get(url: str):
        return _mock_httpx_get(url)

    with (
        patch("pangeia.analyst.LLM_PROVIDER", "ollama"),
        patch("httpx.AsyncClient.get", AsyncMock(side_effect=mock_get)),
        patch("ollama.AsyncClient.chat", AsyncMock(side_effect=capture_chat)),
    ):
        analyst = PangeiaAnalyst()
        await analyst.analyze("Assess stability")

    assert len(call_args_list) == 1
    model, messages, options = call_args_list[0]
    assert model == "llama3"
    assert options["num_predict"] == 4000
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "You are the Pangeia Analyst" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "Assess stability" in messages[1]["content"]


@pytest.mark.asyncio
async def test_ollama_uses_custom_model_from_env():
    call_args_list = []

    async def capture_chat(model=None, messages=None, options=None, **kw):
        call_args_list.append(model)
        return {"message": {"content": "# Report"}}

    async def mock_get(url: str):
        return _mock_httpx_get(url)

    with (
        patch("pangeia.analyst.LLM_PROVIDER", "ollama"),
        patch("pangeia.analyst.OLLAMA_MODEL", "mistral:7b"),
        patch("httpx.AsyncClient.get", AsyncMock(side_effect=mock_get)),
        patch("ollama.AsyncClient.chat", AsyncMock(side_effect=capture_chat)),
    ):
        analyst = PangeiaAnalyst()
        await analyst.analyze("Test")

    assert call_args_list[0] == "mistral:7b"


@pytest.mark.asyncio
async def test_ollama_raises_on_api_error():
    async def fail_chat(model=None, messages=None, options=None, **kw):
        import ollama as _ollama
        resp = httpx.Response(500, request=httpx.Request("POST", "http://localhost:11434/api/chat"))
        raise _ollama.ResponseError(response=resp)

    async def mock_get(url: str):
        return _mock_httpx_get(url)

    with (
        patch("pangeia.analyst.LLM_PROVIDER", "ollama"),
        patch("httpx.AsyncClient.get", AsyncMock(side_effect=mock_get)),
        patch("ollama.AsyncClient.chat", AsyncMock(side_effect=fail_chat)),
    ):
        analyst = PangeiaAnalyst()
        with pytest.raises(Exception):
            await analyst.analyze("Trigger error")


# ─── ReportWriter tests ────────────────────────────────────────


def test_report_writer_saves_file_in_reports_dir(tmp_path):
    writer = ReportWriter(reports_dir=str(tmp_path / "reports"))
    report_text = "# Test Report\n\nContent."
    path = writer.save("What is the risk?", report_text, tick=150)

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert content == report_text


def test_report_writer_creates_reports_directory(tmp_path):
    target = tmp_path / "custom_reports"
    assert not target.exists()

    writer = ReportWriter(reports_dir=str(target))
    writer.save("Test?", "content", tick=100)

    assert target.exists()
    assert target.is_dir()


def test_report_writer_filename_format(tmp_path):
    writer = ReportWriter(reports_dir=str(tmp_path))
    path = writer.save("Qual o risco de colapso político?", "report content", tick=150)

    assert "tick150" in path.name
    assert path.name.endswith(".md")
    assert "qual_o_risco_de_colapso" in path.name


def test_report_writer_sanitizes_special_chars_in_filename(tmp_path):
    writer = ReportWriter(reports_dir=str(tmp_path))
    path = writer.save("Compare (tech) & [economy]!", "content", tick=50)

    assert path.name.endswith(".md")
    assert "(" not in path.name
    assert ")" not in path.name
    assert "[" not in path.name
    assert "]" not in path.name


# ─── CLI tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cli_with_question_executes_successfully(tmp_path):
    mock_response = MagicMock()
    mock_response.text = "# Report from CLI"

    test_args = ["pangeia.analyst", "What is the current state?"]

    async def mock_get(url: str):
        return _mock_httpx_get(url)

    with patch.object(sys, "argv", test_args):
        with patch("httpx.AsyncClient.get", AsyncMock(side_effect=mock_get)):
            with patch("google.genai.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_client.models.generate_content.return_value = mock_response

                with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
                    with patch("pangeia.analyst.ReportWriter.save", return_value=tmp_path / "report.md"):
                        try:
                            await main()
                        except SystemExit as e:
                            pytest.fail(f"main() raised SystemExit: {e}")


def test_cli_without_question_exits_with_usage():
    test_args = ["pangeia.analyst"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as exc:
            import asyncio
            asyncio.run(main())
    assert exc.value.code == 1
