from __future__ import annotations

from typing import Dict, List, Optional

from pangeia.persistence.event_types import Event, EventType
from pangeia.persistence.event_store import AuditLog


class AuditRecorder:
    def __init__(self, store: AuditLog, enabled: bool = True):
        self.store = store
        self.enabled = enabled
        self._batch: List[Event] = []

    def set_enabled(self, enabled: bool):
        self.enabled = enabled

    def _emit(self, event: Event):
        if not self.enabled:
            return
        self._batch.append(event)
        if len(self._batch) >= 100:
            self.flush()

    def flush(self):
        if not self._batch:
            return
        self.store.append_batch(self._batch)
        self._batch.clear()

    def record_tick(self, tick: int, metrics: dict):
        self._emit(Event(
            tick=tick,
            event_type=EventType.TICK,
            aggregate_type="world",
            aggregate_id="pangeia",
            data={"metrics": metrics},
        ))

    def record_agent_created(self, tick: int, agent_id: str, name: str,
                              agent_class: str, territory_id: int,
                              personality: Optional[dict] = None,
                              archetype: str = "",
                              contradictions: Optional[List[str]] = None):
        self._emit(Event(
            tick=tick,
            event_type=EventType.AGENT_CREATED,
            aggregate_type="agent",
            aggregate_id=agent_id,
            data={
                "agent_id": agent_id,
                "name": name,
                "class": agent_class,
                "territory_id": territory_id,
                "personality": personality or {},
                "archetype": archetype,
                "contradictions": contradictions or [],
            },
        ))

    def record_agent_died(self, tick: int, agent_id: str, name: str,
                           agent_class: str, age: int, wealth: float):
        self._emit(Event(
            tick=tick,
            event_type=EventType.AGENT_DIED,
            aggregate_type="agent",
            aggregate_id=agent_id,
            data={
                "agent_id": agent_id,
                "name": name,
                "class": agent_class,
                "age": age,
                "wealth": round(wealth, 2),
            },
        ))

    def record_agent_action(self, tick: int, agent_id: str, action: str,
                             agent_class: str):
        self._emit(Event(
            tick=tick,
            event_type=EventType.AGENT_ACTION,
            aggregate_type="agent",
            aggregate_id=agent_id,
            data={
                "agent_id": agent_id,
                "action": action,
                "class": agent_class,
            },
        ))

    def record_company_created(self, tick: int, company_id: str,
                                name: str, owner_id: str, industry: str):
        self._emit(Event(
            tick=tick,
            event_type=EventType.COMPANY_CREATED,
            aggregate_type="company",
            aggregate_id=company_id,
            data={
                "company_id": company_id,
                "name": name,
                "owner_id": owner_id,
                "industry": industry,
            },
        ))

    def record_company_closed(self, tick: int, company_id: str, name: str):
        self._emit(Event(
            tick=tick,
            event_type=EventType.COMPANY_CLOSED,
            aggregate_type="company",
            aggregate_id=company_id,
            data={
                "company_id": company_id,
                "name": name,
            },
        ))

    def record_election(self, tick: int, winner_id: str, winner_name: str,
                         total_votes: int, turnout: float):
        self._emit(Event(
            tick=tick,
            event_type=EventType.ELECTION_HELD,
            aggregate_type="governance",
            aggregate_id="pangeia",
            data={
                "winner_id": winner_id,
                "winner_name": winner_name,
                "total_votes": total_votes,
                "turnout": round(turnout, 3),
            },
        ))

    def record_law_proposed(self, tick: int, law_id: str, name: str,
                             category: str, proposer_id: str):
        self._emit(Event(
            tick=tick,
            event_type=EventType.LAW_PROPOSED,
            aggregate_type="governance",
            aggregate_id="pangeia",
            data={
                "law_id": law_id,
                "name": name,
                "category": category,
                "proposer_id": proposer_id,
            },
        ))

    def record_religion_founded(self, tick: int, religion_id: str,
                                 name: str, founder_id: str, beliefs: list):
        self._emit(Event(
            tick=tick,
            event_type=EventType.RELIGION_FOUNDED,
            aggregate_type="religion",
            aggregate_id=religion_id,
            data={
                "religion_id": religion_id,
                "name": name,
                "founder_id": founder_id,
                "beliefs": beliefs,
            },
        ))

    def record_religion_schism(self, tick: int, parent_id: str,
                                parent_name: str, new_id: str,
                                new_name: str, belief: str):
        self._emit(Event(
            tick=tick,
            event_type=EventType.RELIGION_SCHISM,
            aggregate_type="religion",
            aggregate_id=new_id,
            data={
                "parent_id": parent_id,
                "parent_name": parent_name,
                "new_id": new_id,
                "new_name": new_name,
                "belief": belief,
            },
        ))

    def record_ideology_created(self, tick: int, ideology_id: str,
                                 name: str, values: dict):
        self._emit(Event(
            tick=tick,
            event_type=EventType.IDEOLOGY_CREATED,
            aggregate_type="ideology",
            aggregate_id=ideology_id,
            data={
                "ideology_id": ideology_id,
                "name": name,
                "values": values,
            },
        ))

    def record_technology_discovered(self, tick: int, tech_id: str,
                                      name: str, era: str,
                                      researcher_id: str):
        self._emit(Event(
            tick=tick,
            event_type=EventType.TECHNOLOGY_DISCOVERED,
            aggregate_type="technology",
            aggregate_id=tech_id,
            data={
                "tech_id": tech_id,
                "name": name,
                "era": era,
                "researcher_id": researcher_id,
            },
        ))

    def record_faction_created(self, tick: int, faction_id: str,
                                name: str, faction_type: str,
                                leader_id: str):
        self._emit(Event(
            tick=tick,
            event_type=EventType.FACTION_CREATED,
            aggregate_type="faction",
            aggregate_id=faction_id,
            data={
                "faction_id": faction_id,
                "name": name,
                "type": faction_type,
                "leader_id": leader_id,
            },
        ))

    def record_conflict(self, tick: int, faction1_id: str,
                         faction1_name: str, faction2_id: str,
                         faction2_name: str):
        self._emit(Event(
            tick=tick,
            event_type=EventType.CONFLICT_STARTED,
            aggregate_type="diplomacy",
            aggregate_id=f"{faction1_id}_vs_{faction2_id}",
            data={
                "faction1_id": faction1_id,
                "faction1_name": faction1_name,
                "faction2_id": faction2_id,
                "faction2_name": faction2_name,
            },
        ))

    def record_random_event(self, tick: int, event_type_name: str,
                             name: str, severity: float):
        self._emit(Event(
            tick=tick,
            event_type=EventType.RANDOM_EVENT_OCCURRED,
            aggregate_type="event",
            aggregate_id=f"event_{tick}",
            data={
                "event_type": event_type_name,
                "name": name,
                "severity": round(severity, 3),
            },
        ))

    def record_world_event(self, tick: int, event_type: str,
                            description: str, event_data: dict):
        self._emit(Event(
            tick=tick,
            event_type=EventType.WORLD_EVENT,
            aggregate_type="world",
            aggregate_id="pangeia",
            data={
                "event_type": event_type,
                "description": description,
                "data": event_data,
            },
        ))

    def record_external_agent_registered(self, tick: int, agent_id: str,
                                          name: str, capabilities: list):
        self._emit(Event(
            tick=tick,
            event_type=EventType.EXTERNAL_AGENT_REGISTERED,
            aggregate_type="external_agent",
            aggregate_id=agent_id,
            data={
                "agent_id": agent_id,
                "name": name,
                "capabilities": capabilities,
            },
        ))
