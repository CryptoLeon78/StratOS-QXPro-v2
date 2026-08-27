from httpx import AsyncClient


class TestKillswitchLadder:
    async def test_returns_4_levels_matching_seed_thresholds(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/config/killswitch-ladder")
        assert response.status_code == 200
        body = response.json()
        assert [level["level"] for level in body] == [1, 2, 3, 4]
        assert [level["threshold_pct"] for level in body] == ["8", "12", "15", "20"]
        assert body[3]["instruction_text"] == "Cerrar posiciones y DESACTIVAR todos los EAs."


class TestUmsPhases:
    async def test_returns_6_phases_matching_seed(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/config/ums-phases")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 6
        assert body[3]["name"] == "Semi-Profesional"
        assert body[3]["risk_per_trade_pct_min"] == "0.3"
        assert body[3]["risk_per_trade_pct_max"] == "0.7"
        assert body[0]["risk_note"] == "micro-lotes"
        assert body[5]["equity_max"] is None


class TestPipelineGateThresholds:
    async def test_returns_the_7_gate_thresholds(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/config/pipeline-gate")
        assert response.status_code == 200
        body = response.json()
        assert body == {
            "min_trades": 30,
            "min_days": 60,
            "pf": 1.5,
            "exp": 0.15,
            "sharpe": 1.0,
            "maxdd": 20.0,
            "min_freq_week": 2.0,
            "kill_pf": 1.1,
            "marginal_band": 0.10,
        }


class TestSemaphoreInstructions:
    async def test_returns_the_3_instruction_templates(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/config/semaphore-instructions")
        assert response.status_code == 200
        body = response.json()
        assert body["verde"] == "Mantener. No tocar nada."
        assert "{magic}" in body["naranja_template"]
