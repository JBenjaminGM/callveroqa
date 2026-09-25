"""
Script de datos iniciales (seed).

Crea, de forma idempotente (no duplica si ya existen):
- Usuarios: un administrador y un jefe de área.
- Las 7 dimensiones de la rúbrica de evaluación (con subcriterios).
- Los settings globales por defecto (idioma + umbrales QA).
- 3 ejecutivos de ejemplo y una cuenta de asesor por cada uno.
- 3 campañas de ejemplo con su nota de producto.

Las contraseñas de las cuentas de ejemplo NO están en el código: se toman de
SEED_ADMIN_PASSWORD / SEED_JEFE_PASSWORD / SEED_ASESOR_PASSWORD si están
definidas y, si no, se generan aleatorias y se imprimen UNA sola vez al final.

Uso:  python scripts/seed_data.py
"""

import os
import secrets
import sys
from datetime import date
from pathlib import Path

# Permite ejecutar el script directamente (añade la raíz del proyecto al path).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.agent import Agent  # noqa: E402
from app.models.campaign import Campaign  # noqa: E402
from app.models.settings import AppSettings, RubricConfig  # noqa: E402
from app.models.user import (  # noqa: E402
    ROLE_ADMIN,
    ROLE_ASESOR,
    ROLE_JEFE,
    User,
)
from app.utils.security import hash_password, verify_password  # noqa: E402

# Cuentas de gestión de ejemplo. Las contraseñas se resuelven en tiempo de
# ejecución (ver _resolve_password), nunca se escriben aquí.
ADMIN_EMAIL = "admin@callveroqa.com"
JEFE_EMAIL = "jefe@callveroqa.com"

# Emails de las marcas anteriores. Si existe la cuenta vieja y no la nueva, se
# renombra en vez de duplicarla: así conserva su historial y sus permisos.
# Se recorren en orden, de la marca más reciente a la más antigua.
LEGACY_EMAILS = {
    "admin@callaibrate.com": ADMIN_EMAIL,
    "jefe@callaibrate.com": JEFE_EMAIL,
    "admin@callqa.com": ADMIN_EMAIL,
    "jefe@callqa.com": JEFE_EMAIL,
}

# Contraseñas que versiones anteriores de este seed fijaban en el código y que
# llegaron a estar publicadas en el repositorio. Cualquier cuenta sembrada que
# todavía use una de ellas se rota a una contraseña aleatoria.
PUBLISHED_PASSWORDS = ("Admin123!", "Jefe123!", "Asesor123!")

# Credenciales generadas durante esta ejecución, para imprimirlas al terminar.
_NEW_CREDENTIALS: list[tuple[str, str]] = []


def _resolve_password(env_var: str, email: str) -> str:
    """
    Contraseña para una cuenta sembrada.

    Usa la variable de entorno si está definida (útil en CI y en despliegues
    controlados). Si no, genera una aleatoria y la anota para mostrarla al final:
    es la única vez que se podrá leer.
    """
    from_env = os.getenv(env_var)
    if from_env:
        return from_env
    generated = secrets.token_urlsafe(12)
    _NEW_CREDENTIALS.append((email, generated))
    return generated


def _print_new_credentials() -> None:
    """Muestra, una sola vez, las contraseñas generadas en esta ejecución."""
    if not _NEW_CREDENTIALS:
        return
    line = "=" * 68
    print()
    print(line)
    print("CREDENCIALES GENERADAS - se muestran una sola vez. Guardalas ahora.")
    print(line)
    for email, password in _NEW_CREDENTIALS:
        print(f"  {email:<34} {password}")
    print(line)
    print("Para fijarlas tu mismo, define SEED_ADMIN_PASSWORD, SEED_JEFE_PASSWORD")
    print("y SEED_ASESOR_PASSWORD antes de ejecutar el seed.")
    print()


# Las 7 dimensiones de la rúbrica (regla de negocio RN-01).
RUBRIC = [
    ("greeting", "Saludo y protocolo de apertura/cierre", 14.28, 1),
    ("assertiveness", "Asertividad y tono", 14.28, 2),
    ("promotions", "Mención correcta de promociones/productos", 14.28, 3),
    ("compliance", "Cumplimiento normativo", 14.28, 4),
    ("resolution", "Resolución efectiva del motivo", 14.28, 5),
    ("objections", "Manejo de objeciones", 14.28, 6),
    ("sentiment", "Detección de sentimiento del cliente", 14.32, 7),
]

# Subcriterios (subcategorías) por defecto de cada dimensión. Cada uno se puede
# activar/desactivar desde Configuración; la IA solo evalúa los activos.
CRITERIA = {
    "greeting": ["Saludo inicial", "Identificación del ejecutivo y banco", "Aviso de grabación", "Despedida y cierre"],
    "assertiveness": ["Empatía", "Claridad al explicar", "Paciencia", "Escucha activa", "Tono profesional"],
    "promotions": ["Menciona productos relevantes", "Explica beneficios", "Condiciones claras y completas"],
    "compliance": [
        "Disclaimers obligatorios",
        "Sin afirmaciones prohibidas",
        "Protección de datos sensibles",
        "Solicitud de consentimiento",
    ],
    "resolution": ["Atiende el motivo de la llamada", "Ofrece solución concreta", "Confirma la resolución"],
    "objections": ["Identifica la objeción", "Responde con argumentos", "Persuasión profesional"],
    "sentiment": ["Satisfacción percibida", "Tono emocional del cliente", "Cierre en positivo"],
}

# Subcriterios críticos (auto-fail) por defecto: en banca, omitir un disclaimer
# obligatorio o afirmar algo prohibido suspende la llamada, no le resta puntos.
CRITICAL_BY_DEFAULT = {
    "compliance": {"Disclaimers obligatorios", "Sin afirmaciones prohibidas"},
}

# Dimensiones que pueden no aplicar a una llamada, y cuándo. Solo se aplica al
# crear la dimensión: si el jefe lo cambia, ningún arranque se lo deshace. Las
# bases anteriores las reciben de la migración 0016, con el mismo texto.
NA_POR_DEFECTO = {
    "objections": "Solo aplica si el cliente plantea alguna objeción, duda o reparo.",
    "promotions": (
        "Solo aplica si la llamada es de venta o el cliente pregunta por un "
        "producto; no en consultas, reclamos o gestiones."
    ),
}

# El proveedor de IA/transcripción lo fija la variable de entorno, no la BD.
SETTINGS = {
    "default_language": "es",
}

AGENTS = [
    ("María González", "maria@banco.com", "Tarjetas Premium", date(2024, 1, 15)),
    ("Carlos Ruiz", "carlos@banco.com", "Préstamos", date(2024, 3, 1)),
    ("Lucía Fernández", "lucia@banco.com", "Seguros", date(2023, 11, 20)),
]

# Campañas de ejemplo con su nota de producto (la oferta que el ejecutivo debe
# presentar). Coinciden con las campañas de los ejecutivos demo.
CAMPAIGNS = [
    {
        "name": "Tarjetas Premium",
        "product_service": "Tarjeta de crédito Premium",
        "offer_description": (
            "Tarjeta de crédito Premium sin cuota de mantenimiento el primer año, "
            "con beneficios exclusivos de viajes y compras."
        ),
        "key_benefits": [
            "Sin cuota de mantenimiento el primer año",
            "2% de cashback en todas las compras",
            "Acceso a salas VIP de aeropuerto",
            "Seguro de viaje incluido",
        ],
        "pricing_conditions": (
            "TEA desde 39.9%. Cuota de mantenimiento de S/ 25 al mes a partir del "
            "segundo año. Línea de crédito sujeta a evaluación."
        ),
        "customer_requirements": "Ingresos mínimos de S/ 3,000 mensuales y buen historial crediticio.",
        "mandatory_phrases": [
            "Informar la Tasa Efectiva Anual (TEA)",
            "Mencionar que la aprobación está sujeta a evaluación crediticia",
        ],
        "prohibited_claims": [
            "No afirmar que la tarjeta es gratuita de por vida",
            "No garantizar la aprobación inmediata",
        ],
        "target_audience": "Clientes con ingresos medios-altos y buen perfil crediticio.",
    },
    {
        "name": "Préstamos",
        "product_service": "Préstamo personal de libre disponibilidad",
        "offer_description": (
            "Préstamo personal con desembolso rápido y cuotas fijas mensuales."
        ),
        "key_benefits": [
            "Desembolso en 24 horas",
            "Cuotas fijas mensuales",
            "Sin penalidad por pago anticipado",
        ],
        "pricing_conditions": "TEA desde 29.9% según perfil. Plazos de 6 a 48 meses.",
        "customer_requirements": "Antigüedad laboral mínima de 6 meses e ingresos demostrables.",
        "mandatory_phrases": [
            "Informar la TEA y el monto total a pagar",
            "Indicar el número de cuotas y su importe",
        ],
        "prohibited_claims": ["No prometer tasas que no estén aprobadas"],
        "target_audience": "Clientes dependientes o independientes con ingresos demostrables.",
    },
    {
        "name": "Seguros",
        "product_service": "Seguro de protección financiera",
        "offer_description": (
            "Seguro de protección financiera que cubre al titular ante imprevistos "
            "como desempleo o incapacidad."
        ),
        "key_benefits": [
            "Cobertura ante desempleo o incapacidad",
            "Primas accesibles",
            "Activación inmediata",
        ],
        "pricing_conditions": "Prima mensual desde S/ 15 según la cobertura elegida.",
        "customer_requirements": "Ser titular de un producto del banco.",
        "mandatory_phrases": [
            "Explicar las exclusiones de la cobertura",
            "Mencionar el periodo de carencia",
        ],
        "prohibited_claims": ["No afirmar que cubre cualquier situación sin excepciones"],
        "target_audience": "Clientes con productos activos que buscan protección financiera.",
    },
]


def seed() -> None:
    """Inserta los datos iniciales si aún no existen."""
    db = SessionLocal()
    try:
        # --- Migración: cuentas creadas con los emails de la marca anterior ---
        for legacy_email, new_email in LEGACY_EMAILS.items():
            legacy = db.scalar(select(User).where(User.email == legacy_email))
            already_migrated = db.scalar(
                select(User).where(User.email == new_email)
            )
            if legacy is not None and already_migrated is None:
                legacy.email = new_email
                print(f"[seed] Cuenta {legacy_email} renombrada a {new_email}.")
        db.flush()

        # --- Rotación de las contraseñas que llegaron a ser públicas ---
        seeded_emails = {ADMIN_EMAIL, JEFE_EMAIL} | {email for _, email, _, _ in AGENTS}
        for user in db.scalars(select(User).where(User.email.in_(seeded_emails))):
            if any(verify_password(p, user.password_hash) for p in PUBLISHED_PASSWORDS):
                rotated = secrets.token_urlsafe(12)
                user.password_hash = hash_password(rotated)
                _NEW_CREDENTIALS.append((user.email, rotated))
                print(f"[seed] Contraseña rotada para {user.email} (era pública).")

        # --- Usuario administrador (se garantiza el rol admin) ---
        admin = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if admin is None:
            db.add(
                User(
                    email=ADMIN_EMAIL,
                    password_hash=hash_password(
                        _resolve_password("SEED_ADMIN_PASSWORD", ADMIN_EMAIL)
                    ),
                    name="Administrador",
                    role=ROLE_ADMIN,
                )
            )
            print(f"[seed] Usuario administrador creado: {ADMIN_EMAIL}")
        elif admin.role != ROLE_ADMIN:
            # Corrige cuentas legacy que la migración 0005 dejó como 'jefe'.
            admin.role = ROLE_ADMIN
            print(f"[seed] Rol de {ADMIN_EMAIL} actualizado a admin.")
        else:
            print("[seed] El usuario administrador ya existía.")

        # --- Usuario jefe de área ---
        if db.scalar(select(User).where(User.email == JEFE_EMAIL)) is None:
            db.add(
                User(
                    email=JEFE_EMAIL,
                    password_hash=hash_password(
                        _resolve_password("SEED_JEFE_PASSWORD", JEFE_EMAIL)
                    ),
                    name="Jefe de Área QA",
                    role=ROLE_JEFE,
                )
            )
            print(f"[seed] Usuario jefe de área creado: {JEFE_EMAIL}")

        # --- Rúbrica ---
        for key, name, weight, order in RUBRIC:
            default_criteria = [
                {
                    "name": c,
                    "enabled": True,
                    "critical": c in CRITICAL_BY_DEFAULT.get(key, set()),
                }
                for c in CRITERIA.get(key, [])
            ]
            existing = db.scalar(
                select(RubricConfig).where(RubricConfig.dimension_key == key)
            )
            if existing is None:
                db.add(
                    RubricConfig(
                        dimension_key=key,
                        dimension_name=name,
                        weight=weight,
                        display_order=order,
                        criteria=default_criteria,
                        allow_na=key in NA_POR_DEFECTO,
                        na_condition=NA_POR_DEFECTO.get(key),
                    )
                )
            elif not existing.criteria:
                # Backfill: si la dimensión ya existía sin subcriterios, los añade.
                existing.criteria = default_criteria
        print("[seed] Rúbrica de 7 dimensiones verificada.")

        # --- Settings globales ---
        for key, value in SETTINGS.items():
            if db.get(AppSettings, key) is None:
                db.add(AppSettings(key=key, value=value))
        print("[seed] Settings globales verificados.")

        # --- Ejecutivos de ejemplo ---
        for name, email, campaign, start in AGENTS:
            if db.scalar(select(Agent).where(Agent.email == email)) is None:
                db.add(
                    Agent(name=name, email=email, campaign=campaign, start_date=start)
                )
        db.flush()  # asegura los IDs de los ejecutivos recién creados
        print("[seed] Ejecutivos de ejemplo verificados.")

        # --- Cuentas de acceso de asesor (una por ejecutivo de ejemplo) ---
        for name, email, campaign, start in AGENTS:
            agent = db.scalar(select(Agent).where(Agent.email == email))
            if agent is not None and (
                db.scalar(select(User).where(User.email == email)) is None
            ):
                db.add(
                    User(
                        email=email,
                        password_hash=hash_password(
                            _resolve_password("SEED_ASESOR_PASSWORD", email)
                        ),
                        name=name,
                        role=ROLE_ASESOR,
                        agent_id=agent.id,
                    )
                )
        print("[seed] Cuentas de asesor verificadas.")

        # --- Campañas de ejemplo con su nota de producto ---
        for camp in CAMPAIGNS:
            existing = db.scalar(select(Campaign).where(Campaign.name == camp["name"]))
            if existing is None:
                db.add(Campaign(**camp))
            elif not existing.offer_description:
                # La campaña ya existía pero sin nota (p.ej. creada por el backfill
                # de la migración): se rellenan SOLO sus campos vacíos.
                for key, value in camp.items():
                    if key != "name" and not getattr(existing, key, None):
                        setattr(existing, key, value)
        print("[seed] Campañas de ejemplo verificadas.")

        db.commit()
        print("[seed] Datos iniciales cargados correctamente.")
        _print_new_credentials()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
