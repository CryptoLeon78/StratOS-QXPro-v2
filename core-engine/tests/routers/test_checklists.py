from httpx import AsyncClient

from tests.routers.conftest import TEST_OPERATOR


class TestCurrentChecklist:
    async def test_returns_the_catalog_unsigned(self, api_client: AsyncClient) -> None:
        response = await api_client.get(
            "/api/v1/checklists/current", params={"checklist_type": "SUNDAY"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["completed"] is False
        assert len(body["items"]) == 4


class TestSignItem:
    async def test_signing_all_items_completes_the_checklist(self, api_client: AsyncClient) -> None:
        progress = await api_client.get(
            "/api/v1/checklists/current", params={"checklist_type": "SUNDAY"}
        )
        item_keys = [i["item_key"] for i in progress.json()["items"]]

        last_response = None
        for item_key in item_keys:
            last_response = await api_client.post(
                f"/api/v1/checklists/SUNDAY/items/{item_key}/sign"
            )
            assert last_response.status_code == 200

        assert last_response is not None
        assert last_response.json()["completed"] is True
        assert last_response.json()["progress"]["completed"] is True
        for item in last_response.json()["progress"]["items"]:
            assert item["signed_by"] == TEST_OPERATOR.email

    async def test_rejects_an_item_outside_the_catalog(self, api_client: AsyncClient) -> None:
        response = await api_client.post("/api/v1/checklists/SUNDAY/items/item-inventado/sign")
        assert response.status_code == 400
