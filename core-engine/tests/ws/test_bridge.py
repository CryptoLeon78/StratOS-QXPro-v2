import asyncio

import fakeredis

from core.ws.bridge import TOPIC_MAP, stream_topics


class TestTopicMap:
    def test_covers_the_eight_contractual_topics(self) -> None:
        all_topics = {topic for topics in TOPIC_MAP.values() for topic in topics}
        assert all_topics == {
            "events:equity",
            "events:trade",
            "events:alert",
            "events:decision",
            "events:pipeline",
            "events:semaphore",
            "events:killswitch",
            "events:heartbeat",
        }

    def test_covers_the_four_contractual_endpoints(self) -> None:
        assert set(TOPIC_MAP.keys()) == {"/ws/equity", "/ws/alerts", "/ws/pipeline", "/ws/health"}


class TestStreamTopics:
    async def test_yields_only_messages_from_subscribed_topics(self) -> None:
        redis = fakeredis.FakeAsyncRedis()
        received: list[str] = []

        async def _consume() -> None:
            async for payload in stream_topics(redis, ("events:semaphore", "events:killswitch")):
                received.append(payload)
                if len(received) == 2:
                    return

        task = asyncio.create_task(_consume())
        await asyncio.sleep(0.2)
        await redis.publish("events:equity", "should-not-arrive")
        await redis.publish("events:semaphore", "semaphore-msg")
        await redis.publish("events:killswitch", "killswitch-msg")
        await asyncio.wait_for(task, timeout=2)

        assert received == ["semaphore-msg", "killswitch-msg"]
        await redis.aclose()
