"""
Tests de la evidencia por dimensión, los criterios críticos (auto-fail) y la
búsqueda en transcripciones.

Lo que se protege, por orden de importancia:

- que la IA **no pueda suspender** una llamada por un criterio que la rúbrica
  no marcó como crítico;
- que un crítico incumplido deje la nota en 0 **sin perder** la que habría
  tenido;
- que la evidencia solo apunte a segmentos que existen;
- que la búsqueda respete el alcance del asesor y trate los comodines como texto.
"""

from datetime import date, datetime, timedelta

from app.models.analysis import Analysis
from app.models.call import Call, CallStatus
from app.models.settings import RubricConfig
from app.models.transcription import Transcription
from app.prompts.analysis_es import build_analysis_prompt
from app.services.call_service import match_snippet
from app.services.evidence_service import (
    apply_auto_fail,
    normalize_critical_failures,
    normalize_evidence,
)

RUBRICA = [
    {
        "dimension_key": "compliance",
        "dimension_name": "Cumplimiento",
        "criteria": [
            {"name": "Informar la TEA", "enabled": True, "critical": True},
            {"name": "Aviso de grabación", "enabled": True, "critical": False},
            {"name": "Garantizar aprobación", "enabled": False, "critical": True},
        ],
    },
    {"dimension_key": "greeting", "dimension_name": "Saludo", "criteria": []},
]


# ===============================================================
# Evidencia (funciones puras)
# ===============================================================
def test_evidencia_descarta_claves_y_segmentos_que_no_existen():
    raw = {
        "compliance": {"justification": "No dijo la TEA.", "segments": [2, 99, -1, "1"]},
        "inventada": {"justification": "x", "segments": [0]},
    }
    ev = normalize_evidence(raw, ["compliance", "greeting"], n_segments=5)
    assert set(ev) == {"compliance"}
    assert ev["compliance"]["segments"] == [1, 2]
    assert ev["compliance"]["justification"] == "No dijo la TEA."


def test_evidencia_como_mucho_tres_segmentos_sin_duplicados():
    raw = {"greeting": {"justification": "ok", "segments": [4, 0, 0, 3, 1, 2]}}
    ev = normalize_evidence(raw, ["greeting"], n_segments=10)
    assert ev["greeting"]["segments"] == [0, 1, 2]


def test_evidencia_recorta_justificaciones_largas_y_tolera_basura():
    raw = {"greeting": {"justification": "a" * 1000, "segments": "no-es-lista"}}
    ev = normalize_evidence(raw, ["greeting"], n_segments=3)
    assert len(ev["greeting"]["justification"]) == 400
    assert ev["greeting"]["segments"] == []
    assert normalize_evidence("basura", ["greeting"], 3) == {}
    assert normalize_evidence({"greeting": {}}, ["greeting"], 3) == {}


# ===============================================================
# Criterios críticos (funciones puras)
# ===============================================================
def test_critico_solo_cuenta_si_la_rubrica_lo_define_y_esta_activo():
    raw = [
        {"dimension": "compliance", "criterion": "informar la tea", "segment": 3, "reason": "Omitió la TEA"},
        # No es crítico en la rúbrica: la IA no puede suspender por esto.
        {"dimension": "compliance", "criterion": "Aviso de grabación", "segment": 0},
        # Crítico pero desactivado.
        {"dimension": "compliance", "criterion": "Garantizar aprobación", "segment": 1},
        # Inventado.
        {"dimension": "greeting", "criterion": "Sonreír", "segment": 0},
    ]
    fallos = normalize_critical_failures(raw, RUBRICA, n_segments=5)
    assert fallos == [
        {
            "dimension": "compliance",
            "criterion": "Informar la TEA",  # nombre tal cual lo escribió el jefe
            "segment": 3,
            "reason": "Omitió la TEA",
        }
    ]


def test_critico_sin_duplicados_y_segmento_invalido_a_none():
    raw = [
        {"dimension": "compliance", "criterion": "Informar la TEA", "segment": 50},
        {"dimension": "compliance", "criterion": "Informar la TEA", "segment": 1},
    ]
    fallos = normalize_critical_failures(raw, RUBRICA, n_segments=5)
    assert len(fallos) == 1
    assert fallos[0]["segment"] is None


def test_sin_criticos_definidos_no_hay_fallos():
    rubrica = [{"dimension_key": "greeting", "criteria": [{"name": "Hola", "enabled": True}]}]
    raw = [{"dimension": "greeting", "criterion": "Hola"}]
    assert normalize_critical_failures(raw, rubrica, 3) == []


def test_auto_fail_deja_cero_y_conserva_la_nota():
    assert apply_auto_fail(82, [{"criterion": "x"}]) == (0, 82)
    assert apply_auto_fail(82, []) == (82, None)


# ===============================================================
# Prompt
# ===============================================================
def test_prompt_lista_solo_los_criticos_activos_y_pide_evidencia():
    prompt = build_analysis_prompt([{"text": "hola"}], RUBRICA)
    assert "CRITERIOS CRÍTICOS" in prompt
    assert "- Informar la TEA (dimensión: compliance)" in prompt
    assert "Garantizar aprobación (dimensión" not in prompt  # desactivado
    assert "dimension_evidence" in prompt
    assert "critical_failures" in prompt


def test_prompt_sin_criticos_no_incluye_el_bloque():
    prompt = build_analysis_prompt([{"text": "hola"}], [RUBRICA[1]])
    assert "CRITERIOS CRÍTICOS" not in prompt


# ===============================================================
# Pipeline completo
# ===============================================================
def test_pipeline_guarda_evidencia_y_aplica_auto_fail(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.tasks.call_tasks as ct
    from app.models import Base, User

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TS = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    class _Storage:
        def load(self, url):
            return b"x"

    class _Trans:
        async def transcribe(self, path, language):
            return {
                "text": "Le atiende Ana. Le ofrezco la tarjeta. Gracias.",
                "segments": [
                    {"start": 0.0, "end": 1.0, "text": "Le atiende Ana."},
                    {"start": 1.0, "end": 4.0, "text": "Le ofrezco la tarjeta."},
                    {"start": 4.0, "end": 5.0, "text": "Gracias."},
                ],
            }

    class _An:
        async def analyze(self, prompt):
            return {
                "dimension_scores": {"compliance": 70, "greeting": 90},
                "dimension_evidence": {
                    "compliance": {"justification": "Ofreció sin decir la TEA.", "segments": [1, 7]},
                    "greeting": {"justification": "Se presentó.", "segments": [0]},
                },
                "critical_failures": [
                    {"dimension": "compliance", "criterion": "Informar la TEA", "segment": 1, "reason": "No la mencionó"},
                    {"dimension": "greeting", "criterion": "Inventado", "segment": 0},
                ],
                "summary": "ok",
                "recommendations": [],
                "ai_model": "x",
                "tokens_used": 1,
            }

    monkeypatch.setattr(ct, "SessionLocal", TS)
    monkeypatch.setattr(ct, "get_storage_provider", lambda: _Storage())
    monkeypatch.setattr(ct, "get_transcription_provider", lambda: _Trans())
    monkeypatch.setattr(ct, "get_analysis_provider", lambda: _An())

    s = TS()
    s.add(User(email="u@u.com", password_hash="x", name="U", role="jefe"))
    s.flush()
    s.add(
        RubricConfig(
            dimension_key="compliance",
            dimension_name="Cumplimiento",
            weight=50.0,
            display_order=1,
            criteria=[{"name": "Informar la TEA", "enabled": True, "critical": True}],
        )
    )
    s.add(RubricConfig(dimension_key="greeting", dimension_name="Saludo", weight=50.0, display_order=2))
    call = Call(uploaded_by=1, audio_url="f", audio_filename="a.mp3", language="es", status=CallStatus.QUEUED)
    s.add(call)
    s.commit()
    call_id = call.id
    s.close()

    ct.process_call(call_id)

    chk = TS()
    analysis = chk.query(Analysis).filter_by(call_id=call_id).one()
    chk.close()

    assert analysis.global_score == 0
    assert analysis.uncapped_score == 80  # (70 + 90) / 2
    assert analysis.dimension_evidence["compliance"]["segments"] == [1]  # el 7 no existe
    assert [f["criterion"] for f in analysis.critical_failures] == ["Informar la TEA"]


# ===============================================================
# API: detalle, búsqueda y filtro de críticos
# ===============================================================
def _llamada(db, uploaded_by, texto, *, score=80, uncapped=None, agent_id=None, evidencia=None):
    call = Call(
        uploaded_by=uploaded_by,
        audio_url="x",
        status=CallStatus.DONE,
        call_date=date.today(),
        created_at=datetime.now() - timedelta(hours=1),
        agent_id=agent_id,
        duration_seconds=60,
    )
    db.add(call)
    db.flush()
    db.add(
        Transcription(
            call_id=call.id,
            full_text=texto,
            segments=[{"start": 0.0, "end": 2.0, "speaker": "agent", "text": texto}],
        )
    )
    db.add(
        Analysis(
            call_id=call.id,
            global_score=0 if uncapped is not None else score,
            uncapped_score=uncapped,
            critical_failures=(
                [{"dimension": "compliance", "criterion": "Informar la TEA", "segment": 0, "reason": "x"}]
                if uncapped is not None
                else None
            ),
            dimension_scores={"compliance": score},
            dimension_evidence=evidencia,
            recommendations=[],
        )
    )
    db.commit()
    return call


def test_detalle_devuelve_evidencia_y_fallos_criticos(client, auth_headers, db_session, admin_user):
    call = _llamada(
        db_session,
        admin_user.id,
        "hola",
        uncapped=75,
        evidencia={"compliance": {"justification": "No dijo la TEA.", "segments": [0]}},
    )
    data = client.get(f"/api/v1/calls/{call.id}", headers=auth_headers).json()["analysis"]
    assert data["global_score"] == 0
    assert data["uncapped_score"] == 75
    assert data["critical_failures"][0]["criterion"] == "Informar la TEA"
    assert data["dimension_evidence"]["compliance"]["segments"] == [0]


def test_detalle_de_analisis_antiguo_sin_evidencia(client, auth_headers, db_session, admin_user):
    call = _llamada(db_session, admin_user.id, "hola")
    data = client.get(f"/api/v1/calls/{call.id}", headers=auth_headers).json()["analysis"]
    assert data["dimension_evidence"] is None
    assert data["critical_failures"] is None
    assert data["uncapped_score"] is None


def test_busqueda_en_transcripcion_con_fragmento(client, auth_headers, db_session, admin_user):
    _llamada(db_session, admin_user.id, "Buenas tardes, quiero CANCELAR mi tarjeta hoy mismo.")
    _llamada(db_session, admin_user.id, "Buenas tardes, quiero un préstamo.")
    data = client.get("/api/v1/calls", params={"q": "cancelar"}, headers=auth_headers).json()
    assert data["total"] == 1
    assert "CANCELAR" in data["items"][0]["match_snippet"]


def test_busqueda_trata_los_comodines_como_texto(client, auth_headers, db_session, admin_user):
    _llamada(db_session, admin_user.id, "La tasa es del 100% anual.")
    _llamada(db_session, admin_user.id, "La tasa es del 1000 anual.")
    data = client.get("/api/v1/calls", params={"q": "100%"}, headers=auth_headers).json()
    assert data["total"] == 1
    data = client.get("/api/v1/calls", params={"q": "_"}, headers=auth_headers).json()
    assert data["total"] == 0


def test_busqueda_respeta_el_alcance_del_asesor(
    client, asesor_headers, db_session, admin_user, sample_agent
):
    _llamada(db_session, admin_user.id, "quiero cancelar", agent_id=sample_agent.id)
    _llamada(db_session, admin_user.id, "quiero cancelar")  # de otro / sin asignar
    data = client.get("/api/v1/calls", params={"q": "cancelar"}, headers=asesor_headers).json()
    assert data["total"] == 1


def test_filtro_de_llamadas_suspendidas_por_critico(client, auth_headers, db_session, admin_user):
    _llamada(db_session, admin_user.id, "a", uncapped=90)
    _llamada(db_session, admin_user.id, "b")
    todas = client.get("/api/v1/calls", headers=auth_headers).json()
    assert todas["total"] == 2
    assert sorted(i["critical_failed"] for i in todas["items"]) == [False, True]
    criticas = client.get("/api/v1/calls", params={"critical": "true"}, headers=auth_headers).json()
    assert criticas["total"] == 1
    assert criticas["items"][0]["critical_failed"] is True


# ===============================================================
# Rúbrica: el flag crítico se guarda
# ===============================================================
def test_rubrica_guarda_el_flag_critico(client, auth_headers, db_session):
    db_session.add(RubricConfig(dimension_key="compliance", dimension_name="Cumplimiento", weight=100.0, display_order=1))
    db_session.commit()
    payload = {
        "dimensions": [
            {
                "dimension_key": "compliance",
                "dimension_name": "Cumplimiento",
                "weight": 100,
                "criteria": [
                    {"name": "Informar la TEA", "enabled": True, "critical": True},
                    {"name": "Aviso de grabación", "enabled": True},
                ],
            }
        ]
    }
    r = client.put("/api/v1/config/rubric", json=payload, headers=auth_headers)
    assert r.status_code == 200, r.text
    rubrica = client.get("/api/v1/config/rubric", headers=auth_headers).json()
    criterios = {c["name"]: c["critical"] for c in rubrica[0]["criteria"]}
    assert criterios == {"Informar la TEA": True, "Aviso de grabación": False}


# ===============================================================
# El auto-fail no contamina la calibración ni el coaching
# ===============================================================
def test_calibracion_compara_contra_la_nota_sin_auto_fail(
    client, auth_headers, db_session, admin_user
):
    """
    Una llamada suspendida tiene nota 0 por regla, no porque la IA puntuara
    0 la rúbrica. Si el jefe pone 72, el desacuerdo real es con el 75 de la
    rúbrica, no con el 0: una «diferencia» de 72 sería la regla, no calibración.
    """
    db_session.add(RubricConfig(dimension_key="compliance", dimension_name="Cumplimiento", weight=100.0, display_order=1))
    db_session.commit()
    call = _llamada(db_session, admin_user.id, "hola", score=75, uncapped=75)

    body = client.put(
        f"/api/v1/calls/{call.id}/review",
        json={"dimension_scores": {"compliance": 72}},
        headers=auth_headers,
    ).json()
    assert body["ai_global_score"] == 75
    assert body["global_delta"] == -3

    acuerdo = client.get("/api/v1/calibration/agreement", headers=auth_headers).json()
    assert acuerdo["ai_avg"] == 75
    assert acuerdo["mean_abs_diff"] == 3


def test_la_suspendida_sin_escuchar_va_antes_que_la_banda_roja(
    client, auth_headers, db_session, admin_user
):
    roja = _llamada(db_session, admin_user.id, "a", score=40)
    suspendida = _llamada(db_session, admin_user.id, "b", uncapped=85)
    lista = client.get("/api/v1/coaching/who-to-listen", headers=auth_headers).json()
    motivos = [(s["call_id"], s["reason"]) for s in lista]
    assert motivos[0] == (suspendida.id, "critical_failed")
    assert (roja.id, "red_unreviewed") in motivos
    assert "Informar la TEA" in lista[0]["description"]


def test_fragmento_de_busqueda():
    texto = "x" * 100 + " cancelar " + "y" * 100
    frag = match_snippet(texto, "CANCELAR")
    assert frag.startswith("…") and frag.endswith("…") and "cancelar" in frag
    assert match_snippet("hola", "adiós") is None
    assert match_snippet(None, "x") is None
