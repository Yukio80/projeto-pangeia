from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CollectiveMemory:
    """Memória compartilhada por um grupo (território, religião, facção
    ou toda a civilização). A narrativa evolui com as gerações —
    eventos reais viram mitos, a carga emocional se transforma."""
    event_id: str
    tick: int
    event_type: str
    description: str
    narrative: str
    emotional_charge: Dict[str, float]  # anger, fear, sadness, joy, trust
    generations_passed: int = 0
    importance: float = 1.0
    territory_id: Optional[int] = None
    religion_id: Optional[str] = None
    faction_id: Optional[str] = None
    citation_count: int = 1  # quantas vezes foi referenciado

    def age(self, myth_rate: float = 0.05, fade_rate: float = 0.03):
        """Uma geração se passa. A memória desbota e pode virar mito."""
        self.generations_passed += 1
        self.importance = max(0.0, self.importance - fade_rate)
        if self.generations_passed >= 3 and self.importance > 0.3:
            if random.random() < myth_rate:
                self._mythologize()

    def _mythologize(self):
        """Transforma a memória em mito — narrativa se torna mais abstrata
        e simbólica, carga emocional se intensifica."""
        myth_prefixes = [
            "Reza a lenda que ", "Contam os antigos que ",
            "Nos tempos imemoriais, ", "Diz-se que outrora ",
            "As vozes do passado sussurram que ",
        ]
        prefix = random.choice(myth_prefixes)
        self.narrative = f"{prefix}{self.narrative.lower().rstrip('.')}."
        for k in self.emotional_charge:
            self.emotional_charge[k] = min(1.0, self.emotional_charge[k] * 1.3)

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
            "territory_id": self.territory_id,
            "religion_id": self.religion_id,
            "faction_id": self.faction_id,
            "citation_count": self.citation_count,
        }


def merge_emotional_profiles(
    event_type: str,
    existing_territory_charge: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Gera perfil emocional base para um CollectiveMemory."""
    from pangeia.core.psychology import EVENT_EMOTIONAL_PROFILES
    base = EVENT_EMOTIONAL_PROFILES.get(event_type, {}).copy()
    if not base:
        base = {"fear": 0.3, "sadness": 0.2, "trust": -0.1}
    # Amplifica se o território já tem histórico
    if existing_territory_charge:
        for k in base:
            base[k] = base[k] * 0.7 + existing_territory_charge.get(k, 0) * 0.3
    return base


class CollectiveMemorySystem:
    """Gerencia as memórias coletivas da civilização.

    Memórias são criadas a partir de eventos significativos e associadas
    a territórios, religiões, facções ou a toda a civilização.

    Com o passar das gerações:
    - A importância desbota (fade_rate)
    - Memórias antigas viram mitos (myth_rate)
    - A carga emocional influencia decisões do grupo
    """

    def __init__(self):
        self.memories: List[CollectiveMemory] = []
        self._event_counter: int = 0

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
    ) -> CollectiveMemory:
        self._event_counter += 1
        event_id = f"CM{self._event_counter:05d}"
        mem = CollectiveMemory(
            event_id=event_id,
            tick=tick,
            event_type=event_type,
            description=description,
            narrative=narrative,
            emotional_charge=emotional_charge or {"fear": 0.3, "sadness": 0.2},
            importance=importance,
            territory_id=territory_id,
            religion_id=religion_id,
            faction_id=faction_id,
        )
        self.memories.append(mem)
        return mem

    def step(self, tick: int, generations: int = 1):
        """Avança o tempo para todas as memórias. Gerações podem ser
        passadas mais rápido (ex: 1 geração = N ticks)."""
        for _ in range(generations):
            for mem in self.memories:
                mem.age()
        self.memories = [m for m in self.memories if m.importance > 0.01]

    def get_memories(
        self,
        territory_id: Optional[int] = None,
        religion_id: Optional[str] = None,
        faction_id: Optional[str] = None,
        min_importance: float = 0.0,
        limit: int = 50,
    ) -> List[CollectiveMemory]:
        """Filtra memórias por grupo e importância mínima."""
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
            results.append(m)
        results.sort(key=lambda x: x.importance, reverse=True)
        return results[:limit]

    def get_emotional_bias(
        self,
        territory_id: Optional[int] = None,
        religion_id: Optional[str] = None,
        faction_id: Optional[str] = None,
    ) -> Dict[str, float]:
        """Retorna a carga emocional agregada para um grupo,
        ponderada pela importância de cada memória."""
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
        """Retorna memórias que já viraram mito."""
        return [m for m in self.memories if m.generations_passed >= min_generations]

    def most_influential(self, n: int = 10) -> List[CollectiveMemory]:
        """As memórias mais influentes (importância * citações)."""
        scored = sorted(
            self.memories,
            key=lambda m: m.importance * (1 + m.citation_count * 0.1),
            reverse=True,
        )
        return scored[:n]

    def cite(self, event_id: str):
        """Incrementa o contador de citações de uma memória."""
        for m in self.memories:
            if m.event_id == event_id:
                m.citation_count += 1
                break

    def summarize(self) -> dict:
        total = len(self.memories)
        myths = len(self.get_myths())
        return {
            "total_memories": total,
            "myths": myths,
            "active_memories": total - myths,
            "most_influential": [m.as_dict() for m in self.most_influential(5)],
            "average_generations": (
                sum(m.generations_passed for m in self.memories) / max(1, total)
            ),
        }
