import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any


class EventBus:
    """In-process pub/sub bus used by API, scheduler, and device manager."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, topic: str, event: dict[str, Any]) -> None:
        async with self._lock:
            subscribers = list(self._subscribers.get(topic, set()))
        for queue in subscribers:
            if queue.full():
                _ = queue.get_nowait()
            queue.put_nowait(event)

    async def subscribe(self, topic: str, maxsize: int = 250) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=maxsize)
        async with self._lock:
            self._subscribers[topic].add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            async with self._lock:
                self._subscribers[topic].discard(queue)


event_bus = EventBus()
