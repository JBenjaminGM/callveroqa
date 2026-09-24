"""
Tests de retención de grabaciones y supresión de datos.

Lo que se protege:

- que la retención caduque **el audio y no la evaluación**: la transcripción y
  la nota son el valor del producto y no son una grabación de voz;
- que con la política desactivada (0 días) no se borre nada, que es el valor
  por defecto y el que evita perder datos por actualizar;
- que reproducir un audio caducado explique qué pasó en vez de parecer un fallo;
- que suprimir los datos de una persona sea **de administrador** y se lleve todo
  lo suyo.
"""

from datetime import date, datetime, timedelta

from app.models.analysis import Analysis
from app.models.call import Call, CallStatus
from app.models.transcription import Transcription
from app.services import retention_service


class _AlmacenFalso:
    """Almacenamiento en memoria: registra qué se borró."""

    def __init__(self):
        self.borrados: list[str] = []
        self.falla = False

    def save(self, content, filename):
        return f"local://{filename}"

    def load(self, url):
        return b"audio"

    def delete(self, url):
        if self.falla:
            raise RuntimeError("el archivo ya no está")
        self.borrados.append(url)


def _llamada(db, uploaded_by, *, dias_atras: int, agent_id=None):
    momento = datetime.now() - timedelta(days=dias_atras)
    call = Call(
        uploaded_by=uploaded_by,
        audio_url=f"local://audio-{dias_atras}-{agent_id}.mp3",
        audio_filename="a.mp3",
        status=CallStatus.DONE,
        call_date=date.today() - timedelta(days=dias_atras),
        created_at=momento,
        agent_id=agent_id,
        duration_seconds=60,
    )
    db.add(call)
    db.flush()
    db.add(Transcription(call_id=call.id, full_text="hola", segments=[]))
    db.add(
        Analysis(
            call_id=call.id,
            global_score=80,
            dimension_scores={"greeting": 80},
            recommendations=[],
        )
    )
    db.commit()
    return call


def _con_almacen(monkeypatch):
    almacen = _AlmacenFalso()
    monkeypatch.setattr(retention_service, "get_storage_provider", lambda: almacen)
    return almacen


# ===============================================================
# Política de retención
# ===============================================================
def test_sin_politica_no_se_borra_nada(client, auth_headers, db_session, admin_user, monkeypatch):
    almacen = _con_almacen(monkeypatch)
    _llamada(db_session, admin_user.id, dias_atras=400)

    assert retention_service.get_retention_days(db_session) == 0
    assert retention_service.purge_expired_audio(db_session) == 0
    assert almacen.borrados == []


def test_caduca_el_audio_pero_no_la_evaluacion(
    client, auth_headers, db_session, admin_user, monkeypatch
):
    almacen = _con_almacen(monkeypatch)
    vieja = _llamada(db_session, admin_user.id, dias_atras=120)
    reciente = _llamada(db_session, admin_user.id, dias_atras=5)

    client.put(
        "/api/v1/config/settings",
        json={"retention_audio_days": 90},
        headers=auth_headers,
    )
    borradas = retention_service.purge_expired_audio(db_session)

    assert borradas == 1
    assert almacen.borrados == [vieja.audio_url]
    db_session.refresh(vieja)
    db_session.refresh(reciente)
    assert vieja.audio_deleted_at is not None
    assert reciente.audio_deleted_at is None
    # Lo que da valor sigue ahí.
    assert vieja.transcription is not None and vieja.analysis is not None


def test_si_el_archivo_ya_no_estaba_la_llamada_se_marca_igual(
    client, auth_headers, db_session, admin_user, monkeypatch
):
    almacen = _con_almacen(monkeypatch)
    almacen.falla = True
    vieja = _llamada(db_session, admin_user.id, dias_atras=120)
    retention_service.set_retention_days(db_session, 30)

    assert retention_service.purge_expired_audio(db_session) == 1
    db_session.refresh(vieja)
    assert vieja.audio_deleted_at is not None


def test_el_endpoint_de_retencion_es_de_gestion(client, asesor_headers):
    r = client.post("/api/v1/config/retention/run", headers=asesor_headers)
    assert r.status_code == 403


def test_ejecutar_la_retencion_a_mano_informa_de_lo_borrado(
    client, auth_headers, db_session, admin_user, monkeypatch
):
    _con_almacen(monkeypatch)
    _llamada(db_session, admin_user.id, dias_atras=200)
    client.put(
        "/api/v1/config/settings",
        json={"retention_audio_days": 30},
        headers=auth_headers,
    )

    r = client.post("/api/v1/config/retention/run", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"retention_audio_days": 30, "audios_deleted": 1}

    # Y la política se ve en los ajustes.
    ajustes = client.get("/api/v1/config/settings", headers=auth_headers).json()
    assert ajustes["retention_audio_days"] == 30


def test_reproducir_un_audio_caducado_explica_que_paso(
    client, auth_headers, db_session, admin_user, monkeypatch
):
    _con_almacen(monkeypatch)
    vieja = _llamada(db_session, admin_user.id, dias_atras=200)
    retention_service.set_retention_days(db_session, 30)
    retention_service.purge_expired_audio(db_session)

    r = client.get(f"/api/v1/calls/{vieja.id}/audio", headers=auth_headers)
    assert r.status_code == 410
    assert "retención" in r.json()["detail"]

    # La ficha sigue abriéndose y dice desde cuándo no hay audio.
    detalle = client.get(f"/api/v1/calls/{vieja.id}", headers=auth_headers).json()
    assert detalle["audio_deleted_at"] is not None
    assert detalle["transcription"] is not None


# ===============================================================
# Supresión de los datos de una persona
# ===============================================================
def test_suprimir_los_datos_de_una_persona_se_lleva_todo(
    client, auth_headers, db_session, admin_user, sample_agent, monkeypatch
):
    almacen = _con_almacen(monkeypatch)
    _llamada(db_session, admin_user.id, dias_atras=10, agent_id=sample_agent.id)
    _llamada(db_session, admin_user.id, dias_atras=20, agent_id=sample_agent.id)
    ajena = _llamada(db_session, admin_user.id, dias_atras=10)

    r = client.delete(f"/api/v1/agents/{sample_agent.id}/data", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {
        "agent_id": sample_agent.id,
        "calls_deleted": 2,
        "audios_deleted": 2,
    }
    assert len(almacen.borrados) == 2

    # No queda nada suyo; lo de los demás no se toca.
    restantes = db_session.query(Call).all()
    assert [c.id for c in restantes] == [ajena.id]
    # La ficha se conserva desactivada, para no dejar huecos en los históricos.
    db_session.refresh(sample_agent)
    assert sample_agent.active is False


def test_suprimir_datos_es_solo_de_administradores(
    client, db_session, sample_agent, asesor_headers
):
    from app.models.user import ROLE_JEFE, User
    from app.utils.security import hash_password

    jefe = User(
        email="jefe.limitado@banco.com",
        password_hash=hash_password("una-contrasena-larga"),
        name="Jefe",
        role=ROLE_JEFE,
    )
    db_session.add(jefe)
    db_session.commit()
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "jefe.limitado@banco.com", "password": "una-contrasena-larga"},
    ).json()["access_token"]

    como_jefe = {"Authorization": f"Bearer {token}"}
    assert client.delete(
        f"/api/v1/agents/{sample_agent.id}/data", headers=como_jefe
    ).status_code == 403
    assert client.delete(
        f"/api/v1/agents/{sample_agent.id}/data", headers=asesor_headers
    ).status_code == 403


def test_no_se_borra_un_audio_que_otra_llamada_vigente_comparte(
    client, auth_headers, db_session, admin_user, monkeypatch
):
    """
    Varias llamadas pueden apuntar al mismo archivo (pasa con los datos de
    demostración). Borrarlo por la más vieja dejaría muda a la reciente.
    """
    almacen = _con_almacen(monkeypatch)
    compartido = "local://compartido.mp3"
    vieja = _llamada(db_session, admin_user.id, dias_atras=200)
    reciente = _llamada(db_session, admin_user.id, dias_atras=2)
    vieja.audio_url = compartido
    reciente.audio_url = compartido
    db_session.commit()

    retention_service.set_retention_days(db_session, 30)
    assert retention_service.purge_expired_audio(db_session) == 0
    assert almacen.borrados == []
    db_session.refresh(vieja)
    assert vieja.audio_deleted_at is None
