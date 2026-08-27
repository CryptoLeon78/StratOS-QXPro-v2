import httpx
import pytest

from gateway.proxy import forward_request


def _echo_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "body": request.content.decode() if request.content else "",
        },
    )


def _make_client(handler: httpx.MockTransport | None = None) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler or _echo_handler))


@pytest.mark.asyncio
async def test_forwards_method_path_and_query_to_upstream_base_url() -> None:
    async with _make_client() as client:
        response = await forward_request(
            method="GET",
            path="api/v1/header/summary",
            query="range=30d",
            headers={},
            body=b"",
            client=client,
            upstream_base_url="http://core-engine:8000",
        )
    body = response.json()
    assert body["method"] == "GET"
    assert body["url"] == "http://core-engine:8000/api/v1/header/summary?range=30d"


@pytest.mark.asyncio
async def test_forwards_authorization_header_and_body_intact() -> None:
    async with _make_client() as client:
        response = await forward_request(
            method="POST",
            path="auth/token",
            query="",
            headers={"authorization": "Bearer abc123", "content-type": "application/json"},
            body=b'{"foo":"bar"}',
            client=client,
            upstream_base_url="http://core-engine:8000",
        )
    body = response.json()
    assert body["headers"]["authorization"] == "Bearer abc123"
    assert body["body"] == '{"foo":"bar"}'


@pytest.mark.asyncio
async def test_strips_stale_host_and_hop_by_hop_headers_before_forwarding() -> None:
    async with _make_client() as client:
        response = await forward_request(
            method="GET",
            path="health",
            query="",
            headers={
                "host": "gateway.local",
                "proxy-authorization": "should-never-reach-upstream",
                "x-custom": "kept",
            },
            body=b"",
            client=client,
            upstream_base_url="http://core-engine:8000",
        )
    body = response.json()
    # httpx recalcula Host desde la URL destino, no reenvia el original.
    assert body["headers"]["host"] == "core-engine:8000"
    assert "proxy-authorization" not in body["headers"]
    assert body["headers"]["x-custom"] == "kept"


@pytest.mark.asyncio
async def test_does_not_follow_redirects_leaves_that_to_the_real_client() -> None:
    def _redirecting_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(307, headers={"location": "/somewhere-else"})

    async with _make_client(_redirecting_handler) as client:
        response = await forward_request(
            method="GET",
            path="whatever",
            query="",
            headers={},
            body=b"",
            client=client,
            upstream_base_url="http://core-engine:8000",
        )
    assert response.status_code == 307
    assert response.headers["location"] == "/somewhere-else"
