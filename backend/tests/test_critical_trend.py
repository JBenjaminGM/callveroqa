"""
Tests de las suspendidas por asesor y su tendencia.

Lo que se protege:

- que una suspensión suelta no dispare una alerta de patrón, y dos sí;
- que la subida se mida entre mitades del periodo y no se invente con pocas llamadas;
- que el endpoint agregue por semana, asesor y criterio, y sea solo de managers.
"""

from datetime import date, datetime, timedelta

from app.models.agent import Agent
from app.models.analysis import Analysis
from app.models.call import Call, CallStatus
from app.services import critical_service as cs

FIN = datetime.now()
INICIO = FIN - timedelta(days=30)
FALLO = [{"dimension": "compliance", "criterion": "Disclaimers obligatorios", "segment": 1, "reason": "x"}]


def _fila(dias_atras, agent_id=1, suspendida=False):
    momento = FIN - timedelta(days=dias_atras)
    call = Call(id=None, agent_id=agent_id, created_at=momento, call_date=momento.date())
    analysis = Analysis(
        global_score=0 if suspendida else 80,
        uncapped_score=70 if suspendida else None,
        dimension_scores={},
        critical_failures=FALLO if suspendida else None,
    )
    return call, analysis


def _informe(rows):
    return cs.critical_report(rows, INICIO, FIN, {1: "Ana", 2: "Beto"})


def test_una_suspension_suelta_no_es_un_patron_y_dos_si():
    una = _informe([_fila(5, suspendida=True), _fila(6), _fila(7)])
    assert not [a for a in cs.critical_alerts(una) if a["type"] == "critical_agent"]

    dos = _informe([_fila(5, suspendida=True), _fila(6, suspendida=True), _fila(7), _fila(8)])
    alertas = [a for a in cs.critical_alerts(dos) if a["type"] == "critical_agent"]
    assert len(alertas) == 1
    assert alertas[0]["agent_name"] == "Ana"
    assert alertas[0]["severity"] == "high"  # 2 de 4 = 50 %
    assert "Disclaimers obligatorios" in alertas[0]["description"]


def test_detecta_la_subida_entre_mitades():
    filas = [_fila(d) for d in (25, 24, 23, 22)] + [
        _fila(d, suspendida=True) for d in (5, 4)
    ] + [_fila(3), _fila(2)]
    informe = _informe(filas)
    assert informe["first_half_pct"] == 0
    assert informe["second_half_pct"] == 50
    tendencias = [a for a in cs.critical_alerts(informe) if a["type"] == "critical_trend"]
    # Una del equipo y otra de Ana (que es todo el equipo aquí).
    assert {a.get("agent_id") for a in tendencias} == {None, 1}


def test_con_pocas_llamadas_no_se_mide_la_subida():
    informe = _informe([_fila(25), _fila(3, suspendida=True), _fila(2, suspendida=True)])
    assert informe["first_half_pct"] is None
    assert not [a for a in cs.critical_alerts(informe) if a["type"] == "critical_trend"]


def test_agrega_por_semana_asesor_y_criterio():
    filas = [
        _fila(2, agent_id=1, suspendida=True),
        _fila(3, agent_id=2),
        _fila(10, agent_id=2, suspendida=True),
        _fila(11, agent_id=2, suspendida=True),
    ]
    informe = _informe(filas)
    assert informe["critical_calls"] == 3
    assert informe["critical_pct"] == 75
    assert sum(w["total_calls"] for w in informe["weekly"]) == 4
    # Primero quien más suspende.
    assert [a["agent_name"] for a in informe["by_agent"]] == ["Beto", "Ana"]
    assert informe["top_criteria"] == [{"criterion": "Disclaimers obligatorios", "count": 3}]


def test_endpoint_y_alertas_del_panel(client, db_session, admin_user, auth_headers, asesor_headers):
    agente = Agent(name="Ana")
    db_session.add(agente)
    db_session.flush()
    for dias, susp in ((2, True), (4, True), (6, False)):
        momento = datetime.now() - timedelta(days=dias)
        call = Call(
            uploaded_by=admin_user.id,
            audio_url="x",
            status=CallStatus.DONE,
            agent_id=agente.id,
            created_at=momento,
            call_date=date.today() - timedelta(days=dias),
        )
        db_session.add(call)
        db_session.flush()
        db_session.add(
            Analysis(
                call_id=call.id,
                global_score=0 if susp else 85,
                uncapped_score=75 if susp else None,
                dimension_scores={"compliance": 40 if susp else 90},
                critical_failures=FALLO if susp else None,
                recommendations=[],
            )
        )
    db_session.commit()

    r = client.get("/api/v1/dashboard/critical?period=30d", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["critical_calls"] == 2
    assert body["by_agent"][0]["agent_name"] == "Ana"

    alertas = client.get("/api/v1/dashboard/alerts?period=30d", headers=auth_headers).json()
    assert any(a["type"] == "critical_agent" for a in alertas)

    assert client.get("/api/v1/dashboard/critical", headers=asesor_headers).status_code == 403
