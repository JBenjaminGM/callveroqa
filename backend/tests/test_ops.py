"""
Tests de operación: salud del servicio y trazabilidad de una petición.

Lo que se protege:

- que `/health` **falle** cuando la base de datos no responde. Un proceso vivo
  que no puede consultar nada está caído para el usuario, y esa diferencia es
  justo la que dejó pasar dos meses de caída en producción sin alarma.
- que cada respuesta lleve un identificador con el que encontrar sus líneas en
  el log, y que se respete el del proxy si ya viene puesto.
"""


from app.database import get_db
from app.main import app


def test_health_comprueba_la_base_de_datos(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy", "database": "ok"}


def test_health_falla_si_la_base_no_responde(client):
    class _SesionCaida:
        def execute(self, *_args, **_kwargs):
            raise RuntimeError("could not connect to server")

    anterior = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: _SesionCaida()
    try:
        r = client.get("/health")
    finally:
        if anterior is not None:
            app.dependency_overrides[get_db] = anterior
        else:
            app.dependency_overrides.pop(get_db, None)

    assert r.status_code == 503
    assert r.json()["database"] == "unreachable"


def test_cada_respuesta_trae_su_identificador(client):
    r = client.get("/health")
    request_id = r.headers.get("X-Request-ID")
    assert request_id and len(request_id) >= 8

    # Dos peticiones no comparten identificador.
    otra = client.get("/health").headers["X-Request-ID"]
    assert otra != request_id


def test_se_respeta_el_identificador_del_proxy(client):
    r = client.get("/health", headers={"X-Request-ID": "trazado-desde-render"})
    assert r.headers["X-Request-ID"] == "trazado-desde-render"
