"""
Coaching medible: si una sesión de coaching movió la nota, y cuánto.

Una sesión se hace con un asesor sobre **una** dimensión de la rúbrica y en un
día concreto. Medirla es comparar esa misma dimensión en sus llamadas de antes
y de después de ese día. Tres decisiones sostienen la medida:

1. **Se compara contra el equipo.** Si en esas mismas semanas todo el equipo
   sube cinco puntos en esa dimensión (se tocó la rúbrica, cambió la campaña,
   llegó un modelo nuevo de IA), esos cinco puntos no son del coaching. El
   efecto que se juzga es la mejora del asesor **menos** la del resto.
2. **Sin datos suficientes no hay veredicto.** Con una o dos llamadas a cada
   lado, cualquier diferencia es ruido. Se dice «faltan llamadas» en vez de
   inventar una mejora.
3. **Se mide con la nota de la IA por dimensión**, no con las revisiones
   humanas: la IA puntúa todas las llamadas con el mismo criterio, las
   revisiones son una muestra y cambiarían de revisor a revisor.
"""

from datetime import date, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.models.call import Call, CallStatus
from app.models.coaching_session import CoachingSession
from app.models.settings import RubricConfig

# Días que se miran a cada lado de la sesión. Treinta dan margen a que el
# asesor tenga llamadas suficientes y son lo bastante cortos para que lo que
# pase después se pueda atribuir a la sesión y no a cualquier otra cosa.
VENTANA_DIAS = 30

# Llamadas mínimas a cada lado para emitir un veredicto. Por debajo, la media
# depende de una sola llamada buena o mala.
MIN_LLAMADAS = 3

# Diferencia neta (en puntos sobre 100) a partir de la cual el cambio cuenta.
# Por debajo es la variación normal de una semana a otra.
CAMBIO_RELEVANTE = 5


def _fecha(call: Call) -> date:
    """El día de la llamada: la fecha declarada o, si falta, la de subida."""
    return call.call_date or call.created_at.date()


def dimension_names(db: Session) -> dict[str, str]:
    """{dimension_key: nombre} de la rúbrica vigente."""
    return {
        r.dimension_key: r.dimension_name for r in db.scalars(select(RubricConfig))
    }


def _rows_between(db: Session, desde: date, hasta: date) -> list[tuple[Call, Analysis]]:
    """Llamadas analizadas cuyo día cae en [desde, hasta], de cualquier asesor."""
    stmt = (
        select(Call, Analysis)
        .join(Analysis, Analysis.call_id == Call.id)
        .where(Call.status == CallStatus.DONE)
        .where(
            or_(
                and_(Call.call_date.is_not(None), Call.call_date.between(desde, hasta)),
                # Sin fecha declarada se usa la de subida. El margen de un día
                # cubre que created_at lleva hora y la comparación es por día.
                and_(
                    Call.call_date.is_(None),
                    Call.created_at >= desde,
                    Call.created_at < hasta + timedelta(days=1),
                ),
            )
        )
    )
    return list(db.execute(stmt).all())


def _media(valores: list[int]) -> float | None:
    return round(sum(valores) / len(valores), 1) if valores else None


def _veredicto(antes: int, despues: int, cambio: float | None) -> str:
    """
    Qué se puede decir de la sesión con los datos que hay.

    `no_baseline`: no había llamadas suficientes antes, así que no hay contra
    qué comparar (y no la habrá nunca: el pasado no crece). `pending`: la línea
    base existe pero aún no hay llamadas suficientes después.
    """
    if antes < MIN_LLAMADAS:
        return "no_baseline"
    if despues < MIN_LLAMADAS or cambio is None:
        return "pending"
    if cambio >= CAMBIO_RELEVANTE:
        return "improved"
    if cambio <= -CAMBIO_RELEVANTE:
        return "worsened"
    return "no_change"


def measure(
    session: CoachingSession,
    rows: list[tuple[Call, Analysis]],
    window_days: int = VENTANA_DIAS,
    today: date | None = None,
) -> dict:
    """
    Antes y después de una sesión, a partir de las filas ya cargadas.

    Recibe las filas en vez de consultarlas para que un listado de sesiones
    haga una sola consulta en lugar de una por sesión.

    El propio día de la sesión no cuenta en ningún lado: una llamada de esa
    mañana pudo ser antes o después de sentarse a hablar.
    """
    today = today or date.today()
    key = session.dimension_key
    inicio = session.held_on - timedelta(days=window_days)
    fin = session.held_on + timedelta(days=window_days)

    puntos: list[dict] = []
    propio = {"before": [], "after": []}
    equipo = {"before": [], "after": []}

    for call, analysis in rows:
        dia = _fecha(call)
        if not (inicio <= dia <= fin) or dia == session.held_on:
            continue
        nota = (analysis.dimension_scores or {}).get(key)
        # Una llamada donde la dimensión no se puntuó (no aplicaba, o la
        # rúbrica era otra) no dice nada de ella: ni a favor ni en contra.
        if nota is None:
            continue
        fase = "before" if dia < session.held_on else "after"
        if call.agent_id == session.agent_id:
            propio[fase].append(int(nota))
            puntos.append(
                {"call_id": call.id, "date": dia, "score": int(nota), "phase": fase}
            )
        elif call.agent_id is not None:
            equipo[fase].append(int(nota))

    antes, despues = _media(propio["before"]), _media(propio["after"])
    delta = round(despues - antes, 1) if antes is not None and despues is not None else None

    eq_antes, eq_despues = _media(equipo["before"]), _media(equipo["after"])
    equipo_valido = (
        len(equipo["before"]) >= MIN_LLAMADAS and len(equipo["after"]) >= MIN_LLAMADAS
    )
    team_delta = round(eq_despues - eq_antes, 1) if equipo_valido else None
    if delta is None:
        net = None
    elif team_delta is not None:
        net = round(delta - team_delta, 1)
    elif not equipo["before"] and not equipo["after"]:
        # Nadie más puntúa esa dimensión (un equipo de una persona, o una
        # dimensión que solo se usa en su campaña): el cambio bruto es lo mejor
        # que se puede decir.
        net = delta
    else:
        # Hay equipo pero aún no suficiente para comparar. Juzgar el bruto
        # mientras tanto daría «funcionó» a la semana de la sesión por algo que
        # quizá le pasó a todos; se espera.
        net = None

    puntos.sort(key=lambda p: (p["date"], p["call_id"]))
    return {
        "window_days": window_days,
        "window_start": inicio,
        "window_end": fin,
        # Mientras no termine la ventana, el «después» todavía puede cambiar.
        "window_closed": today > fin,
        "before_count": len(propio["before"]),
        "before_avg": antes,
        "after_count": len(propio["after"]),
        "after_avg": despues,
        "delta": delta,
        "team_before_avg": eq_antes,
        "team_after_avg": eq_despues,
        "team_delta": team_delta,
        "net_delta": net,
        "verdict": _veredicto(len(propio["before"]), len(propio["after"]), net),
        "points": puntos,
    }


def measure_many(
    db: Session, sessions: list[CoachingSession], window_days: int = VENTANA_DIAS
) -> dict[int, dict]:
    """Mide varias sesiones con una sola consulta a las llamadas."""
    if not sessions:
        return {}
    desde = min(s.held_on for s in sessions) - timedelta(days=window_days)
    hasta = max(s.held_on for s in sessions) + timedelta(days=window_days)
    rows = _rows_between(db, desde, hasta)
    return {s.id: measure(s, rows, window_days) for s in sessions}


def suggest_dimensions(
    db: Session, agent_id: int, days: int = VENTANA_DIAS, limit: int = 3
) -> list[dict]:
    """
    Sobre qué dimensiones merece la pena hacer coaching a este asesor.

    Se ordena por la distancia a la media del equipo, no por la nota absoluta:
    una dimensión donde todos puntúan bajo es un problema de la rúbrica o del
    producto, no de esta persona, y un coaching individual no lo arreglará.
    """
    hoy = date.today()
    rows = _rows_between(db, hoy - timedelta(days=days), hoy)
    propio: dict[str, list[int]] = {}
    equipo: dict[str, list[int]] = {}
    for call, analysis in rows:
        if call.agent_id is None:
            continue
        destino = propio if call.agent_id == agent_id else equipo
        for key, nota in (analysis.dimension_scores or {}).items():
            if nota is not None:
                destino.setdefault(key, []).append(int(nota))

    nombres = dimension_names(db)
    sugerencias = []
    for key, notas in propio.items():
        if key not in nombres or len(notas) < MIN_LLAMADAS:
            continue
        media = sum(notas) / len(notas)
        del_equipo = equipo.get(key)
        media_equipo = sum(del_equipo) / len(del_equipo) if del_equipo else None
        sugerencias.append(
            {
                "dimension_key": key,
                "dimension_name": nombres[key],
                "agent_avg": round(media, 1),
                "team_avg": round(media_equipo, 1) if media_equipo is not None else None,
                "gap": round(media - media_equipo, 1) if media_equipo is not None else None,
                "calls": len(notas),
            }
        )
    # Primero la que más se aleja por debajo del equipo; sin equipo, la más baja.
    sugerencias.sort(
        key=lambda s: s["gap"] if s["gap"] is not None else s["agent_avg"] - 100
    )
    return sugerencias[:limit]
