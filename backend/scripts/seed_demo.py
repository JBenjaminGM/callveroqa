"""
Datos de demostración.

Siembra un histórico de 90 días de llamadas ya procesadas, para que quien abra
la plataforma por primera vez vea un panel con contenido en vez de vacío.

Qué genera:
- ~70 llamadas repartidas en 90 días, con más volumen en días laborables.
- Transcripción real de cada llamada, con sus tiempos exactos, y el archivo de
  audio correspondiente (lo que se oye coincide con lo que se lee).
- Notas por dimensión escritas a mano en `demo_conversations.py`, con una
  variación pequeña por llamada para que las gráficas no salgan planas.
- Tendencias con intención: María mejora, Lucía empeora y Carlos se mantiene.
  Así el ranking, las alertas y la evolución temporal cuentan algo.
- Revisiones humanas sobre parte de esas llamadas, con una discrepancia
  deliberada en un criterio concreto: el panel de calibración abre señalando
  algo real en vez de vacío.
- Respuestas de los asesores a sus evaluaciones, alguna con petición de revisión
  abierta, para que «a quién escuchar hoy» tenga algo urgente que proponer.

No llama a la IA: funciona sin clave y sin coste, y siempre produce lo mismo
(la semilla del azar es fija).

Uso:  SEED_DEMO=true python scripts/seed_demo.py
      o bien:      python scripts/seed_demo.py --force
"""

import os
import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import select  # noqa: E402

import demo_conversations as guiones  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.agent import Agent  # noqa: E402
from app.models.analysis import Analysis  # noqa: E402
from app.models.call import Call, CallStatus  # noqa: E402
from app.models.campaign import Campaign  # noqa: E402
from app.models.acknowledgement import Acknowledgement  # noqa: E402
from app.models.review import Review  # noqa: E402
from app.models.transcription import Transcription  # noqa: E402
from app.models.user import ROLE_JEFE, User  # noqa: E402
from app.services.conversation_metrics_service import (  # noqa: E402
    compute_conversation_metrics,
)
from app.services.storage_service import get_storage_provider  # noqa: E402
from app.utils.security import hash_password  # noqa: E402

# Cuenta de demostración pública. Su contraseña se publica a propósito en el
# README: es de solo lectura, así que compartirla no compromete nada. Solo
# existe si se pide el seed de demostración, nunca en un despliegue normal.
DEMO_EMAIL = "demo@callveroqa.com"
DEMO_PASSWORD = os.getenv("SEED_DEMO_PASSWORD", "CallVeroQA-Demo-2026")
# Cuenta demo de la marca anterior: se renombra (con la contraseña nueva) en vez
# de dejar dos cuentas públicas.
LEGACY_DEMO_EMAIL = "demo@callaibrate.com"

DIAS_DE_HISTORIAL = 90
LLAMADAS_OBJETIVO = 70
# Cuántas de esas llamadas llevan además revisión humana.
REVISIONES_OBJETIVO = 22
# Ventana en la que caen las peticiones de revisión de los asesores. Tiene que
# ser menor que el periodo con el que abre el panel (30 días) o no se verían.
DIAS_RECIENTES_PARA_ACUSE = 25
CARPETA_AUDIO = Path(__file__).resolve().parent.parent / "demo_audio"

# Cómo evoluciona cada ejecutivo a lo largo de los 90 días. El número es la
# probabilidad de que la llamada sea la "buena" al principio y al final del
# periodo; entre medias se interpola. Es lo que hace que la evolución temporal
# y las alertas de tendencia tengan algo que contar.
TENDENCIAS = {
    "María González": {"inicio": 0.15, "fin": 0.95},   # mejora mucho con el coaching
    "Carlos Ruiz": {"inicio": 0.74, "fin": 0.70},      # estable
    "Lucía Fernández": {"inicio": 0.95, "fin": 0.20},  # se deteriora
}

# Guiones disponibles por ejecutivo: (el que cumple, el que falla).
GUIONES_POR_EJECUTIVO = {
    "María González": ("tarjetas_alta", "tarjetas_baja"),
    "Carlos Ruiz": ("prestamos_alta", "prestamos_baja"),
    "Lucía Fernández": ("seguros_alta", "seguros_baja"),
}


def crear_usuario_demo(db) -> None:
    """Crea (o repara) la cuenta de demostración de solo lectura."""
    demo = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if demo is None:
        legacy = db.scalar(select(User).where(User.email == LEGACY_DEMO_EMAIL))
        if legacy is not None:
            legacy.email = DEMO_EMAIL
            legacy.password_hash = hash_password(DEMO_PASSWORD)
            demo = legacy
            print(f"[demo] Cuenta {LEGACY_DEMO_EMAIL} renombrada a {DEMO_EMAIL} / {DEMO_PASSWORD}")
    if demo is None:
        db.add(
            User(
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                name="Invitado (demostración)",
                role=ROLE_JEFE,
                is_readonly=True,
            )
        )
        print(f"[demo] Cuenta de demostración creada: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    elif not demo.is_readonly:
        # Nunca dejar la cuenta pública con permiso de escritura.
        demo.is_readonly = True
        print("[demo] La cuenta de demostración se ha vuelto a marcar como solo lectura.")
    db.commit()


def _quiere_sembrar() -> bool:
    """El seed de demostración solo corre si se pide explícitamente."""
    if "--force" in sys.argv:
        return True
    return os.getenv("SEED_DEMO", "").strip().lower() in {"1", "true", "yes", "si", "sí"}


def _dias_con_llamadas(rng: random.Random) -> list[date]:
    """
    Reparte las llamadas por días, con más volumen entre semana.

    Un histórico uniforme se ve artificial; uno con picos y valles se lee como
    actividad real.
    """
    hoy = date.today()
    dias: list[date] = []
    for atras in range(DIAS_DE_HISTORIAL):
        dia = hoy - timedelta(days=atras)
        if dia.weekday() >= 5:          # fin de semana: casi nada
            cuantas = rng.choices([0, 1], weights=[85, 15])[0]
        else:
            cuantas = rng.choices([0, 1, 2], weights=[25, 45, 30])[0]
        dias.extend([dia] * cuantas)
    rng.shuffle(dias)
    return dias[:LLAMADAS_OBJETIVO]


def _probabilidad_de_buena(ejecutivo: str, dia: date) -> float:
    """Interpola la tendencia del ejecutivo según lo reciente que sea el día."""
    t = TENDENCIAS[ejecutivo]
    antiguedad = (date.today() - dia).days
    avance = 1 - (antiguedad / DIAS_DE_HISTORIAL)   # 0 = lo más antiguo, 1 = hoy
    return t["inicio"] + (t["fin"] - t["inicio"]) * avance


def _notas_con_variacion(base: dict[str, int], rng: random.Random) -> dict[str, int]:
    """
    Aparta las notas del guion para que la distribución no salga bimodal.

    Con solo dos guiones por ejecutivo, los scores se agolpan en dos picos y la
    banda intermedia queda vacía, que es justo lo que delata unos datos
    inventados. Se aplica un desplazamiento común a toda la llamada —una llamada
    entera sale mejor o peor, no cada criterio por su cuenta— más un ruido
    pequeño por criterio.
    """
    # El +6 sube el conjunto lo justo para que las llamadas flojas caigan en la
    # banda intermedia en vez de amontonarse todas en rojo.
    desplazamiento = 6 + rng.gauss(0, 8)
    return {
        clave: max(15, min(100, round(valor + desplazamiento + rng.gauss(0, 3))))
        for clave, valor in base.items()
    }


def _score_global(notas: dict[str, int], pesos: dict[str, float]) -> int:
    total_peso = sum(pesos.get(k, 0) for k in notas) or 1
    acumulado = sum(nota * pesos.get(clave, 0) for clave, nota in notas.items())
    return int(round(acumulado / total_peso))


# Cómo se desvía la persona respecto a la IA en cada dimensión: (sesgo, ruido).
#
# La gracia está en que las tres filas cuentan historias distintas y el panel
# sabe distinguirlas:
#
# - `objections`: la persona puntúa sistemáticamente mucho más bajo. Sesgo
#   grande y desviación grande: el criterio está mal escrito y hay que
#   reescribirlo. Es el caso que el panel destaca arriba.
# - `assertiveness`: unas veces arriba y otras abajo, sin desviarse a ningún
#   lado. El sesgo se cancela pero la desviación no: también está mal
#   calibrado, y solo mirando el sesgo no se vería.
# - El resto: acuerdo razonable, ruido de un par de puntos.
DESVIACION_HUMANA = {
    "objections": (-19.0, 5.0),
    "assertiveness": (0.0, 11.0),
}
DESVIACION_POR_DEFECTO = (0.5, 2.5)

MOTIVOS = [
    "La objeción de precio se despachó sin argumentar; para mí no es un 80.",
    "Cumple el guion, pero no confirmó el importe de la cuota antes de cerrar.",
    "Buen manejo general. Bajo objeciones: no rebatió, solo repitió la oferta.",
    "El cierre fue correcto; el tono, algo plano para una venta en frío.",
    "Coincido casi del todo con la nota automática.",
    "Rebatió tarde y sin datos concretos. El resto, correcto.",
]


def sembrar_revisiones(db, rng, pesos: dict[str, float]) -> int:
    """
    Añade revisiones humanas sobre una parte de las llamadas ya creadas.

    Sin esto el panel de calibración abre vacío, que es la peor manera de
    enseñar precisamente la función que distingue al producto.
    """
    if db.scalar(select(Review).limit(1)) is not None:
        return 0

    # El revisor es el jefe de área. La cuenta de demostración también tiene rol
    # jefe, pero es de solo lectura: firmar revisiones con ella sería incoherente.
    revisor = db.scalar(
        select(User).where(User.role == ROLE_JEFE, User.is_readonly.is_(False))
    ) or db.scalar(select(User).order_by(User.id))
    if revisor is None:
        return 0

    llamadas = list(
        db.scalars(select(Call).where(Call.status == CallStatus.DONE).order_by(Call.id))
    )
    rng.shuffle(llamadas)

    creadas = 0
    for i, llamada in enumerate(llamadas[:REVISIONES_OBJETIVO]):
        if llamada.analysis is None:
            continue
        ia = llamada.analysis.dimension_scores or {}
        humanas = {}
        for clave, nota in ia.items():
            sesgo, ruido = DESVIACION_HUMANA.get(clave, DESVIACION_POR_DEFECTO)
            humanas[clave] = max(0, min(100, round(nota + sesgo + rng.gauss(0, ruido))))

        db.add(
            Review(
                call_id=llamada.id,
                reviewer_id=revisor.id,
                global_score=_score_global(humanas, pesos),
                dimension_scores=humanas,
                comment=rng.choice(MOTIVOS),
                # Dos de cada tres se puntuaron en sesión a ciegas: son las
                # únicas comparables sin sesgo de anclaje, y el panel permite
                # filtrar por ellas.
                blind=(i % 3 != 0),
                created_at=llamada.processed_at,
            )
        )
        creadas += 1

    db.commit()
    return creadas


# Lo que responden los asesores. Los dos primeros piden revisión: son los que
# hacen que «a quién escuchar hoy» abra con alguien esperando respuesta.
RESPUESTAS_DE_ASESORES = [
    ("El cliente ya era titular, el guion de captación no aplicaba aquí.", True),
    ("Rebatí la objeción en el minuto 3, creo que no se ha tenido en cuenta.", True),
    ("Recibido. Tengo que cerrar antes, se me va el cliente en el trámite.", False),
    ("De acuerdo con la evaluación, trabajo el cierre esta semana.", False),
    ("Anotado lo de confirmar la cuota. No volverá a pasar.", False),
    ("Visto.", False),
]


def sembrar_acuses(db, rng) -> int:
    """
    Añade respuestas de los asesores a algunas de sus evaluaciones.

    Sin esto el panel del asesor abre sin nada que hacer y «a quién escuchar
    hoy» solo puede proponer llamadas rojas: falta justo el caso que mejor
    explica la funcion, el de alguien esperando una respuesta.
    """
    if db.scalar(select(Acknowledgement).limit(1)) is not None:
        return 0

    # Solo llamadas asignadas a un ejecutivo: el acuse lo firma quien fue
    # evaluado, y una llamada sin asignar no tiene a quién.
    llamadas = [
        c
        for c in db.scalars(
            select(Call).where(Call.status == CallStatus.DONE).order_by(Call.id)
        )
        if c.agent_id is not None
    ]
    if not llamadas:
        return 0

    # Cada asesor responde desde su propia cuenta, si la tiene creada.
    usuarios_por_agente = {
        u.agent_id: u
        for u in db.scalars(select(User).where(User.agent_id.is_not(None)))
    }

    # Dos condiciones para que las peticiones de revisión se vean:
    #
    # - **recientes**: el panel abre con los últimos 30 días, y una petición más
    #   antigua no aparecería por ningún lado;
    # - **de las llamadas peor puntuadas**: nadie recurre un sobresaliente. Con
    #   un reparto al azar acababa habiendo un asesor discutiendo un 98.
    rng.shuffle(llamadas)
    limite = date.today() - timedelta(days=DIAS_RECIENTES_PARA_ACUSE)
    recientes = sorted(
        (c for c in llamadas if c.call_date and c.call_date >= limite),
        key=lambda c: c.analysis.global_score if c.analysis else 100,
    )
    piden = [r for r in RESPUESTAS_DE_ASESORES if r[1]]
    conformes = [r for r in RESPUESTAS_DE_ASESORES if not r[1]]

    usadas = {c.id for c in recientes[: len(piden)]}
    resto = [c for c in llamadas if c.id not in usadas]
    reparto = list(zip(piden, recientes)) + list(zip(conformes, resto))

    creados = 0
    for (comentario, pide_revision), llamada in reparto:
        usuario = usuarios_por_agente.get(llamada.agent_id)
        db.add(
            Acknowledgement(
                call_id=llamada.id,
                user_id=usuario.id if usuario else None,
                comment=comentario,
                review_requested=pide_revision,
                created_at=llamada.processed_at,
            )
        )
        creados += 1

    db.commit()
    return creados


def marcar_criterios_criticos(db) -> None:
    """
    Deja marcados como críticos los criterios que usa la demo.

    Respeta la decisión del jefe: si un criterio ya tiene la marca `critical`
    (true o false), es que alguien lo guardó desde Configuración y no se toca.
    Solo se marca lo que nunca se ha decidido, y se añade lo que falte.
    """
    from app.models.settings import RubricConfig

    cambios = 0
    for clave, nombres in guiones.CRITERIOS_CRITICOS_DEMO.items():
        fila = db.scalar(select(RubricConfig).where(RubricConfig.dimension_key == clave))
        if fila is None:
            continue
        criterios = [dict(c) for c in (fila.criteria or [])]
        por_nombre = {c.get("name"): c for c in criterios}
        for nombre in nombres:
            criterio = por_nombre.get(nombre)
            if criterio is None:
                criterios.append({"name": nombre, "enabled": True, "critical": True})
                cambios += 1
            elif "critical" not in criterio:
                criterio["critical"] = True
                cambios += 1
        fila.criteria = criterios  # reasignar para que se detecte el cambio
    db.commit()
    if cambios:
        print(f"[demo] {cambios} criterios de cumplimiento marcados como críticos.")


def completar_evidencia(db) -> int:
    """
    Añade evidencia y criterios críticos a llamadas de demo sembradas antes de
    que existieran. Sin duplicar: solo toca las que aún no tienen evidencia.
    """
    por_audio = {conv["audio"]: clave for clave, conv in guiones.CONVERSACIONES.items()}
    completadas = 0
    for analisis in db.scalars(select(Analysis).where(Analysis.ai_provider == "demo")):
        if analisis.dimension_evidence:
            continue
        nombre = analisis.call.audio_filename or ""
        clave = next((c for audio, c in por_audio.items() if nombre.endswith(audio)), None)
        if clave is None:
            continue
        analisis.dimension_evidence = guiones.evidencia(clave)
        criticos = guiones.CRITICOS.get(clave)
        if criticos and analisis.uncapped_score is None:
            analisis.critical_failures = criticos
            analisis.uncapped_score = analisis.global_score
            analisis.global_score = 0
        completadas += 1
    db.commit()
    return completadas


def sembrar() -> None:
    rng = random.Random(20260909)     # semilla fija: siempre el mismo resultado
    db = SessionLocal()
    almacen = get_storage_provider()

    try:
        crear_usuario_demo(db)
        marcar_criterios_criticos(db)

        # Los pesos de la rúbrica se leen de la base: si el jefe los cambió,
        # los scores de la demo siguen siendo coherentes con su configuración.
        from app.models.settings import RubricConfig
        pesos = {
            r.dimension_key: float(r.weight)
            for r in db.scalars(select(RubricConfig))
        }

        if db.scalar(select(Call).limit(1)) is not None:
            print("[demo] Ya hay llamadas en la base de datos. No se crean más.")
            # Las llamadas no se tocan, pero las revisiones sí pueden faltar:
            # una base sembrada antes de que existiera la calibración abriría el
            # panel vacío. Se rellenan sin duplicar nada.
            revisadas = sembrar_revisiones(db, rng, pesos)
            if revisadas:
                print(f"[demo] {revisadas} revisiones humanas añadidas.")
            acuses = sembrar_acuses(db, rng)
            if acuses:
                print(f"[demo] {acuses} respuestas de asesores añadidas.")
            completadas = completar_evidencia(db)
            if completadas:
                print(f"[demo] Evidencia y criterios críticos añadidos a {completadas} llamadas.")
            return

        admin = db.scalar(select(User).order_by(User.id))
        if admin is None:
            print("[demo] No hay usuarios. Ejecuta antes scripts/seed_data.py.")
            return

        ejecutivos = {a.name: a for a in db.scalars(select(Agent))}
        campanas = {c.name: c for c in db.scalars(select(Campaign))}
        faltan = set(GUIONES_POR_EJECUTIVO) - set(ejecutivos)
        if faltan:
            print(f"[demo] Faltan ejecutivos: {', '.join(sorted(faltan))}. Ejecuta seed_data.py.")
            return

        # El audio se copia una sola vez al almacenamiento y se reutiliza: son
        # seis grabaciones para setenta llamadas, y ocupan seis veces menos.
        audios_guardados: dict[str, str] = {}
        for clave, conv in guiones.CONVERSACIONES.items():
            origen = CARPETA_AUDIO / conv["audio"]
            if not origen.exists():
                print(f"[demo] Falta el audio {origen.name}. Se siembra sin audio.")
                continue
            audios_guardados[clave] = almacen.save(origen.read_bytes(), conv["audio"])

        creadas = 0
        for dia in _dias_con_llamadas(rng):
            ejecutivo_nombre = rng.choice(list(GUIONES_POR_EJECUTIVO))
            agente = ejecutivos[ejecutivo_nombre]
            buena, mala = GUIONES_POR_EJECUTIVO[ejecutivo_nombre]
            clave = buena if rng.random() < _probabilidad_de_buena(ejecutivo_nombre, dia) else mala
            conv = guiones.CONVERSACIONES[clave]

            segmentos = guiones.construir_segmentos(clave)
            duracion = guiones.duracion_total(clave)
            momento = datetime.combine(
                dia, time(hour=rng.randint(9, 18), minute=rng.randint(0, 59))
            )

            llamada = Call(
                uploaded_by=admin.id,
                agent_id=agente.id,
                audio_url=audios_guardados.get(clave, f"demo://{conv['audio']}"),
                audio_filename=f"{dia.isoformat()}_{conv['audio']}",
                duration_seconds=duracion,
                language="es",
                status=CallStatus.DONE,
                detected_agent_name=conv["ejecutivo"],
                call_date=dia,
                campaign_type=conv["campana"],
                campaign_id=campanas[conv["campana"]].id if conv["campana"] in campanas else None,
                responsible="Datos de demostración",
                created_at=momento,
                processed_at=momento + timedelta(minutes=2),
                conversation_metrics=compute_conversation_metrics(segmentos, duracion),
            )
            db.add(llamada)
            db.flush()

            db.add(
                Transcription(
                    call_id=llamada.id,
                    full_text=guiones.texto_completo(clave),
                    segments=segmentos,
                    language="es",
                )
            )

            notas = _notas_con_variacion(conv["scores"], rng)
            criticos = guiones.CRITICOS.get(clave) or None
            nota = _score_global(notas, pesos)
            db.add(
                Analysis(
                    call_id=llamada.id,
                    global_score=0 if criticos else nota,
                    uncapped_score=nota if criticos else None,
                    critical_failures=criticos,
                    dimension_evidence=guiones.evidencia(clave),
                    dimension_scores=notas,
                    recommendations=conv["recomendaciones"],
                    summary=conv["resumen"],
                    ai_provider="demo",
                    ai_model="datos-de-demostracion",
                    created_at=momento + timedelta(minutes=2),
                )
            )
            creadas += 1

        db.commit()
        print(f"[demo] {creadas} llamadas de demostración creadas en {DIAS_DE_HISTORIAL} días.")
        print("[demo] Tendencias: María mejora · Carlos estable · Lucía se deteriora.")

        revisadas = sembrar_revisiones(db, rng, pesos)
        if revisadas:
            print(
                f"[demo] {revisadas} revisiones humanas creadas. El panel de "
                "calibración señala «Manejo de objeciones» como peor calibrado."
            )

        acuses = sembrar_acuses(db, rng)
        if acuses:
            print(
                f"[demo] {acuses} respuestas de asesores creadas, dos con "
                "petición de revisión abierta."
            )
    finally:
        db.close()


if __name__ == "__main__":
    if not _quiere_sembrar():
        print(
            "[demo] Omitido. Para sembrar datos de demostración usa SEED_DEMO=true "
            "o el argumento --force."
        )
    else:
        sembrar()
