"""
Tests del motivo de llamada (por qué llama el cliente).

Lo que se protege, por orden de importancia:

- que el vocabulario **no se fragmente**: "Cobro duplicado" y "cobro duplicado"
  tienen que ser la misma barra del panel, o la agregación no sirve para nada;
- que la IA reciba los motivos ya usados para reutilizarlos;
- que la basura que a veces devuelve un LLM ("Motivo: ...", comillas, una frase
  entera) se limpie en vez de guardarse tal cual.
"""

from datetime import date, datetime, timedelta

from app.models.analysis import Analysis
from app.models.call import Call, CallStatus
from app.prompts.analysis_es import build_analysis_prompt
from app.services import topic_service

RUBRICA = [{"dimension_key": "greeting", "dimension_name": "Saludo", "criteria": []}]


def _llamada(db, uploaded_by, *, topic, score=80, dias_atras=1, criticos=None):
    momento = datetime.now() - timedelta(days=dias_atras)
    call = Call(
        uploaded_by=uploaded_by,
        audio_url=f"x-{topic}-{score}-{dias_atras}",
        status=CallStatus.DONE,
        call_date=date.today() - timedelta(days=dias_atras),
        created_at=momento,
        duration_seconds=60,
        topic=topic,
    )
    db.add(call)
    db.flush()
    db.add(
        Analysis(
            call_id=call.id,
            global_score=score,
            dimension_scores={"greeting": score},
            recommendations=[],
            critical_failures=criticos,
            uncapped_score=90 if criticos else None,
        )
    )
    db.commit()
    return call


# ===============================================================
# Limpieza y unificación
# ===============================================================
def test_se_limpia_lo_que_devuelve_el_llm():
    assert topic_service.clean_topic("  Cobro   duplicado  ") == "Cobro duplicado"
    assert topic_service.clean_topic("Motivo: cobro duplicado") == "Cobro duplicado"
    assert topic_service.clean_topic('"Reclamo por comisión"') == "Reclamo por comisión"
    # Una frase entera se recorta a etiqueta, sin cortar una palabra por la mitad.
    largo = topic_service.clean_topic(
        "El cliente llama porque no entiende el cobro de la comisión de mantenimiento"
    )
    assert len(largo) <= topic_service.MAX_TOPIC_CHARS
    assert not largo.endswith(" ") and " " in largo
    # Lo que no vale, fuera.
    assert topic_service.clean_topic(None) is None
    assert topic_service.clean_topic("") is None
    assert topic_service.clean_topic("ok") is None


def test_no_se_duplica_un_motivo_que_ya_existe(db_session, admin_user):
    _llamada(db_session, admin_user.id, topic="Cobro duplicado")

    # Mismas palabras con otras mayúsculas o acentos: es el mismo motivo.
    assert topic_service.resolve_topic(db_session, "cobro duplicado") == "Cobro duplicado"
    assert topic_service.resolve_topic(db_session, "COBRO DUPLICADO") == "Cobro duplicado"
    assert topic_service.resolve_topic(db_session, "  Cobro  Duplicado ") == "Cobro duplicado"
    # Uno nuevo sí entra como nuevo.
    assert topic_service.resolve_topic(db_session, "Baja de producto") == "Baja de producto"


def test_el_catalogo_va_de_mas_a_menos_frecuente(db_session, admin_user):
    for _ in range(3):
        _llamada(db_session, admin_user.id, topic="Consulta de saldo")
    _llamada(db_session, admin_user.id, topic="Reclamo por cobro")

    assert topic_service.catalog(db_session) == ["Consulta de saldo", "Reclamo por cobro"]


def test_el_prompt_ensena_los_motivos_ya_usados():
    con_catalogo = build_analysis_prompt(
        [{"text": "hola"}], RUBRICA, topic_catalog=["Consulta de saldo"]
    )
    assert "MOTIVOS YA USADOS" in con_catalogo
    assert "- Consulta de saldo" in con_catalogo
    assert '"topic"' in con_catalogo

    sin_catalogo = build_analysis_prompt([{"text": "hola"}], RUBRICA)
    assert "MOTIVOS YA USADOS" not in sin_catalogo
    # Aun sin catálogo se pide el motivo: así se construye el catálogo inicial.
    assert '"topic"' in sin_catalogo


# ===============================================================
# Panel
# ===============================================================
def test_el_panel_agrupa_por_motivo(client, auth_headers, db_session, admin_user):
    _llamada(db_session, admin_user.id, topic="Reclamo por cobro", score=40)
    _llamada(db_session, admin_user.id, topic="Reclamo por cobro", score=50)
    _llamada(
        db_session, admin_user.id, topic="Reclamo por cobro", score=0,
        criticos=[{"dimension": "compliance", "criterion": "Disclaimers obligatorios"}],
    )
    _llamada(db_session, admin_user.id, topic="Consulta de saldo", score=95)
    # Una llamada sin motivo (analizada antes de que existiera) no rompe nada.
    _llamada(db_session, admin_user.id, topic=None, score=70)

    filas = client.get("/api/v1/dashboard/topics", headers=auth_headers).json()

    assert [f["topic"] for f in filas] == ["Reclamo por cobro", "Consulta de saldo"]
    reclamos = filas[0]
    assert reclamos["total_calls"] == 3
    assert reclamos["avg_score"] == 30.0
    assert reclamos["red_calls"] == 3 and reclamos["red_pct"] == 100.0
    assert reclamos["critical_calls"] == 1
    assert filas[1]["red_calls"] == 0


def test_los_motivos_son_de_gestion(client, asesor_headers):
    assert client.get("/api/v1/dashboard/topics", headers=asesor_headers).status_code == 403


def test_el_pipeline_guarda_el_motivo_unificado(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.tasks.call_tasks as ct
    from app.models import Base, RubricConfig, User

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
            return {"text": "hola", "segments": [{"start": 0.0, "end": 1.0, "text": "hola"}]}

    class _An:
        async def analyze(self, prompt):
            return {
                "dimension_scores": {"greeting": 80},
                # Con la forma sucia con la que a veces contesta un LLM.
                "topic": "  motivo: CONSULTA de saldo ",
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
            dimension_key="greeting", dimension_name="Saludo", weight=100.0, display_order=1
        )
    )
    # Ya existe el motivo con otra grafía: debe reutilizarse ese.
    previa = Call(
        uploaded_by=1, audio_url="v", status=CallStatus.DONE, topic="Consulta de saldo"
    )
    s.add(previa)
    call = Call(uploaded_by=1, audio_url="f", audio_filename="a.mp3", language="es",
                status=CallStatus.QUEUED)
    s.add(call)
    s.commit()
    call_id = call.id
    s.close()

    ct.process_call(call_id)

    chk = TS()
    procesada = chk.get(Call, call_id)
    topic = procesada.topic
    chk.close()
    assert topic == "Consulta de saldo"
