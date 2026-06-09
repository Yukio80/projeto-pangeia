from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MemoryItem:
    timestamp: float
    content: str
    memory_type: str
    importance: float
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def decay(self, current_time: float, decay_rate: float = 0.001) -> float:
        age = current_time - self.timestamp
        return self.importance * (1.0 - decay_rate * age)


class Memory:
    def __init__(self, capacity: int = 200):
        self.capacity = capacity
        self.short_term: deque = deque(maxlen=capacity)
        self.long_term: deque = deque(maxlen=capacity // 2)

    def remember(self, content: str, memory_type: str = "experience",
                 importance: float = 0.5, tags: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 timestamp: Optional[float] = None):
        item = MemoryItem(
            timestamp=timestamp or time.time(),
            content=content,
            memory_type=memory_type,
            importance=min(1.0, max(0.0, importance)),
            tags=tags or [],
            metadata=metadata or {},
        )
        self.short_term.append(item)
        if importance > 0.7:
            self.long_term.append(item)

    def recall(self, query: Optional[str] = None,
               memory_type: Optional[str] = None,
               min_importance: float = 0.0,
               limit: int = 10) -> List[MemoryItem]:
        results = []
        for item in list(self.short_term) + list(self.long_term):
            if memory_type and item.memory_type != memory_type:
                continue
            if item.importance < min_importance:
                continue
            if query and query.lower() not in item.content.lower():
                continue
            results.append(item)
        results.sort(key=lambda x: x.importance, reverse=True)
        return results[:limit]

    def recent(self, n: int = 10) -> List[MemoryItem]:
        combined = list(self.short_term) + list(self.long_term)
        combined.sort(key=lambda x: x.timestamp, reverse=True)
        return combined[:n]

    def summarize(self) -> dict:
        return {
            "short_term": len(self.short_term),
            "long_term": len(self.long_term),
            "capacity": self.capacity,
            "utilization": (len(self.short_term) + len(self.long_term)) / max(1, self.capacity),
        }
