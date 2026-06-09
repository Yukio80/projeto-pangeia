from __future__ import annotations

import random
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Temperamento Inato — 11 traços, distribuição normal, imutável no nascimento
# ═══════════════════════════════════════════════════════════════════════════════

TRAIT_NAMES = [
    "curiosidade", "agressividade", "empatia", "disciplina", "ambicao",
    "sociabilidade", "impulsividade", "tolerancia_risco", "altruismo",
    "resiliencia", "espiritualidade",
]


@dataclass
class Temperament:
    """Traços inatos do agente. Gerados no nascimento com distribuição normal.
    Mudam muito lentamente ao longo da vida (0.001-0.01 por ano simulado).
    """
    curiosidade: float = 0.5
    agressividade: float = 0.5
    empatia: float = 0.5
    disciplina: float = 0.5
    ambicao: float = 0.5
    sociabilidade: float = 0.5
    impulsividade: float = 0.5
    tolerancia_risco: float = 0.5
    altruismo: float = 0.5
    resiliencia: float = 0.5
    espiritualidade: float = 0.5

    @classmethod
    def random(cls, rng: random.Random) -> Temperament:
        """Distribuição normal μ=0.5, σ=0.15 — maioria com valores médios,
        poucos extremos. Clamping em [0, 1].
        """
        return cls(**{
            name: max(0.0, min(1.0, rng.gauss(0.5, 0.15)))
            for name in TRAIT_NAMES
        })

    def as_dict(self) -> dict:
        return {name: round(getattr(self, name), 3) for name in TRAIT_NAMES}

    def get(self, name: str) -> float:
        return getattr(self, name, 0.5)

    def mutate(self, rate: float = 0.005, rng: Optional[random.Random] = None):
        """Evolução lenta: 0.001-0.01 por ano simulado (rate por tick)."""
        if rng is None:
            rng = random
        for name in TRAIT_NAMES:
            if rng.random() < 0.3:
                delta = rng.gauss(0, rate)
                current = getattr(self, name)
                setattr(self, name, max(0.0, min(1.0, current + delta)))

    def contradictions(self) -> List[str]:
        """Identifica contradições psicológicas — traços que normalmente
        se opõem mas coexistem em alta intensidade."""
        issues = []
        if self.empatia > 0.8 and self.ambicao > 0.8:
            issues.append("empatico_ambicioso")
        if self.curiosidade > 0.8 and self.impulsividade > 0.8:
            issues.append("curioso_impulsivo")
        if self.tolerancia_risco > 0.8 and self.espiritualidade > 0.8:
            issues.append("corajoso_supersticioso")
        if self.agressividade > 0.8 and self.altruismo > 0.8:
            issues.append("agressivo_altruista")
        if self.disciplina > 0.8 and self.impulsividade > 0.8:
            issues.append("disciplinado_impulsivo")
        if self.sociabilidade > 0.8 and self.agressividade > 0.8:
            issues.append("sociavel_agressivo")
        return issues

    def has_contradictions(self) -> bool:
        return len(self.contradictions()) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Arquétipos — tendências iniciais de personalidade
# ═══════════════════════════════════════════════════════════════════════════════

class ArchetypeType(Enum):
    MERCADOR = "mercador"
    GUERREIRO = "guerreiro"
    INVENTOR = "inventor"
    SACERDOTE = "sacerdote"
    DIPLOMATA = "diplomata"
    ARTISTA = "artista"
    EXPLORADOR = "explorador"
    BUROCRATA = "burocrata"
    CRIMINOSO = "criminoso"


@dataclass
class Archetype:
    name: str
    archetype_type: ArchetypeType
    trait_modifiers: Dict[str, float]  # desvio do temperamento base
    preferred_actions: List[str]
    preferred_goals: List[Dict[str, Any]]

    def apply(self, temperament: Temperament) -> Temperament:
        """Aplica modificadores do arquétipo sobre o temperamento base."""
        result = Temperament(
            **{name: getattr(temperament, name) for name in TRAIT_NAMES}
        )
        for trait, modifier in self.trait_modifiers.items():
            current = getattr(result, trait)
            setattr(result, trait, max(0.0, min(1.0, current + modifier)))
        return result


ARCHETYPE_DEFINITIONS: Dict[ArchetypeType, Archetype] = {
    ArchetypeType.MERCADOR: Archetype(
        name="Mercador",
        archetype_type=ArchetypeType.MERCADOR,
        trait_modifiers={
            "ambicao": 0.15, "sociabilidade": 0.10, "altruismo": -0.05,
            "tolerancia_risco": 0.10,
        },
        preferred_actions=["working", "socializing", "consuming", "learning"],
        preferred_goals=[
            {"description": "Acumular riqueza", "priority": 0.9, "goal_type": "economic"},
            {"description": "Expandir negocios", "priority": 0.7, "goal_type": "economic"},
        ],
    ),
    ArchetypeType.GUERREIRO: Archetype(
        name="Guerreiro",
        archetype_type=ArchetypeType.GUERREIRO,
        trait_modifiers={
            "agressividade": 0.20, "resiliencia": 0.15, "empatia": -0.10,
            "tolerancia_risco": 0.15, "altruismo": -0.05,
        },
        preferred_actions=["patrolling", "protecting_resources", "socializing"],
        preferred_goals=[
            {"description": "Proteger o territorio", "priority": 0.9, "goal_type": "survival"},
            {"description": "Ganhar poder", "priority": 0.7, "goal_type": "political"},
        ],
    ),
    ArchetypeType.INVENTOR: Archetype(
        name="Inventor",
        archetype_type=ArchetypeType.INVENTOR,
        trait_modifiers={
            "curiosidade": 0.20, "disciplina": 0.10, "sociabilidade": -0.10,
            "impulsividade": -0.05,
        },
        preferred_actions=["researching", "learning", "contemplating"],
        preferred_goals=[
            {"description": "Descobrir novas tecnologias", "priority": 0.9, "goal_type": "knowledge"},
            {"description": "Inovar e criar", "priority": 0.8, "goal_type": "knowledge"},
        ],
    ),
    ArchetypeType.SACERDOTE: Archetype(
        name="Sacerdote",
        archetype_type=ArchetypeType.SACERDOTE,
        trait_modifiers={
            "espiritualidade": 0.20, "empatia": 0.15, "altruismo": 0.15,
            "ambicao": -0.10, "agressividade": -0.10,
        },
        preferred_actions=["make_speech", "contemplating", "socializing", "learning"],
        preferred_goals=[
            {"description": "Guiar espiritualmente", "priority": 0.9, "goal_type": "religious"},
            {"description": "Unir a comunidade", "priority": 0.7, "goal_type": "social"},
        ],
    ),
    ArchetypeType.DIPLOMATA: Archetype(
        name="Diplomata",
        archetype_type=ArchetypeType.DIPLOMATA,
        trait_modifiers={
            "sociabilidade": 0.20, "empatia": 0.15, "agressividade": -0.15,
            "disciplina": 0.10,
        },
        preferred_actions=["make_speech", "socializing", "learning"],
        preferred_goals=[
            {"description": "Construir aliancas", "priority": 0.9, "goal_type": "social"},
            {"description": "Promover cooperacao", "priority": 0.8, "goal_type": "political"},
        ],
    ),
    ArchetypeType.ARTISTA: Archetype(
        name="Artista",
        archetype_type=ArchetypeType.ARTISTA,
        trait_modifiers={
            "impulsividade": 0.20, "curiosidade": 0.15, "disciplina": -0.15,
            "sociabilidade": 0.10,
        },
        preferred_actions=["contemplating", "socializing", "learning"],
        preferred_goals=[
            {"description": "Expressar criatividade", "priority": 0.9, "goal_type": "cultural"},
            {"description": "Inspirar outros", "priority": 0.7, "goal_type": "social"},
        ],
    ),
    ArchetypeType.EXPLORADOR: Archetype(
        name="Explorador",
        archetype_type=ArchetypeType.EXPLORADOR,
        trait_modifiers={
            "curiosidade": 0.20, "tolerancia_risco": 0.20, "disciplina": -0.10,
            "impulsividade": 0.10,
        },
        preferred_actions=["learning", "researching", "socializing", "investigating"],
        preferred_goals=[
            {"description": "Explorar o desconhecido", "priority": 0.9, "goal_type": "knowledge"},
            {"description": "Descobrir novos horizontes", "priority": 0.8, "goal_type": "survival"},
        ],
    ),
    ArchetypeType.BUROCRATA: Archetype(
        name="Burocrata",
        archetype_type=ArchetypeType.BUROCRATA,
        trait_modifiers={
            "disciplina": 0.20, "impulsividade": -0.20, "tolerancia_risco": -0.10,
            "ambicao": 0.05,
        },
        preferred_actions=["working", "learning", "socializing"],
        preferred_goals=[
            {"description": "Manter a ordem", "priority": 0.9, "goal_type": "political"},
            {"description": "Administrar recursos", "priority": 0.7, "goal_type": "economic"},
        ],
    ),
    ArchetypeType.CRIMINOSO: Archetype(
        name="Criminoso",
        archetype_type=ArchetypeType.CRIMINOSO,
        trait_modifiers={
            "agressividade": 0.20, "ambicao": 0.15, "empatia": -0.20,
            "altruismo": -0.20, "impulsividade": 0.10,
        },
        preferred_actions=["protecting_resources", "socializing", "investigating"],
        preferred_goals=[
            {"description": "Tomar poder pela forca", "priority": 0.9, "goal_type": "political"},
            {"description": "Acumular riqueza rapido", "priority": 0.8, "goal_type": "economic"},
        ],
    ),
}


def random_archetype(rng: random.Random) -> ArchetypeType:
    """Distribuição mais comum: Mercador, Guerreiro, Inventor; mais raros:
    Sacerdote, Diplomata, Artista, Explorador, Burocrata, Criminoso."""
    weights = [0.15, 0.13, 0.12, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10]
    types = list(ArchetypeType)
    return rng.choices(types, weights=weights, k=1)[0]


def generate_temperament_with_contradictions(rng: random.Random) -> Temperament:
    """Gera temperamento que pode incluir contradições psicológicas."""
    base = Temperament.random(rng)
    if rng.random() < 0.15:
        pair = rng.choice([
            ("empatia", "ambicao"),
            ("curiosidade", "impulsividade"),
            ("tolerancia_risco", "espiritualidade"),
            ("agressividade", "altruismo"),
            ("disciplina", "impulsividade"),
            ("sociabilidade", "agressividade"),
        ])
        t1, t2 = pair
        setattr(base, t1, max(0.8, min(1.0, getattr(base, t1) + 0.3)))
        setattr(base, t2, max(0.8, min(1.0, getattr(base, t2) + 0.3)))
    return base


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Modificadores Comportamentais — acumulam com experiências de vida
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BehaviorModifier:
    """Um modificador comportamental gerado por uma experiência de vida."""
    source_event: str
    tick: int
    trait: str  # qual traço do temperamento/emoção influencia
    delta: float  # quanto modifica (-1 a 1)
    duration: int  # ticks que dura (0 = permanente)
    decay_per_tick: float = 0.0  # quanto perde por tick

    def effective_delta(self, current_tick: int) -> float:
        """Retorna o delta atual, considerando decay."""
        age = current_tick - self.tick
        if self.duration > 0 and age >= self.duration:
            return 0.0
        decay = age * self.decay_per_tick
        remaining = abs(self.delta) - decay
        if remaining <= 0:
            return 0.0
        return math.copysign(remaining, self.delta)


@dataclass
class AgentBehaviorModifiers:
    """Sistema de modificadores acumulativos baseados em experiências.
    Não alteram o temperamento original — apenas influenciam a tomada de decisão.
    """
    modifiers: List[BehaviorModifier] = field(default_factory=list)

    def add(self, source_event: str, tick: int, trait: str,
            delta: float, duration: int = 0, decay: float = 0.0):
        self.modifiers.append(BehaviorModifier(
            source_event=source_event, tick=tick, trait=trait,
            delta=delta, duration=duration, decay_per_tick=decay,
        ))

    def get_total_delta(self, tick: int, trait: str) -> float:
        """Soma todos os deltas ativos para um traço."""
        total = 0.0
        self.modifiers = [
            m for m in self.modifiers
            if not (m.duration > 0 and (tick - m.tick) >= m.duration)
        ]
        for m in self.modifiers:
            if m.trait == trait:
                total += m.effective_delta(tick)
        return max(-1.0, min(1.0, total))

    def as_dict(self) -> list:
        return [
            {
                "source": m.source_event,
                "tick": m.tick,
                "trait": m.trait,
                "delta": round(m.delta, 3),
                "duration": m.duration,
            }
            for m in self.modifiers
        ]

    def count(self) -> int:
        return len(self.modifiers)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Memória Emocional — eventos com carga afetiva persistente
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EmotionalMemory:
    """Um evento armazenado com suas cargas emocionais associadas.
    Influencia decisões futuras: vingança, amizade, alianças, preconceitos."""
    event_id: str
    tick: int
    event_type: str
    description: str
    participants: List[str]
    anger: float = 0.0
    fear: float = 0.0
    sadness: float = 0.0
    joy: float = 0.0
    trust: float = 0.0  # positivo = confiança aumentada, negativo = diminuída
    intensity: float = 1.0  # decai com o tempo

    def decay(self, rate: float = 0.002):
        self.intensity = max(0.0, self.intensity - rate)
        for attr in ("anger", "fear", "sadness", "joy", "trust"):
            setattr(self, attr, getattr(self, attr) * self.intensity)

    def as_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "tick": self.tick,
            "event_type": self.event_type,
            "description": self.description[:60],
            "participants": self.participants[:3],
            "anger": round(self.anger, 3),
            "fear": round(self.fear, 3),
            "sadness": round(self.sadness, 3),
            "joy": round(self.joy, 3),
            "trust": round(self.trust, 3),
            "intensity": round(self.intensity, 3),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Estado Emocional Persistente (renovado)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EmotionalState:
    happiness: float = 0.5
    trust: float = 0.5
    anger: float = 0.0
    fear: float = 0.0
    curiosity: float = 0.5
    sadness: float = 0.0

    def update(self, delta_happiness: float = 0, delta_trust: float = 0,
               delta_anger: float = 0, delta_fear: float = 0,
               delta_curiosity: float = 0, delta_sadness: float = 0):
        self.happiness = max(0.0, min(1.0, self.happiness + delta_happiness))
        self.trust = max(0.0, min(1.0, self.trust + delta_trust))
        self.anger = max(0.0, min(1.0, self.anger + delta_anger))
        self.fear = max(0.0, min(1.0, self.fear + delta_fear))
        self.curiosity = max(0.0, min(1.0, self.curiosity + delta_curiosity))
        self.sadness = max(0.0, min(1.0, self.sadness + delta_sadness))

    def as_dict(self) -> dict:
        return {
            "happiness": round(self.happiness, 3),
            "trust": round(self.trust, 3),
            "anger": round(self.anger, 3),
            "fear": round(self.fear, 3),
            "curiosity": round(self.curiosity, 3),
            "sadness": round(self.sadness, 3),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Necessidades Psicológicas (Self-Determination Theory)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PsychologicalNeeds:
    autonomy: float = 0.7
    competence: float = 0.7
    belonging: float = 0.7

    def decay(self, rate: float = 0.005):
        """Necessidades não atendidas decaem com o tempo."""
        self.autonomy = max(0.0, self.autonomy - rate)
        self.competence = max(0.0, self.competence - rate)
        self.belonging = max(0.0, self.belonging - rate)

    def satisfy(self, autonomy: float = 0, competence: float = 0,
                belonging: float = 0):
        self.autonomy = min(1.0, self.autonomy + autonomy)
        self.competence = min(1.0, self.competence + competence)
        self.belonging = min(1.0, self.belonging + belonging)

    def lowest(self) -> Tuple[str, float]:
        """Retorna a necessidade mais baixa."""
        needs = [
            ("autonomy", self.autonomy),
            ("competence", self.competence),
            ("belonging", self.belonging),
        ]
        return min(needs, key=lambda x: x[1])

    def as_dict(self) -> dict:
        return {
            "autonomy": round(self.autonomy, 3),
            "competence": round(self.competence, 3),
            "belonging": round(self.belonging, 3),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Influência Cultural — grupos aos quais o agente pertence
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CulturalInfluence:
    """Valores, crenças, normas e tabus de um grupo cultural."""
    group_name: str
    group_type: str  # city, religion, faction, social_class, professional
    values: Dict[str, float] = field(default_factory=dict)
    beliefs: List[str] = field(default_factory=list)
    norms: List[str] = field(default_factory=list)
    taboos: List[str] = field(default_factory=list)
    cohesion: float = 0.5
    influence_weight: float = 0.3  # quanto este grupo influencia o agente

    def as_dict(self) -> dict:
        return {
            "group_name": self.group_name,
            "group_type": self.group_type,
            "values": self.values,
            "beliefs": self.beliefs[:3],
            "norms": self.norms[:3],
            "taboos": self.taboos[:3],
            "cohesion": round(self.cohesion, 3),
            "weight": round(self.influence_weight, 3),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Sistema de Decisão — fórmula completa
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DecisionWeights:
    """Pesos de cada componente na decisão final."""
    temperament: float = 0.25
    experiences: float = 0.15
    emotions: float = 0.20
    culture: float = 0.15
    needs: float = 0.15
    context: float = 0.10


def compute_action_bias(
    action: str,
    temperament: Temperament,
    modifiers: AgentBehaviorModifiers,
    emotions: EmotionalState,
    needs: PsychologicalNeeds,
    tick: int,
    weights: Optional[DecisionWeights] = None,
) -> float:
    """Calcula um viés (0-1) para uma ação com base em todas as camadas.

    Retorna um score indicando o quão alinhada a ação está com o estado
    psicológico completo do agente.
    """
    w = weights or DecisionWeights()
    score = 0.5  # neutro

    # --- Temperamento ---
    action_trait_map: Dict[str, List[Tuple[str, float, float]]] = {
        "working": [
            ("disciplina", 1.0, 0.15), ("ambicao", 0.5, 0.10),
            ("curiosidade", 0.3, 0.05),
        ],
        "researching": [
            ("curiosidade", 1.0, 0.20), ("disciplina", 0.5, 0.10),
            ("impulsividade", -0.3, 0.05),
        ],
        "socializing": [
            ("sociabilidade", 1.0, 0.15), ("empatia", 0.5, 0.10),
            ("agressividade", -0.3, 0.05),
        ],
        "make_speech": [
            ("sociabilidade", 0.8, 0.10), ("ambicao", 0.5, 0.10),
            ("agressividade", 0.3, 0.05),
        ],
        "learning": [
            ("curiosidade", 1.0, 0.15), ("disciplina", 0.5, 0.10),
        ],
        "consuming": [
            ("impulsividade", 0.5, 0.10), ("disciplina", -0.3, 0.05),
        ],
        "resting": [
            ("resiliencia", -0.3, 0.10), ("disciplina", 0.2, 0.05),
        ],
        "patrolling": [
            ("agressividade", 0.5, 0.10), ("disciplina", 0.5, 0.10),
            ("tolerancia_risco", 0.3, 0.05),
        ],
        "protecting_resources": [
            ("agressividade", 0.8, 0.10), ("tolerancia_risco", 0.5, 0.10),
            ("altruismo", 0.3, 0.05),
        ],
        "contemplating": [
            ("espiritualidade", 0.8, 0.10), ("curiosidade", 0.5, 0.10),
            ("sociabilidade", -0.3, 0.05),
        ],
        "investigating": [
            ("curiosidade", 0.8, 0.10), ("tolerancia_risco", 0.3, 0.10),
            ("agressividade", 0.3, 0.05),
        ],
        "seeking_job": [
            ("ambicao", 0.8, 0.10), ("disciplina", 0.3, 0.05),
        ],
        "starting_company": [
            ("ambicao", 1.0, 0.15), ("tolerancia_risco", 0.8, 0.10),
            ("disciplina", 0.3, 0.05),
        ],
    }

    if action in action_trait_map:
        for trait, direction, weight in action_trait_map[action]:
            trait_val = temperament.get(trait)
            mod = modifiers.get_total_delta(tick, trait) if modifiers else 0
            effective = max(0.0, min(1.0, trait_val + mod))
            score += direction * effective * weight

    # --- Emoções ---
    emotion_action_map: Dict[str, List[Tuple[str, float, float]]] = {
        "working": [("happiness", 0.3, 0.05)],
        "socializing": [
            ("happiness", 0.5, 0.05), ("trust", 0.3, 0.05),
            ("anger", -0.3, 0.03),
        ],
        "make_speech": [
            ("anger", 0.3, 0.03), ("happiness", 0.3, 0.03),
        ],
        "resting": [("fear", -0.3, 0.05), ("sadness", -0.3, 0.03)],
        "patrolling": [("fear", -0.2, 0.03), ("anger", 0.3, 0.03)],
        "protecting_resources": [("anger", 0.5, 0.05), ("fear", 0.3, 0.03)],
        "contemplating": [("curiosity", 0.5, 0.05), ("sadness", 0.2, 0.03)],
    }
    if action in emotion_action_map:
        for emo, direction, weight in emotion_action_map[action]:
            emo_val = getattr(emotions, emo, 0.5)
            score += direction * emo_val * weight

    # --- Necessidades ---
    need_action_map: Dict[str, List[Tuple[str, float, float]]] = {
        "starting_company": [("autonomy", 0.5, 0.05), ("competence", 0.3, 0.05)],
        "working": [("competence", 0.3, 0.05)],
        "socializing": [("belonging", 0.5, 0.05)],
        "make_speech": [("autonomy", 0.5, 0.05), ("belonging", 0.3, 0.05)],
        "seeking_job": [("competence", 0.3, 0.05)],
        "learning": [("competence", 0.5, 0.05)],
        "researching": [("competence", 0.5, 0.05), ("autonomy", 0.3, 0.05)],
        "protecting_resources": [("belonging", 0.3, 0.05)],
    }
    if action in need_action_map:
        for need, direction, weight in need_action_map[action]:
            need_val = getattr(needs, need, 0.5)
            deficit = 1.0 - need_val
            score += direction * deficit * weight

    return max(0.0, min(1.0, score))


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Fábrica de eventos emocionais — mapeia eventos de vida para cargas afetivas
# ═══════════════════════════════════════════════════════════════════════════════

EVENT_EMOTIONAL_PROFILES: Dict[str, Dict[str, float]] = {
    "robbery": {"anger": 0.7, "fear": 0.5, "sadness": 0.4, "joy": -0.3, "trust": -0.5},
    "assault": {"anger": 0.9, "fear": 0.7, "sadness": 0.3, "trust": -0.6},
    "robbery_victim": {"anger": 0.8, "fear": 0.6, "trust": -0.6},
    "death": {"sadness": 0.9, "anger": 0.2, "fear": 0.4, "joy": -0.5, "trust": -0.3},
    "birth": {"joy": 0.8, "happiness": 0.7, "trust": 0.3},
    "war": {"fear": 0.8, "anger": 0.6, "sadness": 0.5, "trust": -0.5},
    "victory": {"joy": 0.8, "happiness": 0.9, "trust": 0.4, "anger": -0.3},
    "defeat": {"sadness": 0.7, "fear": 0.5, "anger": 0.4, "trust": -0.3},
    "discovery": {"joy": 0.7, "happiness": 0.8, "curiosity": 0.5, "trust": 0.2},
    "achievement": {"joy": 0.8, "happiness": 0.9, "trust": 0.3},
    "business_success": {"joy": 0.6, "happiness": 0.7, "trust": 0.3, "anger": -0.2},
    "business_fail": {"sadness": 0.5, "fear": 0.4, "anger": 0.4, "trust": -0.3},
    "betrayal": {"anger": 0.8, "sadness": 0.6, "trust": -0.8, "fear": 0.3},
    "friendship": {"joy": 0.6, "happiness": 0.5, "trust": 0.5},
    "enmity": {"anger": 0.5, "fear": 0.3, "trust": -0.5},
    "speech": {"joy": 0.3, "happiness": 0.3, "trust": 0.2},
    "famine": {"fear": 0.7, "sadness": 0.6, "anger": 0.4, "trust": -0.4},
    "disease": {"fear": 0.8, "sadness": 0.5, "trust": -0.3},
    "migration": {"fear": 0.4, "curiosity": 0.5, "sadness": 0.3, "trust": 0.1},
    "promotion": {"joy": 0.7, "happiness": 0.8, "trust": 0.2},
    "punishment": {"anger": 0.6, "sadness": 0.4, "fear": 0.3, "trust": -0.4},
    "idea": {"curiosity": 0.6, "joy": 0.4, "happiness": 0.5},
    "milestone": {"joy": 0.5, "happiness": 0.5, "trust": 0.2},
    "published": {"joy": 0.5, "happiness": 0.6, "trust": 0.3},
    "disaster": {"fear": 0.9, "sadness": 0.8, "anger": 0.5, "trust": -0.6},
    "wealth": {"joy": 0.5, "happiness": 0.7, "trust": 0.2},
    "influence": {"joy": 0.4, "happiness": 0.5, "trust": 0.3},
    "moltbook_post": {"joy": 0.3, "happiness": 0.4, "trust": 0.2},
    "moltbook_comment": {"joy": 0.3, "happiness": 0.3, "trust": 0.2},
}


def get_emotional_profile(event_type: str) -> Dict[str, float]:
    """Retorna o perfil emocional de um tipo de evento, ou vazio se não mapeado."""
    return EVENT_EMOTIONAL_PROFILES.get(event_type, {}).copy()


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Goal — estendido para suportar archetype
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Goal:
    description: str
    priority: float
    goal_type: str
    target: str = ""
    deadline: Optional[float] = None
    progress: float = 0.0

    def as_dict(self) -> dict:
        return {
            "description": self.description,
            "priority": round(self.priority, 3),
            "type": self.goal_type,
            "target": self.target,
            "progress": round(self.progress, 3),
        }
