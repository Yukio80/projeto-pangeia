from __future__ import annotations

import random
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pangeia.core.agent import Agent


class Message:
    def __init__(self, sender_id: str, content: str,
                 message_type: str = "general",
                 truth_value: Optional[bool] = None,
                 target_ids: Optional[List[str]] = None):
        self.sender_id = sender_id
        self.content = content
        self.message_type = message_type
        self.truth_value = truth_value
        self.target_ids = target_ids or []


class CommunicationSystem:
    def __init__(self):
        self.channels: Dict[str, List[Message]] = {
            "public": [],
            "media": [],
            "whisper": [],
        }

    def broadcast(self, message: Message, agents: Dict[str, "Agent"],
                  tick: int, max_targets: int = 20):
        self.channels["public"].append(message)
        target_ids = message.target_ids or list(agents.keys())
        if len(target_ids) > max_targets:
            # Media messages get more targets
            limit = 30 if message.message_type == "media" else max_targets
            import random
            target_ids = random.sample(target_ids, limit)
        for tid in target_ids:
            if tid in agents:
                recipient = agents[tid]
                importance = 0.3
                if message.message_type == "media":
                    importance = 0.5
                recipient.memory.remember(
                    f"Heard from {message.sender_id}: {message.content}",
                    memory_type="communication",
                    importance=importance,
                    timestamp=float(tick),
                )
                if message.truth_value is not None:
                    recipient.knowledge.add_shared_knowledge(
                        proposition=message.content,
                        confidence=0.4 if message.truth_value else 0.1,
                        source=message.sender_id,
                    )

    def spread_rumor(self, content: str, truth_value: bool,
                     agents: Dict[str, "Agent"],
                     spreaders: List[str]):
        for sid in spreaders:
            if sid in agents:
                msg = Message(
                    sender_id=sid,
                    content=content,
                    message_type="whisper",
                    truth_value=truth_value,
                )
                for tid, agent in agents.items():
                    if tid != sid and random.random() < 0.3:
                        recipient = agent
                        recipient.memory.remember(
                            f"Rumor from {sid}: {content}",
                            memory_type="rumor",
                            importance=0.4,
                            timestamp=float(random.randint(0, 100)), # Placeholder - need tick
                        )
                        recipient.knowledge.add_shared_knowledge(
                            proposition=content,
                            confidence=random.uniform(0.2, 0.6),
                            source=sid,
                            truth_value=truth_value,
                        )
