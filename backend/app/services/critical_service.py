"""
Suspendidas por criterio crítico: quién, cuántas y hacia dónde van.

La alerta por llamada ya existía: «esta llamada se suspendió». Lo que no se
veía era el patrón. Una suspensión suelta es un despiste; tres de la misma
persona en un mes, o un equipo que pasa del 5 % al 20 %, es un riesgo normativo
que alguien tiene que atajar antes de que lo encuentre una auditoría.

Todo sale de `Analysis.critical_failures`, que ya viene saneado contra la
rúbrica (solo cuenta lo que la rúbrica marca como crítico).
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from app.models.analysis import Analysis
from app.models.call import Call

# Suspensiones de una misma persona en el periodo a partir de las cuales deja de
# ser un despiste y se avisa.
MIN_SUSPENSIONES_ASESOR = 2

# Subida (en puntos porcentuales) de la tasa de suspendidas entre la primera y
# la segunda mitad del periodo para avisar de que la cosa va a peor.
SUBIDA_RELEVANTE = 15

# Llamadas mínimas en cada mitad para que la comparación signifique algo: con
# dos llamadas, una suspendida es un 50 %.
MIN_LLAMADAS_POR_MITAD = 3


def _pct(parte: int, total: int) -> float:
    return round(parte / total * 100, 1) if total else 0.0


def _suspendida(analysis: Analysis) -> bool:
    return bool(analysis.critical_failures)


def _mitades(
    rows: list[tuple[Call, Analysis]], start: datetime, end: datetime
) -> tuple[float | None, float | None]:
    """Tasa de suspendidas en la primera y la segunda mitad de la ventana."""
    mitad = start + (end - start) / 2
    primera = [a for c, a in rows if c.created_at < mitad]
    segunda = [a for c, a in rows if c.created_at >= mitad]
    if len(primera) < MIN_LLAMADAS_POR_MITAD or len(segunda) < MIN_LLAMADAS_POR_MITAD:
        return None, None
    return (
        _pct(sum(map(_suspendida, primera)), len(primera)),
        _pct(sum(map(_suspendida, segunda)), len(segunda)),
    )


def _criterio_mas_repetido(rows: list[tuple[Call, Analysis]]) -> str | None:
    cuenta = Counter(
        f.get("criterion")
        for _, a in rows
        for f in (a.critical_failures or [])
        if f.get("criterion")
    )
    return cuenta.most_common(1)[0][0] if cuenta else None


def critical_report(
    rows: list[tuple[Call, Analysis]],
    start: datetime,
    end: datetime,
    agent_names: dict[int, str],
) -> dict:
    """Tasa de suspendidas del periodo: total, por semana, por asesor y por criterio."""
    total = len(rows)
    suspendidas = sum(1 for _, a in rows if _suspendida(a))
    antes, despues = _mitades(rows, start, end)

    # Semanas desde el lunes de la primera: una serie diaria con dos o tres
    # llamadas por día sería puro ruido de 0 % y 100 %.
    lunes = (start - timedelta(days=start.weekday())).date()
    semanas: dict = {}
    dia = lunes
    while dia <= end.date():
        semanas[dia] = [0, 0]
        dia += timedelta(days=7)
    for call, analysis in rows:
        d = call.created_at.date()
        clave = d - timedelta(days=d.weekday())
        if clave in semanas:
            semanas[clave][0] += 1
            semanas[clave][1] += int(_suspendida(analysis))

    por_asesor: dict[int, list[tuple[Call, Analysis]]] = defaultdict(list)
    for call, analysis in rows:
        if call.agent_id is not None:
            por_asesor[call.agent_id].append((call, analysis))

    asesores = []
    for agent_id, suyas in por_asesor.items():
        n_susp = sum(1 for _, a in suyas if _suspendida(a))
        a_antes, a_despues = _mitades(suyas, start, end)
        asesores.append(
            {
                "agent_id": agent_id,
                "agent_name": agent_names.get(agent_id, f"Ejecutivo {agent_id}"),
                "total_calls": len(suyas),
                "critical_calls": n_susp,
                "critical_pct": _pct(n_susp, len(suyas)),
                "first_half_pct": a_antes,
                "second_half_pct": a_despues,
                "top_criterion": _criterio_mas_repetido(suyas),
            }
        )
    # Primero quien más suspende; a igualdad, quien lo hace en más proporción.
    asesores.sort(key=lambda a: (-a["critical_calls"], -a["critical_pct"]))

    criterios = Counter(
        f.get("criterion")
        for _, a in rows
        for f in (a.critical_failures or [])
        if f.get("criterion")
    )

    return {
        "total_calls": total,
        "critical_calls": suspendidas,
        "critical_pct": _pct(suspendidas, total),
        "first_half_pct": antes,
        "second_half_pct": despues,
        "weekly": [
            {
                "week_start": semana,
                "total_calls": n,
                "critical_calls": s,
                "critical_pct": _pct(s, n),
            }
            for semana, (n, s) in semanas.items()
        ],
        "by_agent": asesores,
        "top_criteria": [
            {"criterion": c, "count": n} for c, n in criterios.most_common(5)
        ],
    }


def critical_alerts(report: dict) -> list[dict]:
    """
    Alertas de patrón a partir del informe: asesores que suspenden de forma
    repetida y tasas de suspendidas que suben, del equipo o de una persona.
    """
    alertas: list[dict] = []

    antes, despues = report["first_half_pct"], report["second_half_pct"]
    if antes is not None and despues - antes >= SUBIDA_RELEVANTE:
        alertas.append(
            {
                "type": "critical_trend",
                "severity": "high",
                "title": "Suben las llamadas suspendidas",
                "description": (
                    f"Del {antes:.0f} % al {despues:.0f} % entre la primera y la "
                    "segunda mitad del periodo, en todo el equipo."
                ),
                "value": round(despues - antes, 1),
            }
        )

    for a in report["by_agent"]:
        criterio = (
            f" Lo que más incumple: {a['top_criterion']}." if a["top_criterion"] else ""
        )
        if a["critical_calls"] >= MIN_SUSPENSIONES_ASESOR:
            alertas.append(
                {
                    "type": "critical_agent",
                    "severity": "high" if a["critical_pct"] >= 25 else "medium",
                    "title": f"{a['agent_name']}: {a['critical_calls']} llamadas suspendidas",
                    "description": (
                        f"{a['critical_calls']} de {a['total_calls']} en el periodo "
                        f"({a['critical_pct']:.0f} %).{criterio}"
                    ),
                    "agent_id": a["agent_id"],
                    "agent_name": a["agent_name"],
                    "value": a["critical_pct"],
                }
            )
        a_antes, a_despues = a["first_half_pct"], a["second_half_pct"]
        if a_antes is not None and a_despues - a_antes >= SUBIDA_RELEVANTE:
            alertas.append(
                {
                    "type": "critical_trend",
                    # Alta, como la del equipo: una tasa de incumplimientos
                    # normativos que sube es riesgo para el banco, no un matiz.
                    "severity": "high",
                    "title": f"{a['agent_name']}: suben sus suspendidas",
                    "description": (
                        f"Del {a_antes:.0f} % al {a_despues:.0f} % entre la primera "
                        f"y la segunda mitad del periodo.{criterio}"
                    ),
                    "agent_id": a["agent_id"],
                    "agent_name": a["agent_name"],
                    "value": round(a_despues - a_antes, 1),
                }
            )
    return alertas
