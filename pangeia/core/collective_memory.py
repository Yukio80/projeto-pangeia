from __future__ import annotations

import random
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# CollectiveMemory
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CollectiveMemory:
    event_id: str
    tick: int
    event_type: str
    description: str
    narrative: str
    emotional_charge: Dict[str, float]
    generations_passed: int = 0
    importance: float = 1.0
    dominance: float = 0.5
    territory_id: Optional[int] = None
    religion_id: Optional[str] = None
    faction_id: Optional[str] = None
    citation_count: int = 1
    narrative_type: str = "foundational"  # foundational | reformist | revolutionary | myth

    def age(self, myth_rate: float = 0.05, fade_rate: float = 0.03):
        self.generations_passed += 1
        self.importance = max(0.0, self.importance - fade_rate)
        if self.generations_passed >= 3 and self.importance > 0.3:
            if random.random() < myth_rate:
                self._mythologize()

    def _mythologize(self):
        myth_prefixes = [
            "Reza a lenda que ", "Contam os antigos que ",
            "Nos tempos imemoriais, ", "Diz-se que outrora ",
            "As vozes do passado sussurram que ",
        ]
        self.narrative = f"{random.choice(myth_prefixes)}{self.narrative.lower().rstrip('.')}."
        for k in self.emotional_charge:
            self.emotional_charge[k] = min(1.0, self.emotional_charge[k] * 1.3)
        self.narrative_type = "myth"

    def as_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "tick": self.tick,
            "event_type": self.event_type,
            "description": self.description[:80],
            "narrative": self.narrative[:120],
            "emotional_charge": {k: round(v, 3) for k, v in self.emotional_charge.items()},
            "generations_passed": self.generations_passed,
            "importance": round(self.importance, 3),
            "dominance": round(self.dominance, 3),
            "territory_id": self.territory_id,
            "religion_id": self.religion_id,
            "faction_id": self.faction_id,
            "citation_count": self.citation_count,
            "narrative_type": self.narrative_type,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Narrativas concorrentes — reformista / revolucionária
# ═══════════════════════════════════════════════════════════════════════════════

_NARRATIVE_PREFIXES: Dict[str, List[str]] = {
    "reformist": [
        "Uma nova geração questiona: ",
        "Vozes dissidentes apontam que ",
        "Reformistas argumentam que ",
        "Críticos recordam que ",
        "Historiadores revisionistas sugerem que ",
    ],
    "revolutionary": [
        "A verdade, há muito escondida, é que ",
        "O povo desperta para o fato de que ",
        "Revolucionários proclamam que ",
        "Rompe-se o véu da ilusão: ",
        "Uma nova consciência denuncia que ",
    ],
}

_COUNTER_SUFFIXES: Dict[str, List[str]] = {
    "reformist": [
        " — é hora de corrigir o rumo sem destruir o que construímos.",
        " — precisamos de reformas, não de rupturas.",
        " — o passado nos guia, mas não nos prende.",
        " — honrar a tradição é também saber mudá-la.",
    ],
    "revolutionary": [
        " — o sistema precisa ser desmantelado por completo.",
        " — não há reconciliação possível com o velho mundo.",
        " — a fundação está podre; construamos do zero.",
        " — a verdadeira Pangeia ainda está por nascer.",
    ],
}


def _generate_counter_narrative(
    original: CollectiveMemory,
    counter_type: str,
    rng: random.Random,
) -> CollectiveMemory:
    prefix = rng.choice(_NARRATIVE_PREFIXES.get(counter_type, ["Recorda-se que "]))
    suffix = rng.choice(_COUNTER_SUFFIXES.get(counter_type, [""]))
    inverted_charge = {k: -v * rng.uniform(0.5, 1.0) for k, v in original.emotional_charge.items()}
    if counter_type == "revolutionary":
        inverted_charge["anger"] = min(1.0, inverted_charge.get("anger", 0) + 0.3)
        inverted_charge["trust"] = max(-1.0, inverted_charge.get("trust", 0) - 0.2)
    return CollectiveMemory(
        event_id=f"CN_{original.event_id}_{counter_type}",
        tick=original.tick,
        event_type=counter_type,
        description=f"Narrativa {counter_type} sobre: {original.description[:50]}",
        narrative=f"{prefix}{original.narrative.lower().rstrip('.')}{suffix}",
        emotional_charge=inverted_charge,
        importance=original.importance * rng.uniform(0.4, 0.8),
        dominance=rng.uniform(0.2, 0.5),
        territory_id=original.territory_id,
        religion_id=original.religion_id,
        faction_id=original.faction_id,
        narrative_type=counter_type,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Coortes geracionais
# ═══════════════════════════════════════════════════════════════════════════════

class GenerationCohort(Enum):
    YOUNG = "young"      # 0-30 ticks
    ADULT = "adult"      # 31-100
    ELDER = "elder"      # 100+


def get_cohort(age: int) -> GenerationCohort:
    if age <= 30:
        return GenerationCohort.YOUNG
    if age <= 100:
        return GenerationCohort.ADULT
    return GenerationCohort.ELDER


_COHORT_REBELLION_WEIGHTS = {
    GenerationCohort.YOUNG: 1.4,
    GenerationCohort.ADULT: 0.8,
    GenerationCohort.ELDER: 0.3,
}


# ═══════════════════════════════════════════════════════════════════════════════
# HistoricalVolatility
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HistoricalVolatility:
    """Indicador composto de volatilidade histórica da civilização."""
    rebellion_count: int = 0
    narrative_turnover: float = 0.0
    emotional_polarization: float = 0.0
    myth_formation_rate: float = 0.0
    dominance_oscillation: float = 0.0
    composite: float = 0.0

    def compute(self, cm_system: "CollectiveMemorySystem", tick: int) -> "HistoricalVolatility":
        mems = cm_system.memories
        total = len(mems)
        if total == 0:
            return self

        # Rebellion frequency (over last 50 gens stored in dominance_history)
        hist = cm_system._parent_dominance_history
        if len(hist) >= 2:
            drops = sum(
                1 for i in range(1, len(hist)) if hist[i] < hist[i-1] * 0.7
            )
            self.rebellion_count = cm_system._rebellion_count

        # Narrative turnover — proportion of reformist + revolutionary memories
        counter = sum(1 for m in mems if m.narrative_type in ("reformist", "revolutionary"))
        self.narrative_turnover = counter / max(1, total)

        # Emotional polarization — spread of emotional charges across memories
        if mems:
            charges = []
            for m in mems:
                for v in m.emotional_charge.values():
                    charges.append(v)
            if charges:
                mean_c = sum(charges) / len(charges)
                variance = sum((c - mean_c) ** 2 for c in charges) / len(charges)
                self.emotional_polarization = min(1.0, math.sqrt(variance))

        # Myth formation rate
        myths = sum(1 for m in mems if m.narrative_type == "myth")
        self.myth_formation_rate = myths / max(1, total)

        # Dominance oscillation — std dev of last 10 dominance values
        if len(hist) >= 3:
            recent = hist[-10:]
            mean_d = sum(recent) / len(recent)
            var_d = sum((d - mean_d) ** 2 for d in recent) / len(recent)
            self.dominance_oscillation = min(1.0, math.sqrt(var_d))

        # Composite: weighted sum
        self.composite = (
            min(1.0, self.rebellion_count * 0.1) * 0.25 +
            self.narrative_turnover * 0.25 +
            self.emotional_polarization * 0.20 +
            self.myth_formation_rate * 0.15 +
            self.dominance_oscillation * 0.15
        )
        return self

    def regime_label(self) -> str:
        c = self.composite
        if c < 0.15:
            return "estável"
        if c < 0.30:
            return "instável"
        if c < 0.45:
            return "revolucionária"
        if c < 0.60:
            return "decadente"
        return "fragmentada"

    def as_dict(self) -> dict:
        return {
            "composite": round(self.composite, 3),
            "regime": self.regime_label(),
            "rebellion_count": self.rebellion_count,
            "narrative_turnover": round(self.narrative_turnover, 3),
            "emotional_polarization": round(self.emotional_polarization, 3),
            "myth_formation_rate": round(self.myth_formation_rate, 3),
            "dominance_oscillation": round(self.dominance_oscillation, 3),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Perfil emocional helper
# ═══════════════════════════════════════════════════════════════════════════════

def merge_emotional_profiles(
    event_type: str,
    existing_territory_charge: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    from pangeia.core.psychology import EVENT_EMOTIONAL_PROFILES
    base = EVENT_EMOTIONAL_PROFILES.get(event_type, {}).copy()
    if not base:
        base = {"fear": 0.3, "sadness": 0.2, "trust": -0.1}
    if existing_territory_charge:
        for k in base:
            base[k] = base[k] * 0.7 + existing_territory_charge.get(k, 0) * 0.3
    return base


# ═══════════════════════════════════════════════════════════════════════════════
# CollectiveMemorySystem
# ═══════════════════════════════════════════════════════════════════════════════

class CollectiveMemorySystem:
    def __init__(self, rng: Optional[random.Random] = None,
                 dominance_threshold: float = 0.6,
                 rebellion_increment: float = 0.15):
        self.memories: List[CollectiveMemory] = []
        self._event_counter: int = 0
        self.rebellion_probability: float = 0.0
        self._parent_dominance_history: List[float] = []
        self._threshold = dominance_threshold
        self._rebellion_increment = rebellion_increment
        self._rebellion_count: int = 0
        self._volatility = HistoricalVolatility()
        self.rng = rng or random.Random()

    def add_memory(
        self,
        tick: int,
        event_type: str,
        description: str,
        narrative: str,
        emotional_charge: Optional[Dict[str, float]] = None,
        territory_id: Optional[int] = None,
        religion_id: Optional[str] = None,
        faction_id: Optional[str] = None,
        importance: float = 0.5,
        dominance: Optional[float] = None,
        narrative_type: str = "foundational",
    ) -> CollectiveMemory:
        self._event_counter += 1
        event_id = f"CM{self._event_counter:05d}"
        if dominance is None:
            total_charge = sum(abs(v) for v in (emotional_charge or {}).values())
            base = min(1.0, 0.3 + total_charge * 0.12)
            significance = min(1.0, importance * 1.5)
            dominance = min(1.0, base * 0.5 + significance * 0.5 + self.rng.uniform(-0.1, 0.1))
        mem = CollectiveMemory(
            event_id=event_id,
            tick=tick,
            event_type=event_type,
            description=description,
            narrative=narrative,
            emotional_charge=emotional_charge or {"fear": 0.3, "sadness": 0.2},
            importance=importance,
            dominance=dominance,
            territory_id=territory_id,
            religion_id=religion_id,
            faction_id=faction_id,
            narrative_type=narrative_type,
        )
        self.memories.append(mem)
        return mem

    def step(self, tick: int, generations: int = 1):
        """Avança as gerações. Se a dominância da geração anterior
        ultrapassou o limiar, a probabilidade de rebelião cresce.

        A rebelião não apenas enfraquece — gera contranarrativas
        (reformistas e revolucionárias) que ocupam o vácuo cultural.
        """
        for _ in range(generations):
            if self.memories:
                avg_dominance = sum(m.dominance for m in self.memories) / len(self.memories)
            else:
                avg_dominance = 0.0
            self._parent_dominance_history.append(avg_dominance)

            # Acumula rebeldia se geração anterior foi muito dominante
            if self._parent_dominance_history:
                parent = self._parent_dominance_history[-1]
                if parent > self._threshold:
                    self.rebellion_probability = min(1.0, self.rebellion_probability + self._rebellion_increment)

            # Envelhece memórias
            for mem in self.memories:
                mem.age()

        self.memories = [m for m in self.memories if m.importance > 0.01]

        # Tenta rebelião
        if self.rebellion_probability > 0.5 and self.rng.random() < self.rebellion_probability * 0.3:
            self._do_rebellion()

    def _do_rebellion(self):
        """Rebelião: narrativas dominantes são desafiadas E substituídas
        por contranarrativas reformistas e revolucionárias."""
        targets = [m for m in self.memories if m.dominance > self._threshold]
        for m in targets:
            m.importance *= 0.5
            m.dominance *= 0.4

            # Gera contranarrativa reformista
            reform = _generate_counter_narrative(m, "reformist", self.rng)
            self.memories.append(reform)

            # Gera contranarrativa revolucionária (menos frequente)
            if self.rng.random() < 0.5:
                rev = _generate_counter_narrative(m, "revolutionary", self.rng)
                self.memories.append(rev)

        self.rebellion_probability = max(0.0, self.rebellion_probability - 0.3)
        self._rebellion_count += 1

    def get_cohort_rebellion_bias(self, age: int) -> float:
        """Retorna o viés de rebeldia para um agente com base na idade.
        Jovens: 1.4×, Adultos: 0.8×, Velhos: 0.3×."""
        cohort = get_cohort(age)
        return _COHORT_REBELLION_WEIGHTS[cohort]

    def get_memories(
        self,
        territory_id: Optional[int] = None,
        religion_id: Optional[str] = None,
        faction_id: Optional[str] = None,
        min_importance: float = 0.0,
        limit: int = 50,
        narrative_type: Optional[str] = None,
    ) -> List[CollectiveMemory]:
        results = []
        for m in self.memories:
            if m.importance < min_importance:
                continue
            if territory_id is not None and m.territory_id != territory_id:
                continue
            if religion_id is not None and m.religion_id != religion_id:
                continue
            if faction_id is not None and m.faction_id != faction_id:
                continue
            if narrative_type is not None and m.narrative_type != narrative_type:
                continue
            results.append(m)
        results.sort(key=lambda x: x.importance, reverse=True)
        return results[:limit]

    def get_emotional_bias(
        self,
        territory_id: Optional[int] = None,
        religion_id: Optional[str] = None,
        faction_id: Optional[str] = None,
    ) -> Dict[str, float]:
        bias: Dict[str, float] = {}
        total_weight = 0.0
        for m in self.memories:
            if territory_id is not None and m.territory_id != territory_id:
                continue
            if religion_id is not None and m.religion_id != religion_id:
                continue
            if faction_id is not None and m.faction_id != faction_id:
                continue
            w = m.importance
            total_weight += w
            for k, v in m.emotional_charge.items():
                bias[k] = bias.get(k, 0) + v * w
        if total_weight > 0:
            for k in bias:
                bias[k] /= total_weight
        return bias

    def get_myths(self, min_generations: int = 3) -> List[CollectiveMemory]:
        return [m for m in self.memories if m.narrative_type == "myth"]

    def most_influential(self, n: int = 10) -> List[CollectiveMemory]:
        scored = sorted(
            self.memories,
            key=lambda m: m.importance * (1 + m.citation_count * 0.1),
            reverse=True,
        )
        return scored[:n]

    def cite(self, event_id: str):
        for m in self.memories:
            if m.event_id == event_id:
                m.citation_count += 1
                break

    def volatility(self, tick: int) -> HistoricalVolatility:
        self._volatility.compute(self, tick)
        return self._volatility

    def summarize(self) -> dict:
        total = len(self.memories)
        vol = self.volatility(0)
        type_counts: Dict[str, int] = {}
        for m in self.memories:
            type_counts[m.narrative_type] = type_counts.get(m.narrative_type, 0) + 1
        avg_dominance = sum(m.dominance for m in self.memories) / max(1, total)
        return {
            "total_memories": total,
            "by_narrative_type": type_counts,
            "avg_dominance": round(avg_dominance, 3),
            "rebellion_count": self._rebellion_count,
            "rebellion_probability": round(self.rebellion_probability, 3),
            "dominance_history": [round(d, 3) for d in self._parent_dominance_history[-10:]],
            "volatility": vol.as_dict(),
            "most_influential": [m.as_dict() for m in self.most_influential(5)],
            "average_generations": (
                sum(m.generations_passed for m in self.memories) / max(1, total)
            ),
        }
