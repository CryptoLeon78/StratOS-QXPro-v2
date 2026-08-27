from datetime import UTC, datetime, timedelta

import fakeredis
import pytest

from core.auth.revocation import is_revoked, revoke_jti


@pytest.mark.asyncio
async def test_a_fresh_jti_is_not_revoked() -> None:
    redis = fakeredis.FakeAsyncRedis()
    assert await is_revoked(redis, "some-jti") is False


@pytest.mark.asyncio
async def test_revoking_a_jti_makes_it_report_as_revoked() -> None:
    redis = fakeredis.FakeAsyncRedis()
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=15)

    await revoke_jti(redis, "some-jti", exp, now)

    assert await is_revoked(redis, "some-jti") is True


@pytest.mark.asyncio
async def test_revocation_ttl_matches_the_time_left_until_expiry_never_longer() -> None:
    redis = fakeredis.FakeAsyncRedis()
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=15)

    await revoke_jti(redis, "some-jti", exp, now)

    ttl = await redis.ttl("revoked:some-jti")
    assert 0 < ttl <= 15 * 60


@pytest.mark.asyncio
async def test_revoking_an_already_expired_token_is_a_no_op_never_a_negative_ttl() -> None:
    """Un token ya vencido no necesita denylist -- decode_token ya lo
    rechaza por expiry antes de llegar aqui. Nunca debe intentar un
    SETEX con TTL<=0 (Redis lo rechazaria con un ResponseError)."""
    redis = fakeredis.FakeAsyncRedis()
    now = datetime.now(UTC)
    exp = now - timedelta(minutes=1)

    await revoke_jti(redis, "some-jti", exp, now)

    assert await is_revoked(redis, "some-jti") is False


@pytest.mark.asyncio
async def test_revocation_is_scoped_to_its_own_jti() -> None:
    redis = fakeredis.FakeAsyncRedis()
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=15)

    await revoke_jti(redis, "revoked-one", exp, now)

    assert await is_revoked(redis, "another-jti") is False
