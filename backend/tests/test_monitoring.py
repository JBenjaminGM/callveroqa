"""
Tests de la monitorización de errores.

Sin DSN no se envía nada; con DSN, un error no controlado llega con su
`request_id` y sin datos personales. Los eventos se capturan en memoria: el
test no habla con Sentry.
"""

import sentry_sdk
from sentry_sdk.transport import Transport

from app import monitoring
from app.config import settings
from app.main import app


class _EnMemoria(Transport):
    def __init__(self, options=None):
        super().__init__(options)
        self.eventos = []

    def capture_envelope(self, envelope):
        for item in envelope.items:
            if item.type == "event":
                self.eventos.append(item.payload.json)


def test_sin_dsn_no_se_activa(monkeypatch):
    monkeypatch.setattr(settings, "sentry_dsn", "")
    assert monitoring.init_sentry() is False


def test_un_error_no_controlado_llega_con_su_request_id_y_sin_datos_personales(
    client, auth_headers, monkeypatch
):
    from fastapi.testclient import TestClient

    # El cliente de siempre relanza los errores del servidor; aquí interesa ver
    # la respuesta 500 que recibe el usuario.
    sin_relanzar = TestClient(app, raise_server_exceptions=False)
    transporte = _EnMemoria()
    monkeypatch.setattr(settings, "sentry_dsn", "https://clave@o0.ingest.sentry.io/0")
    assert monitoring.init_sentry(transport=transporte) is True

    @app.get("/api/v1/_prueba_error")
    def _falla():
        raise RuntimeError("fallo de prueba")

    try:
        r = sin_relanzar.get("/api/v1/_prueba_error", headers=auth_headers)
        assert r.status_code == 500
        request_id = r.json()["request_id"]
        sentry_sdk.flush()

        evento = next(
            e for e in transporte.eventos
            if "fallo de prueba" in str(e.get("exception"))
        )
        assert evento["tags"]["request_id"] == request_id
        cabeceras = (evento.get("request") or {}).get("headers") or {}
        # El token no viaja: Sentry manda la cabecera como «[Filtered]».
        token = auth_headers["Authorization"].split()[-1]
        assert token not in str(evento)
        assert all("Bearer" not in str(v) for v in cabeceras.values())
        assert "user" not in evento or "ip_address" not in (evento.get("user") or {})
    finally:
        app.router.routes = [
            r for r in app.router.routes if getattr(r, "path", "") != "/api/v1/_prueba_error"
        ]
        sentry_sdk.init(dsn=None)
        monitoring._activo = False
