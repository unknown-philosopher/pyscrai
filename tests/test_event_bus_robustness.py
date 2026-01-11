"""Event Bus Robustness Tests.

Tests for unsubscribe/resubscribe logic and edge cases.
"""

import asyncio
import unittest

from forge.core.event_bus import EventBus


class EventBusRobustnessTest(unittest.IsolatedAsyncioTestCase):
    """Test Event Bus robustness features."""

    async def test_unsubscribe_removes_handler(self) -> None:
        """Test that unsubscribe removes a handler and it no longer receives events."""
        bus = EventBus()
        seen = []

        async def handler(payload):
            seen.append(payload)

        await bus.subscribe("test", handler)
        await bus.publish("test", {"value": 1})
        await asyncio.sleep(0)

        self.assertEqual(len(seen), 1)

        await bus.unsubscribe("test", handler)
        await bus.publish("test", {"value": 2})
        await asyncio.sleep(0)

        self.assertEqual(len(seen), 1)  # Should still be 1
        self.assertEqual(seen[0]["value"], 1)

    async def test_unsubscribe_nonexistent_handler_silent(self) -> None:
        """Test that unsubscribing a non-existent handler doesn't raise an error."""
        bus = EventBus()

        async def handler(payload):
            pass

        # Should not raise an error
        await bus.unsubscribe("test", handler)
        await bus.unsubscribe("nonexistent", handler)

    async def test_unsubscribe_different_topic(self) -> None:
        """Test that unsubscribe only removes handler from the specified topic."""
        bus = EventBus()
        seen_topic1 = []
        seen_topic2 = []

        async def handler(payload):
            if payload.get("topic") == "topic1":
                seen_topic1.append(payload)
            else:
                seen_topic2.append(payload)

        await bus.subscribe("topic1", handler)
        await bus.subscribe("topic2", handler)

        await bus.publish("topic1", {"topic": "topic1", "value": 1})
        await bus.publish("topic2", {"topic": "topic2", "value": 2})
        await asyncio.sleep(0)

        self.assertEqual(len(seen_topic1), 1)
        self.assertEqual(len(seen_topic2), 1)

        await bus.unsubscribe("topic1", handler)

        await bus.publish("topic1", {"topic": "topic1", "value": 3})
        await bus.publish("topic2", {"topic": "topic2", "value": 4})
        await asyncio.sleep(0)

        # topic1 handler should be removed
        self.assertEqual(len(seen_topic1), 1)
        # topic2 handler should still work
        self.assertEqual(len(seen_topic2), 2)

    async def test_resubscribe_same_handler(self) -> None:
        """Test that resubscribing the same handler doesn't create duplicates."""
        bus = EventBus()
        seen = []

        async def handler(payload):
            seen.append(payload)

        await bus.subscribe("test", handler)
        await bus.subscribe("test", handler)  # Resubscribe same handler
        await bus.subscribe("test", handler)  # Again

        await bus.publish("test", {"value": 1})
        await asyncio.sleep(0)

        # Should only be called once (EventBus prevents duplicates)
        self.assertEqual(len(seen), 1)

    async def test_subscribe_unsubscribe_resubscribe(self) -> None:
        """Test the full cycle: subscribe, unsubscribe, resubscribe."""
        bus = EventBus()
        seen = []

        async def handler(payload):
            seen.append(payload)

        # Subscribe
        await bus.subscribe("test", handler)
        await bus.publish("test", {"value": 1})
        await asyncio.sleep(0)
        self.assertEqual(len(seen), 1)

        # Unsubscribe
        await bus.unsubscribe("test", handler)
        await bus.publish("test", {"value": 2})
        await asyncio.sleep(0)
        self.assertEqual(len(seen), 1)  # No new events

        # Resubscribe
        await bus.subscribe("test", handler)
        await bus.publish("test", {"value": 3})
        await asyncio.sleep(0)
        self.assertEqual(len(seen), 2)  # Should receive new event

    async def test_multiple_handlers_unsubscribe_one(self) -> None:
        """Test unsubscribing one handler while others remain active."""
        bus = EventBus()
        seen1 = []
        seen2 = []

        async def handler1(payload):
            seen1.append(payload)

        async def handler2(payload):
            seen2.append(payload)

        await bus.subscribe("test", handler1)
        await bus.subscribe("test", handler2)

        await bus.publish("test", {"value": 1})
        await asyncio.sleep(0)

        self.assertEqual(len(seen1), 1)
        self.assertEqual(len(seen2), 1)

        await bus.unsubscribe("test", handler1)

        await bus.publish("test", {"value": 2})
        await asyncio.sleep(0)

        # handler1 should not receive new event
        self.assertEqual(len(seen1), 1)
        # handler2 should still receive events
        self.assertEqual(len(seen2), 2)

    async def test_unsubscribe_after_clear(self) -> None:
        """Test that unsubscribe works correctly after clear is called."""
        bus = EventBus()
        seen = []

        async def handler(payload):
            seen.append(payload)

        await bus.subscribe("test", handler)
        bus.clear()

        # Handler should be removed by clear
        await bus.publish("test", {"value": 1})
        await asyncio.sleep(0)
        self.assertEqual(len(seen), 0)

        # Unsubscribe should not error even though handler was cleared
        await bus.unsubscribe("test", handler)

    async def test_handler_exception_does_not_affect_others(self) -> None:
        """Test that one handler exception doesn't affect other handlers."""
        bus = EventBus()
        seen = []

        async def failing_handler(payload):
            raise ValueError("Handler failed")

        async def working_handler(payload):
            seen.append(payload)

        await bus.subscribe("test", failing_handler)
        await bus.subscribe("test", working_handler)

        await bus.publish("test", {"value": 1})
        await asyncio.sleep(0.1)  # Give handlers time to execute

        # Working handler should still receive the event
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0]["value"], 1)

        # Bus should still be functional
        await bus.publish("test", {"value": 2})
        await asyncio.sleep(0.1)
        self.assertEqual(len(seen), 2)


if __name__ == "__main__":
    unittest.main()
