from __future__ import annotations

import random
from typing import Dict, Optional

from pangeia.config import SimulationConfig
from pangeia.core.world import World
from pangeia.core.agent import Agent, ReputationEntry
from pangeia.core.communication import CommunicationSystem, Message
from pangeia.agents import AGENT_CLASSES
from pangeia.economy.market import Economy
from pangeia.governance.government import GovernanceSystem
from pangeia.governance.laws import LawSystem
from pangeia.governance.elections import ElectionSystem
from pangeia.culture.beliefs import BeliefSystem
from pangeia.culture.memes import MemePool
from pangeia.culture.religion import ReligiousSystem
from pangeia.culture.ideologies import IdeologySystem
from pangeia.diplomacy.diplomacy import DiplomacySystem
from pangeia.society.stratification import StratificationSystem
from pangeia.history.narratives import NarrativeSystem
from pangeia.events.random_events import EventSystem
from pangeia.metrics.tracker import MetricsTracker
from pangeia.technology.tech_tree import TechnologySystem
from pangeia.external_agents.protocol import PAPProtocol
from pangeia.external_agents.icarus_gateway import IcarusGateway
from pangeia.news.newsroom import NewsRoom
from pangeia.core.collective_memory import CollectiveMemorySystem, merge_emotional_profiles
from pangeia.engine.agent_array import AgentArray
from pangeia.engine.batch_processor import BatchProcessor
from pangeia.persistence import AuditRecorder, AuditLog, InMemoryAuditLog, PersistenceBackend


def _handle_working(sim, agent, tick):
    output = agent.work()
    agent.state.wealth += output * 0.5


def _handle_researching(sim, agent, tick):
    agent.work(1.5)
    sim.economy.indicators.tech_level = min(
        1.0, sim.economy.indicators.tech_level + 0.0001
    )


def _handle_starting_company(sim, agent, tick):
    if agent.state.wealth >= sim.config.economy.company_startup_cost:
        industry = sim.rng.choice(["tech", "manufacturing", "services", "agriculture"])
        company = sim.economy.register_company(agent, industry)
        if company:
            agent.state.employer_id = company.id


def _handle_socializing(sim, agent, tick):
    alive = sim._alive_ids
    if not alive or sim.rng.random() < 0.5:
        return
    other = sim.rng.choice(alive)
    attempts = 0
    while other.agent_id == agent.agent_id and attempts < 5:
        other = sim.rng.choice(alive)
        attempts += 1
    if other.agent_id == agent.agent_id:
        return
    topic = sim.rng.choice(["resources", "politics", "economy", "philosophy"])
    agent.communicate(other, f"Discussing {topic}", 0.3)
    agent.social.add_relationship(other.agent_id)
    if sim.rng.random() < 0.3:
        agent.state.add_personal_relation(
            other.agent_id, "friend", sim.rng.uniform(0.3, 0.7),
            f"Bonded over {topic}", tick,
        )
        other.state.add_personal_relation(
            agent.agent_id, "friend", sim.rng.uniform(0.3, 0.7),
            f"Bonded over {topic}", tick,
        )
    if other.agent_id not in agent.state.reputation:
        from pangeia.core.agent import ReputationEntry
        agent.state.reputation[other.agent_id] = ReputationEntry(
            agent_id=other.agent_id,
            trust=sim.rng.uniform(0.3, 0.6),
            respect=sim.rng.uniform(0.2, 0.5),
            fear=0.0,
        )


def _handle_learning(sim, agent, tick):
    topic = sim.rng.choice(["technology", "economy", "politics", "culture", "science"])
    agent.learn(topic, 0.01)


def _handle_consuming(sim, agent, tick):
    agent.state.wealth -= 2.0


def _handle_make_speech(sim, agent, tick):
    theme = sim.rng.choice(["unity", "progress", "security", "prosperity"])
    speech = f"Citizens of Pangeia, we must focus on {theme}!"
    msg = Message(
        sender_id=agent.agent_id,
        content=speech,
        message_type="media",
        truth_value=True,
    )
    sim.communication.broadcast(msg, sim.agents, tick=sim.world.state.tick)


def _handle_contemplating(sim, agent, tick):
    if sim.rng.random() < 0.05:
        myth = sim.belief_system.generate_myth(sim.rng)
        agent.knowledge.add_belief(
            myth, 0.8, agent.agent_id, "mythology"
        )


def _handle_patrolling(sim, agent, tick):
    agent.state.energy -= 1.0


def _handle_protecting_resources(sim, agent, tick):
    agent.state.energy -= 1.5


def _handle_seeking_job(sim, agent, tick):
    for company in sim.economy.companies.values():
        if len(company.employees) < 10:
            company.hire(agent.agent_id)
            agent.state.employer_id = company.id
            break


def _handle_investigating(sim, agent, tick):
    recent_events = sim.world.state.events[-3:] if sim.world.state.events else []
    if recent_events:
        event = sim.rng.choice(recent_events)
        agent.knowledge.add_belief(
            f"Investigated: {event['description']}",
            0.6, agent.agent_id, "investigation"
        )


_ACTION_HANDLERS = {
    "working": _handle_working,
    "researching": _handle_researching,
    "starting_company": _handle_starting_company,
    "socializing": _handle_socializing,
    "learning": _handle_learning,
    "consuming": _handle_consuming,
    "make_speech": _handle_make_speech,
    "contemplating": _handle_contemplating,
    "patrolling": _handle_patrolling,
    "protecting_resources": _handle_protecting_resources,
    "seeking_job": _handle_seeking_job,
    "investigating": _handle_investigating,
}


class Simulation:
    def __init__(self, config: Optional[SimulationConfig] = None,
                 audit_log: Optional[AuditLog] = None):
        self.config = config or SimulationConfig.default()
        random.seed(self.config.world.seed)
        self.rng = random.Random(self.config.world.seed)

        self.world = World(self.config, rng=self.rng)
        self.communication = CommunicationSystem()
        self.agents: Dict[str, Agent] = {}

        self.economy = Economy(self.config)
        self.governance = GovernanceSystem(self.config)
        self.law_system = LawSystem()
        self.election_system = ElectionSystem()

        self.belief_system = BeliefSystem()
        self.meme_pool = MemePool()
        self.religion_system = ReligiousSystem(rng=self.rng)
        self.ideology_system = IdeologySystem(rng=self.rng)

        self.diplomacy = DiplomacySystem(rng=self.rng)
        self.stratification = StratificationSystem()
        self.narratives = NarrativeSystem(rng=self.rng)

        self.technology = TechnologySystem(rng=self.rng)
        self.pap = PAPProtocol(rng=self.rng)

        self.event_system = EventSystem(self.rng)
        self.metrics = MetricsTracker()
        self.newsroom = NewsRoom(rng=self.rng)
        self.icarus: Optional[IcarusGateway] = None
        self.collective_memory = CollectiveMemorySystem(rng=self.rng)

        self._setup_audit_log(audit_log)
        self._initialize_population()
        self._initialize_stratification()
        self.agent_array = AgentArray(self.agents)
        self.batch_processor = BatchProcessor.from_seed(
            self.agent_array, self.config.world.seed
        )
        self._personality_influence = False

    def _setup_audit_log(self, audit_log: Optional[AuditLog] = None):
        persistence = self.config.persistence
        if audit_log:
            store = audit_log
        elif persistence.backend == PersistenceBackend.POSTGRES and persistence.dsn:
            from pangeia.persistence.postgres_store import PostgresAuditLog
            store = PostgresAuditLog(persistence.dsn)
        else:
            store = InMemoryAuditLog()
        self.audit_log = store
        self.audit_recorder = AuditRecorder(store, enabled=True)

    def _initialize_population(self):
        n = self.config.world.initial_population
        class_distribution = {
            "citizen": 0.33,
            "entrepreneur": 0.13,
            "researcher": 0.08,
            "governor": 0.04,
            "journalist": 0.06,
            "military": 0.07,
            "philosopher": 0.05,
            "moltbook": 0.10,
            "teacher": 0.07,
            "conservative": 0.07,
        }

        classes = list(class_distribution.keys())
        weights = list(class_distribution.values())

        agent_ids = []
        for i in range(n):
            agent_class = self.rng.choices(classes, weights=weights, k=1)[0]
            agent_cls = AGENT_CLASSES[agent_class]
            agent = agent_cls(self.config, rng=random.Random(self.rng.randint(0, 2**32)))
            agent.state.territory_id = self.rng.choice(self.world.state.territories).id
            self.agents[agent.agent_id] = agent
            self.governance.register_voter(agent.agent_id)
            agent_ids.append(agent.agent_id)

        for i, aid in enumerate(agent_ids):
            agent = self.agents[aid]
            self.audit_recorder.record_agent_created(
                0, agent.agent_id, agent.state.name,
                agent.state.agent_class, agent.state.territory_id or 0,
                personality=agent.personality.as_dict(),
                archetype=agent.archetype.name if agent.archetype else "none",
                contradictions=agent._contradictions,
            )
            for j in range(min(3, len(agent_ids) // 10)):
                other_id = self.rng.choice([x for x in agent_ids if x != aid])
                agent.social.add_relationship(
                    other_id, trust=self.rng.uniform(0.3, 0.7),
                    influence=self.rng.uniform(0.2, 0.5),
                )
            agent.knowledge.add_belief(
                "The world of Pangeia is vast and full of opportunity",
                0.7, "experience", "culture",
            )

        for agent in self.agents.values():
            if agent.state.agent_class == "entrepreneur" and self.rng.random() < 0.3:
                industry = self.rng.choice(["tech", "manufacturing", "services", "agriculture"])
                company = self.economy.register_company(agent, industry)
                if company:
                    for _ in range(self.rng.randint(1, 5)):
                        candidates = [a for a in self.agents.values()
                                      if a.state.agent_class == "citizen" and not a.state.employer_id]
                        if candidates:
                            employee = self.rng.choice(candidates)
                            company.hire(employee.agent_id)
                            employee.state.employer_id = company.id

        self._register_narrative_actors()

    def _register_narrative_actors(self):
        """Registra agentes influentes como NarrativeActors.

        Sacerdotes, professores, governantes, artistas, jornalistas,
        filósofos — classes que moldam ativamente a disputa cultural.
        """
        # Remove atores mortos
        dead_ids = [aid for aid, a in self.agents.items()
                    if not a.state.is_alive and aid in self.collective_memory.actors]
        for aid in dead_ids:
            self.collective_memory.remove_actor(aid)

        actor_configs = {
            "governor":    {"influence": 0.7, "ideology": "conservative", "charisma": 0.6},
            "journalist":  {"influence": 0.5, "ideology": "neutral",      "charisma": 0.5},
            "philosopher": {"influence": 0.6, "ideology": "progressive",  "charisma": 0.4},
            "researcher":  {"influence": 0.4, "ideology": "progressive",  "charisma": 0.3},
            "military":    {"influence": 0.5, "ideology": "conservative", "charisma": 0.6},
            "teacher":     {"influence": 0.5, "ideology": "neutral",      "charisma": 0.6},
            "conservative":{"influence": 0.5, "ideology": "conservative", "charisma": 0.4},
        }
        narrative_map = {
            "governor":    "foundational",
            "journalist":  "reformist",
            "philosopher": "reformist",
            "researcher":  "reformist",
            "military":    "foundational",
            "teacher":     "reformist",
            "conservative":"foundational",
        }
        for agent in self.agents.values():
            if not agent.state.is_alive:
                continue
            cls = agent.state.agent_class
            if cls in actor_configs and agent.agent_id not in self.collective_memory.actors:
                cfg = actor_configs[cls]
                audience = len(agent.social.relationships) + int(agent.state.influence * 10)
                self.collective_memory.register_actor(
                    agent_id=agent.agent_id,
                    name=agent.state.name,
                    agent_class=cls,
                    influence=cfg["influence"],
                    audience=audience,
                    ideology=cfg["ideology"],
                    charisma=cfg["charisma"] + agent.state.influence * 0.3,
                    preferred_narrative_type=narrative_map[cls],
                )

    def _initialize_stratification(self):
        self.stratification.assign_classes(self.agents)

    def _personality_rerank(self, agent: Agent, actions: list, tick: int) -> list:
        """Reordena ações secundárias por alinhamento com a personalidade.

        A ação principal (índice 0) mantém-se — são decisões de
        sobrevivência/emprego. Apenas ações secundárias (socializar,
        aprender, etc.) são reordenadas para refletir preferências
        da personalidade.

        Quando a personalidade está desativada (ablação), todas as
        ações secudárias têm peso neutro.
        """
        if len(actions) <= 1:
            return actions

        if self._personality_influence:
            scored = []
            for i, act in enumerate(actions):
                if i == 0:
                    scored.append((act, 999.0))
                else:
                    score = agent.compute_action_score(act, tick)
                    scored.append((act, score))
            scored.sort(key=lambda x: -x[1])
            return [s[0] for s in scored]
        return actions

    def step(self):
        tick = self.world.state.tick

        self.world.regenerate()

        alive_ids = [a for a in self.agents.values() if a.state.is_alive]
        self._alive_ids = alive_ids  # cache for handlers
        self._expensive_cache = {
            'economy_summary': self.economy.summary(),
            'governance_summary': self.governance.summary(),
            'resources': self.world.state.global_resources.as_dict(),
        }
        if self.technology:
            self.technology._researchable_cache = None

        for agent in list(self.agents.values()):
            if not agent.state.is_alive:
                continue
            try:
                actions = agent.decide(self)
                actions = self._personality_rerank(agent, actions, tick)
                for action in actions:
                    self._process_action(agent, action, tick)
                    if action.startswith("discovered:"):
                        agent.state.add_life_event(
                            tick, "discovery", action[11:], 0.8
                        )
                        agent.state.notable_achievements.append(action[11:])
                    elif action.startswith("idea:"):
                        agent.state.add_life_event(
                            tick, "idea", action[5:], 0.6
                        )
                    elif action == "starting_company":
                        agent.state.add_life_event(
                            tick, "business", "Started a company", 0.6
                        )
                    elif action == "make_speech":
                        agent.state.add_life_event(
                            tick, "speech", "Made a public speech", 0.4
                        )
            except Exception as e:
                agent.memory.remember(
                    f"Error during decision: {str(e)}",
                    memory_type="error",
                    importance=0.3,
                )

        self._update_economy()
        self.governance.step(self.agents, tick)
        self.event_system.step(self)
        self.belief_system.evolve()
        self.meme_pool.spread(self.agents)
        self.religion_system.step(self.agents)
        self.ideology_system.step(self.agents, tick)
        self.world.ideology_manager.tick(self.agents, tick)
        self.technology.step(self)
        self.diplomacy.step(self)
        self.stratification.assign_classes(self.agents)
        self.stratification.track_mobility()

        self._record_narratives_for_events()

        for agent in self.agents.values():
            if not agent.state.is_alive:
                continue
            agent.state.political_alignment += self.rng.gauss(0, 0.005)
            agent.state.political_alignment = max(-1.0, min(1.0, agent.state.political_alignment))
            if agent.state.wealth > 500:
                agent.state.political_alignment += 0.01
            elif agent.state.wealth < 20:
                agent.state.political_alignment -= 0.01
            rp = self.collective_memory.rebellion_probability
            cohort_bias = self.collective_memory.get_cohort_rebellion_bias(agent.state.age)
            effective_rp = rp * cohort_bias
            if effective_rp > 0.3:
                rebel_drift = self.rng.uniform(-0.03, 0.03) * effective_rp
                agent.state.political_alignment += rebel_drift
                agent.state.political_alignment = max(-1.0, min(1.0, agent.state.political_alignment))

            for other_id, rel in agent.social.relationships.items():
                if other_id in agent.state.reputation:
                    entry = agent.state.reputation[other_id]
                    entry.last_interaction += 1
                    entry.trust = rel.trust * 0.7 + entry.trust * 0.3
                    entry.respect = max(entry.respect, agent.state.influence * 0.3)

        # --- Personalidade: evolução lenta e necessidades (a cada 2 ticks) ---
        evolve_this_tick = tick % 2 == 0
        trim_emotions_this_tick = tick % 5 == 0
        for agent in self.agents.values():
            if not agent.state.is_alive:
                continue
            if evolve_this_tick:
                if not getattr(agent, '_temperament_frozen', False):
                    agent.temperament.mutate(rate=0.005, rng=self.rng)
                if not getattr(agent, '_needs_frozen', False):
                    agent.needs.decay(rate=0.003)
                    if agent.state.wealth > 100:
                        agent.needs.satisfy(autonomy=0.01, competence=0.005)
                    if len(agent.social.relationships) > 3:
                        agent.needs.satisfy(belonging=0.01)
            if trim_emotions_this_tick and not getattr(agent, '_emotions_frozen', False):
                n_keep = 0
                for em in agent.emotional_memories:
                    em.decay(rate=0.002)
                    if em.intensity > 0.01:
                        agent.emotional_memories[n_keep] = em
                        n_keep += 1
                if n_keep < len(agent.emotional_memories):
                    del agent.emotional_memories[n_keep:]

        # --- Registrar eventos emocionais para life_events recentes ---
        for agent in self.agents.values():
            if not agent.state.is_alive:
                continue
            for ev in agent.state.life_events[-3:]:
                agent.record_emotional_event(
                    tick=ev.tick,
                    event_type=ev.event_type,
                    description=ev.description,
                )

        self._age_agents()
        self._record_world_events()
        self._update_collective_memory(tick)
        self._cleanup_dead()
        if tick % 10 == 0:
            for agent in self.agents.values():
                agent.state.trim_reputation(20)
                if len(agent.skills) > 10:
                    agent.skills = dict(sorted(
                        agent.skills.items(), key=lambda x: x[1], reverse=True
                    )[:10])

        snapshot = self.metrics.record(self)
        self.newsroom.tick(self)
        if self.icarus:
            self.icarus.observe(self)
            self.icarus.decide(self)
        self.audit_recorder.record_tick(self.world.state.tick, snapshot.as_dict())
        self.audit_recorder.flush()
        self.world.state.advance_time(1.0)

        return snapshot

    def _record_world_events(self):
        if not hasattr(self, '_last_recorded_event_idx'):
            self._last_recorded_event_idx = 0
        events = self.world.state.events
        for i in range(self._last_recorded_event_idx, len(events)):
            ev = events[i]
            self.audit_recorder.record_world_event(
                ev.get("tick", self.world.state.tick),
                ev.get("type", "unknown"),
                ev.get("description", ""),
                ev.get("data", {}),
            )
        self._last_recorded_event_idx = len(events)

    def _update_collective_memory(self, tick: int):
        """Cria memórias coletivas a partir de eventos significativos
        e envelhece as existentes."""
        cm = self.collective_memory

        # Geração a cada 20 ticks ≈ 1 geração social
        if tick > 0 and tick % 20 == 0:
            cm.step(tick, generations=1)

        # Cria memórias de eventos mundiais significativos
        for ev in self.world.state.events[-3:]:
            ev_type = ev.get("type", "")
            ev_desc = ev.get("description", "")
            data = ev.get("data", {})
            tid = data.get("territory_id") if isinstance(data, dict) else None
            actual_type = data.get("event_type", ev_type) if isinstance(data, dict) else ev_type

            importance_map = {
                "war": 0.9, "disaster": 0.8, "death": 0.6,
                "discovery": 0.7, "event_start": 0.3,
                "economic_crisis": 0.7, "scientific_breakthrough": 0.7,
                "natural_disaster": 0.9, "epidemic": 0.8,
                "energy_crisis": 0.7, "technological_advance": 0.7,
                "cultural_renaissance": 0.6, "economic_boom": 0.6,
                "economic_crash": 0.7, "famine": 0.8, "plague": 0.8,
                "revolution": 0.9, "victory": 0.7, "defeat": 0.7,
                "treaty": 0.6, "migration": 0.5, "founding": 0.8,
                "event_end": 0.2,
            }
            imp = importance_map.get(actual_type, importance_map.get(ev_type, 0.3))
            if imp < 0.5:
                continue

            charge = merge_emotional_profiles(actual_type)
            if not charge or all(v == 0 for v in charge.values()):
                charge = merge_emotional_profiles(ev_type)
            narrative = f"A civilização recorda: {ev_desc.lower().rstrip('.')}."

            cm.add_memory(
                tick=tick,
                event_type=actual_type,
                description=ev_desc,
                narrative=narrative,
                emotional_charge=charge,
                territory_id=tid,
                importance=imp,
            )

        # Cria memórias de descobertas tecnológicas
        if self.technology:
            for tech in self.technology.technologies.values():
                if tech.discovery_tick == tick:
                    cm.add_memory(
                        tick=tick,
                        event_type="discovery",
                        description=f"Descoberta: {tech.name}",
                        narrative=f"Contam que foi na era {tech.era} que {tech.name} foi revelado ao mundo.",
                        emotional_charge={"joy": 0.7, "curiosity": 0.6, "trust": 0.3},
                        importance=0.7,
                    )

        # Cria memórias de novas religiões
        for rel in self.religion_system.religions.values():
            mem_key = f"religion_{rel.name}"
            has_mem = any(
                m.event_type == "religion_founded" and m.description == rel.name
                for m in cm.memories
            )
            if not has_mem and len(rel.followers) >= 3:
                cm.add_memory(
                    tick=tick,
                    event_type="religion_founded",
                    description=rel.name,
                    narrative=f"Surgiu entre nós a crença em {rel.name}, unindo corações em torno de {rel.beliefs[0] if rel.beliefs else 'fé'}.",
                    emotional_charge={"joy": 0.5, "trust": 0.4, "fear": -0.2},
                    religion_id=rel.name,
                    importance=0.6,
                )

        # Atualiza atores narrativos
        cm.actor_step(tick)
        # Re-registra atores periodicamente (audience muda)
        if tick > 0 and tick % 50 == 0:
            self._register_narrative_actors()
        # Computa identidade da civilização
        total_techs = len(self.technology.technologies) if self.technology else 1
        discovered = sum(
            1 for t in (self.technology.technologies.values() if self.technology else [])
            if t.discovered
        )
        cm.compute_identity(tech_discovered=discovered, total_techs=total_techs)

    def _record_narratives_for_events(self):
        if not hasattr(self, '_last_narrated_ids'):
            self._last_narrated_ids = set()
        for event in self.world.state.events[-5:]:
            event_id = (event.get("tick", 0), event.get("type", ""), event.get("description", ""))
            if event_id not in self._last_narrated_ids:
                self.narratives.record_event(event)
                self.narratives.generate_narratives(event, self.agents, event.get("tick", 0))
                self._last_narrated_ids.add(event_id)
        if len(self._last_narrated_ids) > 200:
            self._last_narrated_ids = set(list(self._last_narrated_ids)[-100:])

    def _process_action(self, agent: Agent, action: str, tick: int):
        handler = _ACTION_HANDLERS.get(action)
        if handler is not None:
            handler(self, agent, tick)
        elif action.startswith("discovered:"):
            pass
        elif action.startswith("idea:"):
            pass
        elif action.startswith("published:"):
            pass

    def _update_economy(self):
        self.economy.step(self)

    def _age_agents(self):
        for agent in self.agents.values():
            if agent.state.is_alive:
                agent.state.age += 1
                if agent.state.age in (10, 50, 100, 200, 500):
                    agent.state.add_life_event(
                        agent.state.age, "milestone",
                        f"Reached age {agent.state.age}", 0.4,
                    )
                if agent.state.wealth > 1000 and "amassed_fortune" not in agent.state.notable_achievements:
                    agent.state.notable_achievements.append("amassed_fortune")
                    agent.state.add_life_event(
                        self.world.state.tick, "wealth",
                        "Amassed a fortune", 0.7,
                    )
                if agent.state.influence > 0.8 and "became_influential" not in agent.state.notable_achievements:
                    agent.state.notable_achievements.append("became_influential")
                    agent.state.add_life_event(
                        self.world.state.tick, "influence",
                        "Became highly influential", 0.7,
                    )
                if agent.state.age > 500 and self.rng.random() < 0.01:
                    agent.state.is_alive = False
                    self.audit_recorder.record_agent_died(
                        self.world.state.tick, agent.agent_id,
                        agent.state.name, agent.state.agent_class,
                        agent.state.age, agent.state.wealth,
                    )
                    self.world.log_event(
                        "death",
                        f"{agent.state.name} ({agent.state.agent_class}) has died at age {agent.state.age}.",
                        {"agent_id": agent.agent_id},
                    )

    def _cleanup_dead(self):
        pass

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self.agents.get(agent_id)

    def summary(self) -> dict:
        return {
            "world": self.world.summary(),
            "economy": self.economy.summary(),
            "governance": self.governance.summary(),
            "metrics": self.metrics.summary(),
            "culture": {
                "beliefs": self.belief_system.summary(),
                "memes": self.meme_pool.summarize(),
                "religion": self.religion_system.summary(),
                "ideologies": self.ideology_system.summary(),
                "emergent_ideologies": self.world.ideology_manager.to_dict(),
            },
            "technology": self.technology.summary(),
            "diplomacy": self.diplomacy.summary(),
            "stratification": self.stratification.summary(),
            "history": self.narratives.summary(),
            "events": self.event_system.summary(),
            "agents": {
                "total": len(self.agents),
                "alive": sum(1 for a in self.agents.values() if a.state.is_alive),
                "by_class": self._agent_class_distribution(),
            },
            "external_agents": self.pap.summary(),
            "collective_memory": self.collective_memory.summarize(),
            "civilization": self.civilization_index(),
        }

    def _agent_class_distribution(self) -> dict:
        dist = {}
        for agent in self.agents.values():
            cls = agent.state.agent_class
            dist[cls] = dist.get(cls, 0) + 1
        return dist

    def civilization_index(self) -> dict:
        alive = [a for a in self.agents.values() if a.state.is_alive]
        total = len(self.agents)

        avg_education = sum(a.state.education_level for a in alive) / max(1, len(alive))
        avg_wealth = sum(a.state.wealth for a in alive) / max(1, len(alive))
        avg_happiness = sum(a.emotions.happiness for a in alive) / max(1, len(alive))

        tech = self.technology.get_tech_level() if self.technology else 0.3
        stability = self.governance.government.stability if self.governance else 0.5
        ineq = self.economy.indicators.inequality if self.economy else 0.5
        religious_count = sum(
            len(r.followers) for r in self.religion_system.religions.values()
        ) if self.religion_system else 0
        ideology_count = len(self.ideology_system.ideologies) if self.ideology_system else 0

        cultural_complexity = min(1.0, (
            len(self.belief_system.values) * 0.1 +
            len(self.meme_pool.memes) * 0.05 +
            len(self.religion_system.religions) * 0.15 +
            ideology_count * 0.1 +
            len(self.narratives.narratives) * 0.05 +
            self.technology.get_tech_level() * 0.2
        ) / 5.0)

        institutions = stability * 0.5 + self.governance.government.legitimacy * 0.3 + 0.2

        age_name = self.technology.get_era().title() if self.technology else "Primordial"

        return {
            "age": age_name,
            "population": len(alive),
            "technology": round(tech, 3),
            "stability": round(stability, 3),
            "culture_complexity": round(cultural_complexity, 3),
            "institutional_maturity": round(institutions, 3),
            "avg_education": round(avg_education, 3),
            "avg_wealth": round(avg_wealth, 2),
            "avg_happiness": round(avg_happiness, 3),
            "inequality": round(ineq, 3),
            "religions": len(self.religion_system.religions),
            "ideologies": ideology_count,
            "factions": len(self.diplomacy.factions),
            "technologies_discovered": self.technology.summary().get("discovered", 0) if self.technology else 0,
            "external_agents": len(self.pap.external_agents) if self.pap else 0,
        }
