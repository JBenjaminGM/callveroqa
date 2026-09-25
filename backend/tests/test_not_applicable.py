"""
Tests de los criterios «no aplica».

Lo que se protege:

- que una dimensión que no aplica no baje la nota: su peso se reparte;
- que sin ninguna «no aplica» la nota salga exactamente igual que antes;
- que solo pueda no aplicar lo que la rúbrica permite (la IA no se libra de una
  dimensión por dejarla en blanco);
- que no se pueda suspender por un crítico en una dimensión que no aplicaba;
- que la rúbrica guarde y devuelva la opción y su condición.
"""

from app.models import Analysis, Base, Call, CallStatus, RubricConfig, User
from app.prompts import get_analysis_prompt
from app.services.analysis_service import calculate_global_score
from app.services.evidence_service import normalize_scores

RUBRICA = [
    {"dimension_key": "greeting", "dimension_name": "Saludo", "criteria": []},
    {
        "dimension_key": "objections",
        "dimension_name": "Objeciones",
        "criteria": [],
        "allow_na": True,
        "na_condition": "Solo si el cliente plantea una objeción.",
    },
]


# ===============================================================
# Nota global
# ===============================================================
def test_lo_que_no_aplica_reparte_su_peso():
    pesos = {"greeting": 50.0, "objections": 50.0}
    # Antes: el hueco de objeciones contaba como cero y la nota era 40.
    assert calculate_global_score({"greeting": 80}, pesos) == 40
    assert calculate_global_score({"greeting": 80}, pesos, ["objections"]) == 80


def test_sin_no_aplica_la_nota_es_la_de_siempre():
    pesos = {"a": 14.28, "b": 14.28, "c": 71.44}
    notas = {"a": 90, "b": 40, "c": 75}
    esperado = round(sum(notas[k] * pesos[k] / 100 for k in notas))
    assert calculate_global_score(notas, pesos, []) == esperado


def test_si_nada_aplica_la_nota_es_cero_y_no_revienta():
    assert calculate_global_score({}, {"a": 100.0}, ["a"]) == 0


# ===============================================================
# Saneado de lo que devuelve la IA
# ===============================================================
def test_solo_puede_no_aplicar_lo_que_la_rubrica_permite():
    notas, na = normalize_scores({"greeting": None, "objections": None}, RUBRICA)
    assert na == ["objections"]
    # El saludo no puede no aplicar: queda sin nota y cuenta como cero.
    assert notas == {}


def test_acepta_las_formas_habituales_de_decir_no_aplica():
    for valor in (None, "N/A", "no aplica", "null", ""):
        _, na = normalize_scores({"objections": valor}, RUBRICA)
        assert na == ["objections"], valor


def test_acota_y_convierte_las_notas():
    notas, na = normalize_scores({"greeting": "87.6", "objections": 140}, RUBRICA)
    assert notas == {"greeting": 88, "objections": 100}
    assert na == []


def test_el_prompt_solo_ofrece_null_donde_se_permite():
    prompt = get_analysis_prompt([{"text": "hola"}], RUBRICA, "es")
    assert '"objections": <int 0-100 o null si no aplica>' in prompt
    assert '"greeting": <int 0-100>' in prompt
    assert "Solo si el cliente plantea una objeción." in prompt


# ===============================================================
# Pipeline completo, con la IA simulada
# ===============================================================
def test_el_pipeline_guarda_lo_que_no_aplico_y_descarta_su_critico(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.tasks.call_tasks as ct

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
            return {"text": "Hola.", "segments": [{"start": 0.0, "end": 1.0, "text": "Hola."}]}

    class _An:
        async def analyze(self, prompt):
            return {
                "dimension_scores": {"greeting": 80, "objections": None},
                "dimension_evidence": {
                    "objections": {"justification": "El cliente no puso ninguna objeción.", "segments": []}
                },
                # Contradicción: un crítico en una dimensión que dice que no aplica.
                "critical_failures": [
                    {"dimension": "objections", "criterion": "Rebatir con datos", "segment": 0, "reason": "x"}
                ],
                "summary": "ok",
                "recommendations": [],
            }

    monkeypatch.setattr(ct, "SessionLocal", TS)
    monkeypatch.setattr(ct, "get_storage_provider", lambda: _Storage())
    monkeypatch.setattr(ct, "get_transcription_provider", lambda: _Trans())
    monkeypatch.setattr(ct, "get_analysis_provider", lambda: _An())

    s = TS()
    s.add(User(email="u@u.com", password_hash="x", name="U", role="jefe"))
    s.flush()
    s.add_all(
        [
            RubricConfig(dimension_key="greeting", dimension_name="Saludo", weight=50.0, display_order=1),
            RubricConfig(
                dimension_key="objections",
                dimension_name="Objeciones",
                weight=50.0,
                display_order=2,
                allow_na=True,
                criteria=[{"name": "Rebatir con datos", "enabled": True, "critical": True}],
            ),
        ]
    )
    call = Call(uploaded_by=1, audio_url="f", audio_filename="a.mp3", language="es", status=CallStatus.QUEUED)
    s.add(call)
    s.commit()
    call_id = call.id
    s.close()

    ct.process_call(call_id)

    chk = TS()
    analysis = chk.query(Analysis).filter_by(call_id=call_id).one()
    assert chk.get(Call, call_id).status == CallStatus.DONE
    assert analysis.dimension_scores == {"greeting": 80}
    assert analysis.not_applicable == ["objections"]
    # Ni suspendida ni penalizada: la nota es la del saludo.
    assert analysis.global_score == 80
    assert analysis.critical_failures is None
    # La explicación de por qué no aplica se conserva.
    assert "objeción" in analysis.dimension_evidence["objections"]["justification"]
    chk.close()


# ===============================================================
# Rúbrica
# ===============================================================
def test_la_rubrica_guarda_la_opcion_y_su_condicion(client, auth_headers):
    payload = {
        "dimensions": [
            {"dimension_key": "greeting", "dimension_name": "Saludo", "weight": 50},
            {
                "dimension_key": "objections",
                "dimension_name": "Objeciones",
                "weight": 50,
                "allow_na": True,
                "na_condition": "  Solo si hay objeción.  ",
            },
        ]
    }
    r = client.put("/api/v1/config/rubric", json=payload, headers=auth_headers)
    assert r.status_code == 200, r.text
    por_clave = {d["dimension_key"]: d for d in r.json()}
    assert por_clave["objections"]["allow_na"] is True
    assert por_clave["objections"]["na_condition"] == "Solo si hay objeción."
    assert por_clave["greeting"]["allow_na"] is False

    # Si deja de poder no aplicar, la condición se va con ella.
    payload["dimensions"][1]["allow_na"] = False
    r = client.put("/api/v1/config/rubric", json=payload, headers=auth_headers)
    por_clave = {d["dimension_key"]: d for d in r.json()}
    assert por_clave["objections"]["na_condition"] is None


def test_el_detalle_de_la_llamada_devuelve_lo_que_no_aplico(
    client, db_session, admin_user, auth_headers
):
    call = Call(uploaded_by=admin_user.id, audio_url="x", status=CallStatus.DONE)
    db_session.add(call)
    db_session.flush()
    db_session.add(
        Analysis(
            call_id=call.id,
            global_score=80,
            dimension_scores={"greeting": 80},
            not_applicable=["objections"],
        )
    )
    db_session.commit()
    body = client.get(f"/api/v1/calls/{call.id}", headers=auth_headers).json()
    assert body["analysis"]["not_applicable"] == ["objections"]
