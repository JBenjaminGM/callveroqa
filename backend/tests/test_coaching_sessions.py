"""
Tests del coaching medible: sesiones ligadas a una dimensión con antes/después.

Lo que se protege:

- que la mejora que se atribuye al coaching descuente la del resto del equipo
  (si todos suben, no fue la sesión);
- que sin llamadas suficientes no se invente un veredicto;
- que el asesor solo vea su coaching y no pueda registrarlo él;
- que suprimir los datos de una persona se lleve también sus sesiones.
"""

from datetime import date, datetime, timedelta

from app.models.agent import Agent
from app.models.analysis import Analysis
from app.models.call import Call, CallStatus
from app.models.coaching_session import CoachingSession
from app.models.settings import RubricConfig
from app.services import coaching_session_service as css

HOY = date.today()


def _rubrica(db):
    db.add_all(
        [
            RubricConfig(dimension_key="objections", dimension_name="Manejo de objeciones", weight=50, display_order=1),
            RubricConfig(dimension_key="greeting", dimension_name="Saludo", weight=50, display_order=2),
        ]
    )
    db.commit()


def _llamada(db, uploaded_by, agent_id, dias_atras, **notas):
    """Llamada analizada hace `dias_atras` días con las notas por dimensión dadas."""
    dia = HOY - timedelta(days=dias_atras)
    call = Call(
        uploaded_by=uploaded_by,
        audio_url="x",
        status=CallStatus.DONE,
        agent_id=agent_id,
        call_date=dia,
        created_at=datetime.combine(dia, datetime.min.time()),
    )
    db.add(call)
    db.flush()
    db.add(Analysis(call_id=call.id, global_score=70, dimension_scores=notas))
    db.commit()
    return call


def _otro_asesor(db, nombre="Otra Persona"):
    agent = Agent(name=nombre)
    db.add(agent)
    db.commit()
    return agent


def _sesion(db, agent_id, dias_atras=20, key="objections"):
    s = CoachingSession(agent_id=agent_id, dimension_key=key, held_on=HOY - timedelta(days=dias_atras))
    db.add(s)
    db.commit()
    return s


def _medir(db, sesion):
    return css.measure_many(db, [sesion])[sesion.id]


# ===============================================================
# La medida
# ===============================================================
def test_mejora_frente_a_un_equipo_estable(db_session, admin_user, sample_agent):
    otro = _otro_asesor(db_session)
    for d in (35, 30, 25):
        _llamada(db_session, admin_user.id, sample_agent.id, d, objections=55)
        _llamada(db_session, admin_user.id, otro.id, d, objections=70)
    for d in (15, 10, 5):
        _llamada(db_session, admin_user.id, sample_agent.id, d, objections=80)
        _llamada(db_session, admin_user.id, otro.id, d, objections=70)

    m = _medir(db_session, _sesion(db_session, sample_agent.id, dias_atras=20))

    assert (m["before_avg"], m["after_avg"]) == (55, 80)
    assert m["team_delta"] == 0
    assert m["net_delta"] == 25
    assert m["verdict"] == "improved"
    assert [p["phase"] for p in m["points"]] == ["before"] * 3 + ["after"] * 3


def test_si_todo_el_equipo_sube_lo_mismo_no_es_merito_del_coaching(
    db_session, admin_user, sample_agent
):
    """El caso por el que existe la comparación con el equipo."""
    otro = _otro_asesor(db_session)
    for d in (35, 30, 25):
        _llamada(db_session, admin_user.id, sample_agent.id, d, objections=60)
        _llamada(db_session, admin_user.id, otro.id, d, objections=60)
    for d in (15, 10, 5):
        _llamada(db_session, admin_user.id, sample_agent.id, d, objections=75)
        _llamada(db_session, admin_user.id, otro.id, d, objections=73)

    m = _medir(db_session, _sesion(db_session, sample_agent.id, dias_atras=20))

    assert m["delta"] == 15
    assert m["team_delta"] == 13
    assert m["net_delta"] == 2
    assert m["verdict"] == "no_change"


def test_sin_equipo_comparable_se_juzga_el_cambio_bruto(db_session, admin_user, sample_agent):
    for d in (35, 30, 25):
        _llamada(db_session, admin_user.id, sample_agent.id, d, objections=80)
    for d in (15, 10, 5):
        _llamada(db_session, admin_user.id, sample_agent.id, d, objections=60)

    m = _medir(db_session, _sesion(db_session, sample_agent.id, dias_atras=20))

    assert m["team_delta"] is None
    assert m["net_delta"] == -20
    assert m["verdict"] == "worsened"


def test_con_equipo_pero_sin_datos_suyos_todavia_se_espera(
    db_session, admin_user, sample_agent
):
    """A los pocos días de la sesión el asesor puede tener llamadas y el equipo no."""
    otro = _otro_asesor(db_session)
    for d in (35, 30, 25):
        _llamada(db_session, admin_user.id, sample_agent.id, d, objections=50)
        _llamada(db_session, admin_user.id, otro.id, d, objections=50)
    for d in (4, 3, 2):
        _llamada(db_session, admin_user.id, sample_agent.id, d, objections=80)
    _llamada(db_session, admin_user.id, otro.id, 3, objections=80)

    m = _medir(db_session, _sesion(db_session, sample_agent.id, dias_atras=5))
    assert m["delta"] == 30
    assert m["team_delta"] is None
    assert m["verdict"] == "pending"


def test_sin_llamadas_suficientes_no_hay_veredicto(db_session, admin_user, sample_agent):
    for d in (35, 30, 25):
        _llamada(db_session, admin_user.id, sample_agent.id, d, objections=50)
    _llamada(db_session, admin_user.id, sample_agent.id, 5, objections=95)

    m = _medir(db_session, _sesion(db_session, sample_agent.id, dias_atras=20))
    # Una sola llamada buena después no es una mejora: es una llamada.
    assert m["verdict"] == "pending"
    assert m["after_count"] == 1

    sin_base = _medir(db_session, _sesion(db_session, sample_agent.id, dias_atras=40))
    assert sin_base["verdict"] == "no_baseline"


def test_el_dia_de_la_sesion_y_las_llamadas_sin_la_dimension_no_cuentan(
    db_session, admin_user, sample_agent
):
    _llamada(db_session, admin_user.id, sample_agent.id, 20, objections=10)
    _llamada(db_session, admin_user.id, sample_agent.id, 25, greeting=90)  # sin objections
    _llamada(db_session, admin_user.id, sample_agent.id, 60, objections=10)  # fuera de ventana

    m = _medir(db_session, _sesion(db_session, sample_agent.id, dias_atras=20))
    assert m["before_count"] == 0
    assert m["after_count"] == 0
    assert m["points"] == []


# ===============================================================
# API y permisos
# ===============================================================
def test_el_jefe_registra_una_sesion_y_la_ve_con_su_medida(
    client, db_session, admin_user, auth_headers, sample_agent
):
    _rubrica(db_session)
    call = _llamada(db_session, admin_user.id, sample_agent.id, 3, objections=40)

    r = client.post(
        "/api/v1/coaching/sessions",
        json={
            "agent_id": sample_agent.id,
            "dimension_key": "objections",
            "notes": "  Practicamos la respuesta a «me lo pienso».  ",
            "call_id": call.id,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["held_on"] == HOY.isoformat()
    assert body["dimension_name"] == "Manejo de objeciones"
    assert body["notes"] == "Practicamos la respuesta a «me lo pienso»."
    assert body["coach_name"] == "Admin Test"
    assert body["measure"]["verdict"] == "no_baseline"

    listado = client.get(
        f"/api/v1/coaching/sessions?agent_id={sample_agent.id}", headers=auth_headers
    ).json()
    assert [s["id"] for s in listado] == [body["id"]]


def test_validaciones_al_registrar(client, db_session, admin_user, auth_headers, sample_agent):
    _rubrica(db_session)
    otro = _otro_asesor(db_session)
    ajena = _llamada(db_session, admin_user.id, otro.id, 3, objections=40)
    base = {"agent_id": sample_agent.id, "dimension_key": "objections"}

    def post(**extra):
        return client.post(
            "/api/v1/coaching/sessions", json={**base, **extra}, headers=auth_headers
        )

    assert post(dimension_key="no_existe").status_code == 422
    assert post(held_on=(HOY + timedelta(days=1)).isoformat()).status_code == 422
    assert post(call_id=ajena.id).status_code == 422
    assert post(agent_id=9999).status_code == 404


def test_el_asesor_solo_ve_su_coaching_y_no_puede_registrarlo(
    client, db_session, admin_user, asesor_headers, sample_agent
):
    _rubrica(db_session)
    otro = _otro_asesor(db_session)
    mia = _sesion(db_session, sample_agent.id)
    ajena = _sesion(db_session, otro.id)

    # Aunque pida las de otro, recibe solo las suyas.
    r = client.get(f"/api/v1/coaching/sessions?agent_id={otro.id}", headers=asesor_headers)
    assert [s["id"] for s in r.json()] == [mia.id]

    assert client.get(f"/api/v1/coaching/sessions/{mia.id}", headers=asesor_headers).status_code == 200
    assert client.get(f"/api/v1/coaching/sessions/{ajena.id}", headers=asesor_headers).status_code == 403

    r = client.post(
        "/api/v1/coaching/sessions",
        json={"agent_id": sample_agent.id, "dimension_key": "objections"},
        headers=asesor_headers,
    )
    assert r.status_code == 403
    assert client.delete(f"/api/v1/coaching/sessions/{mia.id}", headers=asesor_headers).status_code == 403


def test_corregir_y_borrar_una_sesion(client, db_session, auth_headers, sample_agent):
    _rubrica(db_session)
    s = _sesion(db_session, sample_agent.id)

    r = client.patch(
        f"/api/v1/coaching/sessions/{s.id}",
        json={"dimension_key": "greeting", "notes": "Era el saludo"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["dimension_name"] == "Saludo"

    assert client.delete(f"/api/v1/coaching/sessions/{s.id}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/v1/coaching/sessions/{s.id}", headers=auth_headers).status_code == 404


def test_suprimir_los_datos_de_una_persona_borra_su_coaching(
    client, db_session, auth_headers, sample_agent
):
    _sesion(db_session, sample_agent.id)
    r = client.delete(f"/api/v1/agents/{sample_agent.id}/data", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["coaching_sessions_deleted"] == 1
    db_session.expire_all()
    assert db_session.query(CoachingSession).count() == 0


def test_sugiere_la_dimension_mas_alejada_del_equipo(
    client, db_session, admin_user, auth_headers, sample_agent
):
    """No la nota más baja: la que más se separa de lo que hace el resto."""
    _rubrica(db_session)
    otro = _otro_asesor(db_session)
    for d in (3, 6, 9):
        # Saludo: 50, pero el equipo también saca 50 → problema de todos.
        # Objeciones: 65, y el equipo saca 90 → problema de esta persona.
        _llamada(db_session, admin_user.id, sample_agent.id, d, greeting=50, objections=65)
        _llamada(db_session, admin_user.id, otro.id, d, greeting=50, objections=90)

    r = client.get(f"/api/v1/coaching/suggestions/{sample_agent.id}", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body[0]["dimension_key"] == "objections"
    assert body[0]["gap"] == -25
