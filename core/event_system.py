"""
Event System

Implements inter-plugin communication through events as defined in ADR-0028.
"""

import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List


@dataclass
class Event:
    """Represents an event in the system"""

    name: str
    data: Dict[str, Any]
    timestamp: datetime
    source: str = "system"


class EventSystem:
    """
    Event-driven communication system for plugins

    Provides publish-subscribe pattern for loose coupling between
    plugins and system components.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_history: List[Event] = []
        self._lock = threading.RLock()

    def emit(
        self, event_name: str, data: Dict[str, Any] = None, source: str = "system"
    ) -> None:
        """
        Emit an event to all registered listeners

        Args:
            event_name: Name of the event
            data: Event data payload
            source: Source of the event
        """
        data = data or {}
        event = Event(
            name=event_name, data=data, timestamp=datetime.now(), source=source
        )

        with self._lock:
            # Store event in history
            self._event_history.append(event)

            # Notify subscribers
            if event_name in self._subscribers:
                for callback in self._subscribers[event_name]:
                    try:
                        callback(event)
                    except Exception as e:
                        self.logger.error(
                            f"Error in event callback for {event_name}: {e}"
                        )

        self.logger.debug(f"Emitted event: {event_name} from {source}")

    def subscribe(self, event_name: str, callback: Callable[[Event], None]) -> None:
        """
        Subscribe to specific events

        Args:
            event_name: Name of the event to subscribe to
            callback: Function to call when event is emitted
        """
        with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            self._subscribers[event_name].append(callback)

        self.logger.debug(f"Subscribed to event: {event_name}")

    def unsubscribe(self, event_name: str, callback: Callable[[Event], None]) -> bool:
        """
        Unsubscribe from an event

        Args:
            event_name: Name of the event
            callback: Callback function to remove

        Returns:
            bool: True if callback was removed, False if not found
        """
        with self._lock:
            if event_name in self._subscribers:
                try:
                    self._subscribers[event_name].remove(callback)
                    if not self._subscribers[event_name]:
                        del self._subscribers[event_name]
                    return True
                except ValueError:
                    pass
        return False

    def get_subscribers(self, event_name: str) -> List[Callable]:
        """Get list of subscribers for an event"""
        with self._lock:
            return self._subscribers.get(event_name, []).copy()

    def get_event_history(
        self, event_name: str = None, limit: int = 100
    ) -> List[Event]:
        """
        Get event history

        Args:
            event_name: Filter by event name (None for all events)
            limit: Maximum number of events to return

        Returns:
            List[Event]: List of events
        """
        with self._lock:
            events = self._event_history

            if event_name:
                events = [e for e in events if e.name == event_name]

            # Return most recent events first
            return events[-limit:][::-1]

    def clear_history(self) -> None:
        """Clear event history"""
        with self._lock:
            self._event_history.clear()

    def get_statistics(self) -> Dict[str, Any]:
        """Get event system statistics"""
        with self._lock:
            event_counts = {}
            for event in self._event_history:
                event_counts[event.name] = event_counts.get(event.name, 0) + 1

            return {
                "total_events": len(self._event_history),
                "unique_event_types": len(set(e.name for e in self._event_history)),
                "active_subscriptions": len(self._subscribers),
                "event_counts": event_counts,
                "subscribers_by_event": {
                    event_name: len(callbacks)
                    for event_name, callbacks in self._subscribers.items()
                },
            }
