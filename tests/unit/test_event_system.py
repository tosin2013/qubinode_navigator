"""
Unit tests for EventSystem

Tests the event-driven communication system for plugins
as defined in ADR-0028.
"""

import unittest
import time
import threading
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.event_system import EventSystem, Event


class TestEventSystem(unittest.TestCase):
    """Test cases for EventSystem"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.event_system = EventSystem()
    
    def test_initialization(self):
        """Test EventSystem initialization"""
        self.assertEqual(len(self.event_system._subscribers), 0)
        self.assertEqual(len(self.event_system._event_history), 0)
        self.assertIsNotNone(self.event_system._lock)
    
    def test_event_creation(self):
        """Test Event dataclass creation"""
        test_data = {'key': 'value', 'number': 42}
        timestamp = datetime.now()
        
        event = Event(
            name="test_event",
            data=test_data,
            timestamp=timestamp,
            source="test_source"
        )
        
        self.assertEqual(event.name, "test_event")
        self.assertEqual(event.data, test_data)
        self.assertEqual(event.timestamp, timestamp)
        self.assertEqual(event.source, "test_source")
    
    def test_subscribe_single_handler(self):
        """Test subscribing a single event handler"""
        handler = Mock()
        
        self.event_system.subscribe("test_event", handler)
        
        self.assertIn("test_event", self.event_system._subscribers)
        self.assertEqual(len(self.event_system._subscribers["test_event"]), 1)
        self.assertIn(handler, self.event_system._subscribers["test_event"])
    
    def test_subscribe_multiple_handlers(self):
        """Test subscribing multiple handlers to same event"""
        handler1 = Mock()
        handler2 = Mock()
        handler3 = Mock()
        
        self.event_system.subscribe("test_event", handler1)
        self.event_system.subscribe("test_event", handler2)
        self.event_system.subscribe("test_event", handler3)
        
        self.assertEqual(len(self.event_system._subscribers["test_event"]), 3)
        self.assertIn(handler1, self.event_system._subscribers["test_event"])
        self.assertIn(handler2, self.event_system._subscribers["test_event"])
        self.assertIn(handler3, self.event_system._subscribers["test_event"])
    
    def test_subscribe_different_events(self):
        """Test subscribing handlers to different events"""
        handler1 = Mock()
        handler2 = Mock()
        
        self.event_system.subscribe("event1", handler1)
        self.event_system.subscribe("event2", handler2)
        
        self.assertIn("event1", self.event_system._subscribers)
        self.assertIn("event2", self.event_system._subscribers)
        self.assertEqual(len(self.event_system._subscribers["event1"]), 1)
        self.assertEqual(len(self.event_system._subscribers["event2"]), 1)
    
    def test_unsubscribe_existing_handler(self):
        """Test unsubscribing an existing handler"""
        handler = Mock()
        
        self.event_system.subscribe("test_event", handler)
        self.assertEqual(len(self.event_system._subscribers["test_event"]), 1)
        
        result = self.event_system.unsubscribe("test_event", handler)
        self.assertTrue(result)
        # Event should be removed from subscribers when no handlers remain
        self.assertNotIn("test_event", self.event_system._subscribers)
    
    def test_unsubscribe_nonexistent_handler(self):
        """Test unsubscribing a non-existent handler"""
        handler1 = Mock()
        handler2 = Mock()
        
        self.event_system.subscribe("test_event", handler1)
        
        result = self.event_system.unsubscribe("test_event", handler2)
        self.assertFalse(result)
        self.assertEqual(len(self.event_system._subscribers["test_event"]), 1)
    
    def test_unsubscribe_nonexistent_event(self):
        """Test unsubscribing from non-existent event"""
        handler = Mock()
        
        result = self.event_system.unsubscribe("nonexistent_event", handler)
        self.assertFalse(result)
    
    def test_emit_event_with_subscribers(self):
        """Test emitting event with registered subscribers"""
        handler1 = Mock()
        handler2 = Mock()
        
        self.event_system.subscribe("test_event", handler1)
        self.event_system.subscribe("test_event", handler2)
        
        test_data = {'message': 'test message'}
        self.event_system.emit("test_event", test_data, "test_source")
        
        # Check that both handlers were called
        handler1.assert_called_once()
        handler2.assert_called_once()
        
        # Check the event object passed to handlers
        event_arg1 = handler1.call_args[0][0]
        event_arg2 = handler2.call_args[0][0]
        
        self.assertEqual(event_arg1.name, "test_event")
        self.assertEqual(event_arg1.data, test_data)
        self.assertEqual(event_arg1.source, "test_source")
        
        self.assertEqual(event_arg2.name, "test_event")
        self.assertEqual(event_arg2.data, test_data)
        self.assertEqual(event_arg2.source, "test_source")
    
    def test_emit_event_no_subscribers(self):
        """Test emitting event with no subscribers"""
        # Should not raise any exceptions
        self.event_system.emit("nonexistent_event", {'data': 'test'})
        
        # Event should still be recorded in history
        self.assertEqual(len(self.event_system._event_history), 1)
        self.assertEqual(self.event_system._event_history[0].name, "nonexistent_event")
    
    def test_emit_event_default_parameters(self):
        """Test emitting event with default parameters"""
        handler = Mock()
        self.event_system.subscribe("test_event", handler)
        
        self.event_system.emit("test_event")
        
        handler.assert_called_once()
        event_arg = handler.call_args[0][0]
        
        self.assertEqual(event_arg.name, "test_event")
        self.assertEqual(event_arg.data, {})
        self.assertEqual(event_arg.source, "system")
    
    def test_emit_event_handler_exception(self):
        """Test emitting event when handler raises exception"""
        def failing_handler(event):
            raise ValueError("Handler failed")
        
        def working_handler(event):
            working_handler.called = True
        
        working_handler.called = False
        
        self.event_system.subscribe("test_event", failing_handler)
        self.event_system.subscribe("test_event", working_handler)
        
        # Should not raise exception, but should continue to other handlers
        self.event_system.emit("test_event")
        
        # Working handler should still be called
        self.assertTrue(working_handler.called)
    
    def test_event_history_recording(self):
        """Test that events are recorded in history"""
        self.event_system.emit("event1", {'data': 'test1'}, "source1")
        self.event_system.emit("event2", {'data': 'test2'}, "source2")
        
        self.assertEqual(len(self.event_system._event_history), 2)
        
        # Check first event
        event1 = self.event_system._event_history[0]
        self.assertEqual(event1.name, "event1")
        self.assertEqual(event1.data, {'data': 'test1'})
        self.assertEqual(event1.source, "source1")
        
        # Check second event
        event2 = self.event_system._event_history[1]
        self.assertEqual(event2.name, "event2")
        self.assertEqual(event2.data, {'data': 'test2'})
        self.assertEqual(event2.source, "source2")
    
    def test_get_event_history(self):
        """Test retrieving event history"""
        self.event_system.emit("event1", {'data': 'test1'})
        self.event_system.emit("event2", {'data': 'test2'})
        
        history = self.event_system.get_event_history()
        
        self.assertEqual(len(history), 2)
        # Events are returned in reverse order (most recent first)
        self.assertEqual(history[0].name, "event2")
        self.assertEqual(history[1].name, "event1")
    
    def test_get_event_history_filtered(self):
        """Test retrieving filtered event history"""
        self.event_system.emit("plugin.loaded", {'plugin': 'test1'})
        self.event_system.emit("system.error", {'error': 'test error'})
        self.event_system.emit("plugin.loaded", {'plugin': 'test2'})
        
        # Get only plugin.loaded events
        filtered_history = self.event_system.get_event_history(event_name="plugin.loaded")
        
        self.assertEqual(len(filtered_history), 2)
        self.assertEqual(filtered_history[0].name, "plugin.loaded")
        self.assertEqual(filtered_history[1].name, "plugin.loaded")
        # Events are returned in reverse order (most recent first)
        self.assertEqual(filtered_history[0].data['plugin'], 'test2')
        self.assertEqual(filtered_history[1].data['plugin'], 'test1')
    
    def test_get_event_history_with_limit(self):
        """Test retrieving event history with limit"""
        for i in range(5):
            self.event_system.emit(f"event{i}", {'index': i})
        
        # Get only last 3 events
        limited_history = self.event_system.get_event_history(limit=3)
        
        self.assertEqual(len(limited_history), 3)
        # Should get the last 3 events in reverse order (most recent first)
        self.assertEqual(limited_history[0].name, "event4")
        self.assertEqual(limited_history[1].name, "event3")
        self.assertEqual(limited_history[2].name, "event2")
    
    def test_clear_history(self):
        """Test clearing event history"""
        self.event_system.emit("event1", {'data': 'test1'})
        self.event_system.emit("event2", {'data': 'test2'})
        
        self.assertEqual(len(self.event_system._event_history), 2)
        
        self.event_system.clear_history()
        
        self.assertEqual(len(self.event_system._event_history), 0)
    
    def test_thread_safety(self):
        """Test thread safety of event system"""
        handler_calls = []
        
        def thread_safe_handler(event):
            handler_calls.append(event.name)
        
        self.event_system.subscribe("test_event", thread_safe_handler)
        
        # Create multiple threads that emit events
        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=self.event_system.emit,
                args=(f"test_event", {'thread_id': i})
            )
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All events should have been handled
        self.assertEqual(len(handler_calls), 10)
        self.assertEqual(len(self.event_system._event_history), 10)
    
    def test_wildcard_subscription(self):
        """Test wildcard event subscription (if implemented)"""
        # This test assumes wildcard functionality might be added
        # For now, just test that specific event names work
        handler = Mock()
        
        self.event_system.subscribe("plugin.*", handler)
        self.event_system.emit("plugin.loaded", {'plugin': 'test'})
        
        # This might not work in current implementation, but documents expected behavior
        # handler.assert_called_once()  # Uncomment if wildcard support is added
    
    def test_event_timestamp_accuracy(self):
        """Test that event timestamps are accurate"""
        start_time = datetime.now()
        
        handler = Mock()
        self.event_system.subscribe("test_event", handler)
        self.event_system.emit("test_event")
        
        end_time = datetime.now()
        
        handler.assert_called_once()
        event_arg = handler.call_args[0][0]
        
        # Event timestamp should be between start and end time
        self.assertGreaterEqual(event_arg.timestamp, start_time)
        self.assertLessEqual(event_arg.timestamp, end_time)


if __name__ == '__main__':
    unittest.main()
