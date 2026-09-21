"""Evidencia por dimensión y criterios críticos

Añade a `analyses`:
- `dimension_evidence`: por qué la IA puso cada nota y en qué segmentos de la
  transcripción se apoya. Una nota sin evidencia no se puede discutir ni usar
  para coaching.
- `critical_failures`: criterios críticos (auto-fail) incumplidos. Si hay
  alguno, `global_score` pasa a 0.
- `uncapped_score`: la nota que habría tenido la llamada sin el auto-fail, para
  que el suspenso sea transparente.

Las tres son nulables: los análisis anteriores siguen siendo válidos.

Revision ID: 0011
Revises: 0010
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("dimension_evidence", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("critical_failures", postgresql.JSONB(), nullable=True),
    )
    op.add_column("analyses", sa.Column("uncapped_score", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "uncapped_score")
    op.drop_column("analyses", "critical_failures")
    op.drop_column("analyses", "dimension_evidence")
