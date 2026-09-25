"""Criterios que no aplican

Anade `rubric_config.allow_na` y `na_condition` (la dimension puede no aplicar a
una llamada, y cuando) y `analyses.not_applicable` (cuales no aplicaron). Una
dimension que no aplica no puntua y su peso se reparte entre las demas; antes
contaba como un cero y bajaba la nota por algo que el asesor no pudo hacer.

De paso marca como "puede no aplicar" las dos dimensiones de la rubrica por
defecto donde pasa siempre: objeciones (no todas las llamadas las tienen) y
promociones (no todas las llamadas son de venta). Solo se hace aqui, una vez:
si el jefe lo desactiva despues, ningun arranque se lo vuelve a activar.

Revision ID: 0016
Revises: 0015
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mismo texto que NA_POR_DEFECTO en scripts/seed_data.py.
POR_DEFECTO = {
    "objections": "Solo aplica si el cliente plantea alguna objeción, duda o reparo.",
    "promotions": (
        "Solo aplica si la llamada es de venta o el cliente pregunta por un "
        "producto; no en consultas, reclamos o gestiones."
    ),
}


def upgrade() -> None:
    op.add_column(
        "rubric_config",
        sa.Column(
            "allow_na", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
    )
    op.add_column("rubric_config", sa.Column("na_condition", sa.Text(), nullable=True))
    op.add_column(
        "analyses",
        sa.Column("not_applicable", postgresql.JSONB(), nullable=True),
    )

    rubric = sa.table(
        "rubric_config",
        sa.column("dimension_key", sa.String),
        sa.column("allow_na", sa.Boolean),
        sa.column("na_condition", sa.Text),
    )
    for key, condicion in POR_DEFECTO.items():
        op.execute(
            rubric.update()
            .where(rubric.c.dimension_key == key)
            .values(allow_na=True, na_condition=condicion)
        )


def downgrade() -> None:
    op.drop_column("analyses", "not_applicable")
    op.drop_column("rubric_config", "na_condition")
    op.drop_column("rubric_config", "allow_na")
