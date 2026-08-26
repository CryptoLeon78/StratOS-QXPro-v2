"""Prosa de PARTE 12 ("corte de red 10 min"). A diferencia de los otros 4
escenarios, este NO es un timeline de `Mt5ClientProtocol` -- envuelve la
capa HTTP del conector (`httpx.AsyncBaseTransport`), no el cliente MT5.
Las primeras `fail_calls` peticiones fallan con `httpx.ConnectError`, luego
la conexion se restablece delegando al transport real -- el mecanismo que
`mt5-connector/tests` e `integration-tests` usan para probar el criterio
de salida de G4 ("corte de 10 min sin perdidas ni duplicados") sin un
sleep real de 10 minutos."""

import httpx


class FlakyTransport(httpx.AsyncBaseTransport):
    def __init__(self, wrapped: httpx.AsyncBaseTransport, fail_calls: int) -> None:
        self._wrapped = wrapped
        self._fail_calls = fail_calls
        self.attempts = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.attempts += 1
        if self.attempts <= self._fail_calls:
            raise httpx.ConnectError("corte de red simulado", request=request)
        return await self._wrapped.handle_async_request(request)
