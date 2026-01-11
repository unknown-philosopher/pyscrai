import asyncio
import unittest

from forge.core.event_bus import EventBus


class EventBusTest(unittest.IsolatedAsyncioTestCase):
    async def test_publish_delivers_payload(self) -> None:
        bus = EventBus()
        seen = []

        async def handler(payload):
            seen.append(payload)

        await bus.subscribe("demo", handler)
        await bus.publish("demo", {"value": 42})
        await asyncio.sleep(0)  # allow scheduled tasks to run

        self.assertEqual(seen, [{"value": 42}])

    async def test_clear_drops_subscriptions(self) -> None:
        bus = EventBus()
        seen = []

        async def handler(payload):
            seen.append(payload)

        await bus.subscribe("demo", handler)
        bus.clear()
        await bus.publish("demo", {"value": 1})
        await asyncio.sleep(0)

        self.assertEqual(seen, [])

    async def test_handler_failure_isolated(self) -> None:
        bus = EventBus()
        seen = []

        async def bad_handler(payload):
            raise RuntimeError("boom")

        async def good_handler(payload):
            seen.append(payload.get("value"))

        await bus.subscribe("demo", bad_handler)
        await bus.subscribe("demo", good_handler)
        await bus.publish("demo", {"value": 7})
        await asyncio.sleep(0)

        self.assertEqual(seen, [7])


if __name__ == "__main__":
    unittest.main()
