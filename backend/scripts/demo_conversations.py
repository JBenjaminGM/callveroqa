"""
Guiones de las llamadas de demostración.

Seis conversaciones reales (dos por ejecutivo: una que cumple y otra que falla),
con sus segmentos y tiempos. Son la fuente de tres cosas a la vez, y por eso
viven en un solo sitio:

1. Los archivos de audio de `backend/demo_audio/` — generados a partir de estos
   textos, así que lo que se oye coincide con lo que se lee.
2. Las transcripciones que siembra `seed_demo.py`.
3. Las notas por dimensión, escritas a mano para que cuadren con lo que ocurre
   en cada llamada (si el ejecutivo omite la TEA, `compliance` baja de verdad).

Nada de esto llama a la IA: el seed funciona sin clave y sin coste.
"""

# Cada segmento es (hablante, texto, segundos que dura).
# Los tiempos de inicio y fin se calculan al vuelo, con una pausa corta entre turnos.

CONVERSACIONES: dict[str, dict] = {
    # ------------------------------------------------------------------ #
    # TARJETAS PREMIUM — María González
    # ------------------------------------------------------------------ #
    "tarjetas_alta": {
        "audio": "tarjetas_alta.wav",
        "ejecutivo": "María González",
        "campana": "Tarjetas Premium",
        "resumen": (
            "Llamada modélica: se identifica, avisa de la grabación, informa la TEA sin "
            "que se la pidan y responde la objeción del cliente con datos concretos."
        ),
        "scores": {
            "greeting": 95, "assertiveness": 90, "promotions": 92, "compliance": 96,
            "resolution": 88, "objections": 90, "sentiment": 92,
        },
        "recomendaciones": [
            {
                "priority": "low", "dimension": "resolution",
                "title": "Confirmar el siguiente paso con fecha",
                "description": (
                    "Cerraste diciendo que enviarías la información, pero sin decir cuándo. "
                    "Un «se lo envío hoy antes de las seis» reduce las llamadas de seguimiento."
                ),
            },
        ],
        "segmentos": [
            ("agent", "Buenas tardes, le saluda María González del banco. ¿Hablo con el señor Ramírez?", 6.29),
            ("customer", "Sí, con él habla.", 1.83),
            ("agent", "Le informo que esta llamada está siendo grabada por motivos de calidad. ¿Tiene un par de minutos?", 6.82),
            ("customer", "Sí, dígame.", 1.66),
            ("agent", "Le llamo porque su perfil califica para nuestra tarjeta de crédito Premium. Sin cuota de mantenimiento el primer año y dos por ciento de devolución en todas sus compras.", 10.94),
            ("customer", "Suena bien, pero ¿cuánto me cobran de intereses?", 3.42),
            ("agent", "La tasa efectiva anual es desde treinta y nueve punto nueve por ciento, y depende de su evaluación crediticia. Si paga el total cada mes, no genera intereses.", 11.16),
            ("customer", "Ya. ¿Y a partir del segundo año qué pasa con la cuota?", 4.17),
            ("agent", "A partir del segundo año son veinticinco soles al mes, salvo que use la tarjeta por encima de mil soles mensuales, en cuyo caso se le exonera.", 9.69),
            ("customer", "Entiendo. Déjeme pensarlo.", 2.96),
            ("agent", "Por supuesto. Le envío el detalle de las condiciones por escrito para que lo revise con calma. La aprobación está sujeta a evaluación crediticia.", 10.36),
            ("customer", "Perfecto, envíemelo.", 2.23),
            ("agent", "Muy bien, señor Ramírez. Muchas gracias por su tiempo y que tenga buena tarde.", 6.36),
        ],
    },
    "tarjetas_baja": {
        "audio": "tarjetas_baja.wav",
        "ejecutivo": "María González",
        "campana": "Tarjetas Premium",
        "resumen": (
            "Llamada con incumplimientos: no avisa de la grabación, omite la TEA, promete "
            "aprobación inmediata y afirma que la tarjeta es gratis de por vida."
        ),
        "scores": {
            "greeting": 55, "assertiveness": 50, "promotions": 60, "compliance": 22,
            "resolution": 48, "objections": 35, "sentiment": 45,
        },
        "recomendaciones": [
            {
                "priority": "high", "dimension": "compliance",
                "title": "Informar la TEA y avisar de la grabación",
                "description": (
                    "Faltaron las dos obligaciones básicas: el aviso de grabación al inicio y la "
                    "tasa efectiva anual. Cubrir esto sube el score en más de veinte puntos."
                ),
            },
            {
                "priority": "high", "dimension": "compliance",
                "title": "No prometer lo que no se puede garantizar",
                "description": (
                    "Dijiste «gratis de por vida» y «aprobación inmediata». Ambas son afirmaciones "
                    "prohibidas en la nota de producto y exponen al banco a un reclamo."
                ),
            },
            {
                "priority": "medium", "dimension": "objections",
                "title": "Escuchar la objeción antes de responder",
                "description": (
                    "El cliente preguntó por el costo y la respuesta llegó antes de que terminara "
                    "la frase. Deja un segundo de silencio: la objeción real suele venir al final."
                ),
            },
        ],
        "segmentos": [
            ("agent", "Buenas, le llamo del banco. Tengo una promoción para usted.", 5.25),
            ("customer", "¿Perdone, quién habla?", 1.97),
            ("agent", "Del banco, señor. Mire, le tenemos aprobada una tarjeta Premium totalmente gratis de por vida.", 7.74),
            ("customer", "¿Gratis? ¿Y eso qué costo tiene?", 3.17),
            ("agent", "Ninguno, es gratis. Y la aprobación es inmediata, hoy mismo la tiene.", 6.18),
            ("customer", "Pero algún interés tendrá si no pago todo.", 2.78),
            ("agent", "Eso lo vemos después, no se preocupe. Lo importante es que aproveche ahora que está la promoción.", 7.24),
            ("customer", "Es que no me queda claro cuánto termino pagando.", 3.04),
            ("agent", "Le repito que es gratis. ¿Me confirma su dirección para el envío?", 5.21),
            ("customer", "No, mire, prefiero pensarlo.", 2.79),
            ("agent", "Bueno, cualquier cosa nos llama. Hasta luego.", 4.46),
        ],
    },

    # ------------------------------------------------------------------ #
    # PRÉSTAMOS — Carlos Ruiz
    # ------------------------------------------------------------------ #
    "prestamos_alta": {
        "audio": "prestamos_alta.wav",
        "ejecutivo": "Carlos Ruiz",
        "campana": "Préstamos",
        "resumen": (
            "Buena llamada: cumple el protocolo, da cifras concretas y confirma que el "
            "cliente entendió el total a pagar antes de cerrar."
        ),
        "scores": {
            "greeting": 88, "assertiveness": 85, "promotions": 84, "compliance": 90,
            "resolution": 86, "objections": 80, "sentiment": 84,
        },
        "recomendaciones": [
            {
                "priority": "medium", "dimension": "objections",
                "title": "Anticipar la comparación con otro banco",
                "description": (
                    "El cliente mencionó una oferta de la competencia y la conversación se desvió. "
                    "Ten a mano dos diferencias concretas para reconducirla en una frase."
                ),
            },
        ],
        "segmentos": [
            ("agent", "Buenos días, le habla Carlos Ruiz del banco. Esta llamada es grabada por calidad del servicio.", 6.95),
            ("customer", "Buenos días.", 1.45),
            ("agent", "Le contacto por el préstamo personal que consultó en nuestra web. ¿Sigue interesado?", 6.31),
            ("customer", "Sí, quería saber las condiciones.", 2.77),
            ("agent", "Claro. Para el monto que solicitó, quince mil soles a veinticuatro meses, la tasa efectiva anual es de veintinueve punto nueve por ciento.", 9.79),
            ("customer", "¿Y cuánto sería la cuota mensual?", 2.38),
            ("agent", "La cuota sería de ochocientos veinte soles, y el total a pagar diecinueve mil seiscientos ochenta soles. Sin penalidad si adelanta pagos.", 9.88),
            ("customer", "En otro banco me ofrecieron algo parecido.", 2.82),
            ("agent", "Es posible. Nuestra diferencia está en el desembolso en veinticuatro horas y en que no cobramos por el pago anticipado, que suele ser donde aparece el costo escondido.", 10.73),
            ("customer", "Eso sí me interesa.", 1.80),
            ("agent", "¿Le confirmo entonces que el total a pagar son diecinueve mil seiscientos ochenta soles en veinticuatro cuotas?", 6.98),
            ("customer", "Correcto, sí.", 1.76),
            ("agent", "Perfecto. Le envío la solicitud al correo y queda sujeto a evaluación crediticia. Gracias por su tiempo.", 8.38),
        ],
    },
    "prestamos_baja": {
        "audio": "prestamos_baja.wav",
        "ejecutivo": "Carlos Ruiz",
        "campana": "Préstamos",
        "resumen": (
            "Monólogo de casi un minuto sin dejar hablar al cliente. Menciona la TEA pero "
            "nunca confirma que el cliente entendió el total a pagar."
        ),
        "scores": {
            "greeting": 70, "assertiveness": 42, "promotions": 66, "compliance": 62,
            "resolution": 50, "objections": 40, "sentiment": 48,
        },
        "recomendaciones": [
            {
                "priority": "high", "dimension": "assertiveness",
                "title": "Dejar hablar al cliente",
                "description": (
                    "Hablaste cincuenta y dos segundos seguidos sin pausa. El cliente intentó "
                    "interrumpir dos veces. Corta cada treinta segundos con una pregunta."
                ),
            },
            {
                "priority": "medium", "dimension": "resolution",
                "title": "Confirmar el monto total antes de cerrar",
                "description": (
                    "Se dio la cuota mensual pero nunca el total a pagar, y no se comprobó que "
                    "el cliente lo entendiera. Es la causa número uno de reclamos posteriores."
                ),
            },
        ],
        "segmentos": [
            ("agent", "Buenas tardes le saluda Carlos Ruiz del banco esta llamada es grabada.", 4.55),
            ("customer", "Buenas.", 1.23),
            ("agent", "Mire señor le comento que tenemos una campaña de préstamos personales con desembolso en veinticuatro horas y cuotas fijas mensuales, la tasa efectiva anual arranca en veintinueve punto nueve por ciento según su perfil crediticio, puede pedir desde tres mil hasta cincuenta mil soles con plazos que van de seis a cuarenta y ocho meses, no cobramos penalidad por pago anticipado y el trámite es totalmente digital sin necesidad de que se acerque a una agencia, además si ya tiene productos con nosotros el proceso es más rápido porque no le pedimos documentación adicional.", 34.47),
            ("customer", "Perdón, una consulta...", 2.19),
            ("agent", "Y le comento también que este mes tenemos una promoción especial en la que los primeros tres meses puede diferir el pago, esto aplica solo para clientes seleccionados como usted, la cuota se recalcula al final del periodo y se le informa por correo con el cronograma completo.", 16.06),
            ("customer", "Sí pero yo quería saber cuánto...", 2.36),
            ("agent", "Le explico, la cuota para quince mil soles sería de ochocientos veinte soles mensuales aproximadamente.", 7.09),
            ("customer", "¿Y en total cuánto termino pagando?", 2.50),
            ("agent", "Eso se lo detallo en el correo que le envío. ¿Le parece si le mando la solicitud?", 5.94),
            ("customer", "Bueno, mándemelo y lo reviso.", 2.62),
            ("agent", "Listo, que tenga buena tarde.", 2.80),
        ],
    },

    # ------------------------------------------------------------------ #
    # SEGUROS — Lucía Fernández
    # ------------------------------------------------------------------ #
    "seguros_alta": {
        "audio": "seguros_alta.wav",
        "ejecutivo": "Lucía Fernández",
        "campana": "Seguros",
        "resumen": (
            "Explica las exclusiones y el periodo de carencia sin que se los pidan, que es "
            "justo lo que más reclamos evita en seguros."
        ),
        "scores": {
            "greeting": 90, "assertiveness": 88, "promotions": 82, "compliance": 94,
            "resolution": 84, "objections": 82, "sentiment": 88,
        },
        "recomendaciones": [
            {
                "priority": "low", "dimension": "promotions",
                "title": "Aterrizar el beneficio con un ejemplo",
                "description": (
                    "Las coberturas se explicaron bien pero en abstracto. Un caso concreto "
                    "—«si se queda sin trabajo, le cubrimos seis cuotas»— se recuerda mejor."
                ),
            },
        ],
        "segmentos": [
            ("agent", "Buenas tardes, le saluda Lucía Fernández del banco. La llamada es grabada por calidad.", 6.72),
            ("customer", "Buenas tardes.", 1.57),
            ("agent", "Le llamo porque como titular de nuestra tarjeta puede acceder al seguro de protección financiera. ¿Le explico en qué consiste?", 8.42),
            ("customer", "A ver, dígame.", 1.77),
            ("agent", "Cubre sus cuotas si se queda sin empleo o sufre una incapacidad temporal. La prima es desde quince soles al mes según la cobertura que elija.", 9.36),
            ("customer", "¿Y cubre cualquier situación?", 2.16),
            ("agent", "No, y es importante que lo sepa antes. Quedan excluidas las enfermedades preexistentes y la renuncia voluntaria al trabajo. Además hay un periodo de carencia de sesenta días desde la contratación.", 13.45),
            ("customer", "Ah, o sea que no es inmediato.", 2.44),
            ("agent", "Exacto, no es inmediato. Durante esos primeros sesenta días la póliza está activa pero no cubre siniestros. Prefiero que lo sepa ahora y no cuando lo necesite.", 11.79),
            ("customer", "Se agradece la claridad. Déjeme ver el detalle.", 3.83),
            ("agent", "Con gusto. Le envío las condiciones completas con las exclusiones al correo. Muchas gracias por su tiempo.", 8.38),
        ],
    },
    "seguros_baja": {
        "audio": "seguros_baja.wav",
        "ejecutivo": "Lucía Fernández",
        "campana": "Seguros",
        "resumen": (
            "Omite las exclusiones y el periodo de carencia, y afirma que el seguro cubre "
            "cualquier situación. Es el incumplimiento más grave en esta campaña."
        ),
        "scores": {
            "greeting": 72, "assertiveness": 65, "promotions": 70, "compliance": 28,
            "resolution": 58, "objections": 45, "sentiment": 60,
        },
        "recomendaciones": [
            {
                "priority": "high", "dimension": "compliance",
                "title": "Explicar exclusiones y carencia siempre",
                "description": (
                    "No se mencionaron ni las exclusiones ni el periodo de carencia de sesenta "
                    "días, y son frases obligatorias de esta campaña. Vender un seguro sin decirlo "
                    "es la causa habitual de reclamos y de anulación de la póliza."
                ),
            },
            {
                "priority": "high", "dimension": "compliance",
                "title": "No afirmar que cubre todo",
                "description": (
                    "Dijiste «cubre cualquier imprevisto». Es una afirmación prohibida en la nota "
                    "de producto y contradice las exclusiones reales de la póliza."
                ),
            },
        ],
        "segmentos": [
            ("agent", "Hola buenas, le llamo del banco por su seguro.", 3.56),
            ("customer", "¿Mi seguro? No tengo ninguno.", 3.00),
            ("agent", "Por eso le llamo, para que lo tenga. Es un seguro de protección que cubre cualquier imprevisto que se le presente.", 7.73),
            ("customer", "¿Cualquiera?", 1.28),
            ("agent", "Cualquiera, sí. Se queda sin trabajo, se enferma, lo que sea, nosotros le cubrimos las cuotas.", 8.26),
            ("customer", "¿Y desde cuándo empieza a cubrir?", 2.26),
            ("agent", "Desde que lo contrata. Son quince soles al mes, casi no se nota.", 5.69),
            ("customer", "Mmm, no sé, lo tengo que pensar.", 3.47),
            ("agent", "Piénselo, pero la promoción es hasta fin de mes. ¿Le hago la contratación ahora y lo cancela si no le convence?", 8.00),
            ("customer", "No, prefiero leerlo primero.", 2.49),
            ("agent", "Como usted vea. Que esté bien.", 3.27),
        ],
    },
}

# Evidencia de cada nota, escrita a mano igual que las notas: una frase y los
# segmentos (índice desde 0) en que se apoya. Es lo que la IA devuelve en
# `dimension_evidence` y lo que la ficha de la llamada convierte en saltos al audio.
EVIDENCIA: dict[str, dict[str, tuple[str, list[int]]]] = {
    "tarjetas_alta": {
        "greeting": ("Se identifica con nombre y banco, y se despide por el nombre del cliente.", [0, 12]),
        "assertiveness": ("Responde cada pregunta con cifras, sin rodeos ni presión.", [6, 8]),
        "promotions": ("Presenta los dos beneficios clave de la tarjeta en una sola frase.", [4]),
        "compliance": ("Avisa de la grabación, informa la TEA y aclara que la aprobación depende de la evaluación.", [2, 6, 10]),
        "resolution": ("Ofrece enviar las condiciones por escrito, pero sin comprometer una fecha.", [10]),
        "objections": ("Ante la duda por la cuota, explica cuándo se exonera en vez de esquivarla.", [7, 8]),
        "sentiment": ("El cliente cierra receptivo y pide que le envíen la información.", [11]),
    },
    "tarjetas_baja": {
        "greeting": ("No se identifica ni avisa de la grabación; el cliente tiene que preguntar quién llama.", [0, 1]),
        "assertiveness": ("Repite «es gratis» en lugar de responder la duda del cliente.", [8]),
        "promotions": ("Presenta la tarjeta con condiciones falsas en vez de sus beneficios reales.", [2]),
        "compliance": ("Omite la TEA y hace dos afirmaciones prohibidas: gratis de por vida y aprobación inmediata.", [2, 4, 6]),
        "resolution": ("Pide la dirección sin haber aclarado cuánto va a pagar el cliente.", [7, 8]),
        "objections": ("Esquiva la pregunta por los intereses: «eso lo vemos después».", [5, 6]),
        "sentiment": ("El cliente termina desconfiado y rechaza la oferta.", [7, 9]),
    },
    "prestamos_alta": {
        "greeting": ("Se identifica y avisa de la grabación en la primera frase.", [0]),
        "assertiveness": ("Da cuota y total exactos sin que el cliente tenga que insistir.", [6]),
        "promotions": ("Aterriza monto, plazo y tasa del préstamo que el cliente consultó.", [4]),
        "compliance": ("Informa TEA, total a pagar y que queda sujeto a evaluación crediticia.", [4, 6, 12]),
        "resolution": ("Confirma que el cliente entendió el total antes de cerrar.", [10, 11]),
        "objections": ("Responde a la comparación con otro banco con dos diferencias concretas.", [7, 8]),
        "sentiment": ("El cliente pasa de la duda al interés.", [9, 11]),
    },
    "prestamos_baja": {
        "greeting": ("Se identifica y avisa de la grabación, pero de corrido y sin preguntar si es buen momento.", [0]),
        "assertiveness": ("Monólogo de más de treinta segundos; ignora dos intentos del cliente de preguntar.", [2, 3, 4]),
        "promotions": ("Enumera todas las condiciones de golpe, sin conectarlas con lo que busca el cliente.", [2]),
        "compliance": ("Menciona la TEA, pero nunca el total a pagar.", [2, 8]),
        "resolution": ("Deja para un correo la pregunta por el total a pagar.", [7, 8]),
        "objections": ("No deja que el cliente llegue a formular su duda.", [3, 5]),
        "sentiment": ("El cliente acepta el correo por cansancio, no por interés.", [9]),
    },
    "seguros_alta": {
        "greeting": ("Se identifica y avisa de la grabación.", [0]),
        "assertiveness": ("Explica la carencia con claridad y sin minimizarla.", [8]),
        "promotions": ("Presenta coberturas y prima, aunque en abstracto.", [4]),
        "compliance": ("Explica exclusiones y periodo de carencia antes de que el cliente los descubra.", [6, 8]),
        "resolution": ("Envía las condiciones completas por escrito.", [10]),
        "objections": ("Ante «¿cubre cualquier situación?», responde con las exclusiones reales.", [5, 6]),
        "sentiment": ("El cliente agradece la claridad.", [9]),
    },
    "seguros_baja": {
        "greeting": ("No se identifica por su nombre ni avisa de la grabación.", [0]),
        "assertiveness": ("Presiona con la fecha límite de la promoción.", [8]),
        "promotions": ("Presenta el seguro con una cobertura que no existe.", [2, 6]),
        "compliance": ("Afirma que cubre cualquier imprevisto y omite exclusiones y carencia.", [2, 4, 6]),
        "resolution": ("Propone contratar y cancelar después en vez de resolver las dudas.", [8]),
        "objections": ("Responde a «¿desde cuándo cubre?» con información falsa.", [5, 6]),
        "sentiment": ("El cliente desconfía y prefiere leerlo antes.", [7, 9]),
    },
}

# Criterios críticos (auto-fail) incumplidos. Solo dos de las tres llamadas
# flojas: la de préstamos es mala, pero informa la TEA y no afirma nada
# prohibido. La demo enseña así la diferencia entre «baja» y «suspendida».
CRITICOS: dict[str, list[dict]] = {
    "tarjetas_baja": [
        {
            "dimension": "compliance", "criterion": "Sin afirmaciones prohibidas", "segment": 2,
            "reason": "Afirma que la tarjeta es «totalmente gratis de por vida» y promete aprobación inmediata.",
        },
        {
            "dimension": "compliance", "criterion": "Disclaimers obligatorios", "segment": 6,
            "reason": "Nunca informa la TEA: ante la pregunta por los intereses responde «eso lo vemos después».",
        },
    ],
    "seguros_baja": [
        {
            "dimension": "compliance", "criterion": "Sin afirmaciones prohibidas", "segment": 2,
            "reason": "Afirma que el seguro cubre «cualquier imprevisto».",
        },
        {
            "dimension": "compliance", "criterion": "Disclaimers obligatorios", "segment": 6,
            "reason": "Dice que cubre «desde que lo contrata»: omite la carencia de 60 días y las exclusiones.",
        },
    ],
}

# Criterios que la demo necesita marcados como críticos en la rúbrica.
CRITERIOS_CRITICOS_DEMO = {
    "compliance": ["Disclaimers obligatorios", "Sin afirmaciones prohibidas"],
}


def evidencia(clave: str) -> dict[str, dict]:
    """Evidencia en el formato que guarda `Analysis.dimension_evidence`."""
    return {
        dim: {"justification": texto, "segments": segs}
        for dim, (texto, segs) in EVIDENCIA.get(clave, {}).items()
    }


# Pausa entre turnos, en segundos. Sirve para que las métricas de conversación
# (porcentaje de silencio, turnos por minuto) den valores realistas.
PAUSA_ENTRE_TURNOS = 0.6


def construir_segmentos(clave: str) -> list[dict]:
    """Convierte los turnos de una conversación en segmentos con tiempos."""
    segmentos: list[dict] = []
    t = 0.0
    for hablante, texto, duracion in CONVERSACIONES[clave]["segmentos"]:
        segmentos.append(
            {
                "start": round(t, 2),
                "end": round(t + duracion, 2),
                "speaker": hablante,
                "text": texto,
            }
        )
        t += duracion + PAUSA_ENTRE_TURNOS
    return segmentos


def duracion_total(clave: str) -> int:
    """Duración de la llamada en segundos, redondeada."""
    segmentos = construir_segmentos(clave)
    return int(segmentos[-1]["end"]) if segmentos else 0


def texto_completo(clave: str) -> str:
    """Transcripción en texto plano, como la devolvería el proveedor de audio."""
    return " ".join(t for _, t, _ in CONVERSACIONES[clave]["segmentos"])
