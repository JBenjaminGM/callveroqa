"""
Tests de administración de cuentas y contraseñas.

Lo que se protege, por orden de importancia:

- que **nunca** se pueda dejar la plataforma sin ningún administrador activo;
- que una baja cierre la puerta **en la siguiente petición**, no cuando caduque
  el token;
- que la contraseña generada se enseñe una vez y no se pueda volver a leer;
- que la cuenta de demostración pública no se pueda administrar.
"""

from starlette.requests import Request

from app.models.user import ROLE_ADMIN, ROLE_ASESOR, ROLE_JEFE, User
from app.utils.security import hash_password


def _crear(client, headers, **campos):
    payload = {"email": "nuevo@banco.com", "name": "Nuevo", "role": ROLE_JEFE}
    payload.update(campos)
    return client.post("/api/v1/users", json=payload, headers=headers)


def _login(client, email, password):
    return client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )


# ===============================================================
# Altas
# ===============================================================
def test_alta_genera_contrasena_y_permite_entrar(client, auth_headers):
    r = _crear(client, auth_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    generada = body["generated_password"]
    assert generada and len(generada) >= 10
    assert body["user"]["active"] is True

    entrada = _login(client, "nuevo@banco.com", generada)
    assert entrada.status_code == 200
    assert entrada.json()["user"]["email"] == "nuevo@banco.com"


def test_la_contrasena_generada_no_se_puede_volver_a_leer(client, auth_headers):
    _crear(client, auth_headers)
    lista = client.get("/api/v1/users", headers=auth_headers).json()
    nuevo = next(u for u in lista if u["email"] == "nuevo@banco.com")
    assert "password" not in nuevo and "password_hash" not in nuevo
    assert "generated_password" not in nuevo


def test_alta_con_contrasena_propia_la_valida(client, auth_headers):
    corta = _crear(client, auth_headers, password="corta")
    assert corta.status_code == 422
    assert "10 caracteres" in corta.json()["detail"]

    buena = _crear(client, auth_headers, password="una-contrasena-larga")
    assert buena.status_code == 201
    assert buena.json()["generated_password"] is None


def test_no_se_duplica_un_email(client, auth_headers):
    _crear(client, auth_headers)
    repetido = _crear(client, auth_headers, email="NUEVO@banco.com")
    assert repetido.status_code == 409


def test_un_asesor_necesita_ejecutivo_y_un_jefe_no_puede_tenerlo(
    client, auth_headers, sample_agent
):
    sin_agente = _crear(client, auth_headers, role=ROLE_ASESOR)
    assert sin_agente.status_code == 422

    con_agente = _crear(
        client, auth_headers, role=ROLE_ASESOR, agent_id=sample_agent.id,
        email="asesor2@banco.com",
    )
    assert con_agente.status_code == 201
    assert con_agente.json()["user"]["agent_id"] == sample_agent.id

    jefe_con_agente = _crear(
        client, auth_headers, agent_id=sample_agent.id, email="jefe2@banco.com"
    )
    assert jefe_con_agente.status_code == 422


def test_un_asesor_no_puede_administrar_cuentas(client, asesor_headers):
    assert client.get("/api/v1/users", headers=asesor_headers).status_code == 403
    assert _crear(client, asesor_headers).status_code == 403


# ===============================================================
# Bajas y roles
# ===============================================================
def test_la_baja_cierra_la_puerta_en_la_siguiente_peticion(
    client, auth_headers, db_session
):
    creado = _crear(client, auth_headers).json()
    token = _login(client, "nuevo@banco.com", creado["generated_password"]).json()[
        "access_token"
    ]
    suyas = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/auth/me", headers=suyas).status_code == 200

    baja = client.patch(
        f"/api/v1/users/{creado['user']['id']}",
        json={"active": False},
        headers=auth_headers,
    )
    assert baja.status_code == 200 and baja.json()["active"] is False

    # El token sigue siendo criptográficamente válido, pero ya no sirve.
    assert client.get("/api/v1/auth/me", headers=suyas).status_code == 403
    assert _login(client, "nuevo@banco.com", creado["generated_password"]).status_code == 401


def test_nunca_se_queda_la_plataforma_sin_administrador(
    client, auth_headers, admin_user
):
    """
    Con dos administradores se puede dar de baja a uno; al último, no.

    Se usa un tercero con rol de jefe para intentarlo, porque nadie puede
    tocarse a si mismo y sin ese tercero la regla no llegaria a evaluarse.
    """
    admin_b = _crear(
        client, auth_headers, email="admin2@banco.com", role=ROLE_ADMIN
    ).json()
    jefe_c = _crear(client, auth_headers, email="jefe3@banco.com").json()
    token_b = _login(client, "admin2@banco.com", admin_b["generated_password"]).json()[
        "access_token"
    ]
    token_c = _login(client, "jefe3@banco.com", jefe_c["generated_password"]).json()[
        "access_token"
    ]
    como_b = {"Authorization": f"Bearer {token_b}"}
    como_c = {"Authorization": f"Bearer {token_c}"}

    # Quedan dos admins: dar de baja al primero se permite.
    baja_a = client.patch(
        f"/api/v1/users/{admin_user.id}", json={"active": False}, headers=como_b
    )
    assert baja_a.status_code == 200, baja_a.text

    # B es el ultimo admin activo: ni un jefe puede desactivarlo ni bajarle el rol.
    r_baja = client.patch(
        f"/api/v1/users/{admin_b['user']['id']}", json={"active": False}, headers=como_c
    )
    r_rol = client.patch(
        f"/api/v1/users/{admin_b['user']['id']}", json={"role": ROLE_JEFE}, headers=como_c
    )
    assert r_baja.status_code == 409 and r_rol.status_code == 409
    assert "administrador" in r_baja.json()["detail"].lower()

    # Y B sigue entrando.
    assert client.get("/api/v1/auth/me", headers=como_b).status_code == 200


def test_nadie_puede_desactivarse_ni_cambiarse_el_rol_a_si_mismo(
    client, auth_headers, admin_user
):
    r = client.patch(
        f"/api/v1/users/{admin_user.id}", json={"active": False}, headers=auth_headers
    )
    assert r.status_code == 409
    assert "ti mismo" in r.json()["detail"]


def test_ascender_a_manager_suelta_el_vinculo_con_el_ejecutivo(
    client, auth_headers, sample_agent
):
    asesor = _crear(
        client, auth_headers, role=ROLE_ASESOR, agent_id=sample_agent.id,
        email="sube@banco.com",
    ).json()["user"]
    ascendido = client.patch(
        f"/api/v1/users/{asesor['id']}", json={"role": ROLE_JEFE}, headers=auth_headers
    ).json()
    assert ascendido["role"] == ROLE_JEFE
    assert ascendido["agent_id"] is None


# ===============================================================
# Contraseñas
# ===============================================================
def test_reseteo_por_administrador_devuelve_el_acceso(client, auth_headers):
    creado = _crear(client, auth_headers).json()
    nueva = client.post(
        f"/api/v1/users/{creado['user']['id']}/reset-password", headers=auth_headers
    ).json()["password"]

    assert _login(client, "nuevo@banco.com", creado["generated_password"]).status_code == 401
    assert _login(client, "nuevo@banco.com", nueva).status_code == 200


def test_cambio_de_contrasena_propio(client, auth_headers):
    creado = _crear(client, auth_headers).json()
    vieja = creado["generated_password"]
    token = _login(client, "nuevo@banco.com", vieja).json()["access_token"]
    suyas = {"Authorization": f"Bearer {token}"}

    mal = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "no-es-la-mia", "new_password": "otra-larga-1234"},
        headers=suyas,
    )
    assert mal.status_code == 400

    igual = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": vieja, "new_password": vieja},
        headers=suyas,
    )
    assert igual.status_code == 422

    bien = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": vieja, "new_password": "otra-larga-1234"},
        headers=suyas,
    )
    assert bien.status_code == 204
    assert _login(client, "nuevo@banco.com", vieja).status_code == 401
    assert _login(client, "nuevo@banco.com", "otra-larga-1234").status_code == 200


def test_la_cuenta_de_demostracion_no_se_administra(client, auth_headers, db_session):
    demo = User(
        email="demo@callveroqa.com",
        password_hash=hash_password("CallVeroQA-Demo-2026"),
        name="Invitado",
        role=ROLE_JEFE,
        is_readonly=True,
    )
    db_session.add(demo)
    db_session.commit()

    assert client.patch(
        f"/api/v1/users/{demo.id}", json={"name": "Otro"}, headers=auth_headers
    ).status_code == 403
    assert client.post(
        f"/api/v1/users/{demo.id}/reset-password", headers=auth_headers
    ).status_code == 403

    token = _login(client, "demo@callveroqa.com", "CallVeroQA-Demo-2026").json()[
        "access_token"
    ]
    suya = {"Authorization": f"Bearer {token}"}
    assert client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "CallVeroQA-Demo-2026", "new_password": "otra-larga-1234"},
        headers=suya,
    ).status_code == 403


# ===============================================================
# Límite de intentos de login
# ===============================================================
def test_la_clave_del_limite_de_login_separa_por_cuenta():
    """
    Fallar contra una cuenta no debe bloquear a las demás desde la misma IP.

    Un call center sale a internet por una sola IP pública: con la IP como
    clave, el error repetido de una persona dejaba al equipo sin entrar. El
    límite se prueba aquí y no por HTTP porque `conftest` lo desactiva para que
    los tests puedan loguearse muchas veces.
    """
    from app.limiter import login_rate_key

    def _peticion(cuerpo: bytes | None):
        scope = {
            "type": "http",
            "client": ("10.0.0.1", 1234),
            "headers": [],
            "method": "POST",
            "path": "/api/v1/auth/login",
        }
        req = Request(scope)
        if cuerpo is not None:
            req._body = cuerpo
        return req

    maria = login_rate_key(_peticion(b'{"email":"Maria@Banco.com","password":"x"}'))
    carlos = login_rate_key(_peticion(b'{"email":"carlos@banco.com","password":"x"}'))
    assert maria != carlos
    # El email se normaliza: MAYÚSCULAS y minúsculas son la misma cuenta.
    assert maria == login_rate_key(_peticion(b'{"email":"maria@banco.com","password":"y"}'))
    assert "10.0.0.1" in maria

    # Sin cuerpo legible se cae a la IP sola, que es lo prudente.
    assert login_rate_key(_peticion(None)) == "10.0.0.1"
    assert login_rate_key(_peticion(b"no-es-json")) == "10.0.0.1"
