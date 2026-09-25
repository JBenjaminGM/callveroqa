"""Sesiones de coaching

Anade `coaching_sessions`: una sesion con un asesor sobre una dimension de la
rubrica, con su fecha. Es lo que permite medir si el coaching movio la nota:
la misma dimension antes y despues de esa fecha.

La medicion no se guarda; se calcula al leer, para que siga siendo cierta
cuando entran llamadas nuevas.

Revision ID: 0015
Revises: 0014
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coaching_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "agent_id",
            sa.Integer(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dimension_key", sa.String(length=50), nullable=False),
        sa.Column("held_on", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "call_id",
            sa.Integer(),
            sa.ForeignKey("calls.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "coach_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_coaching_sessions_agent_id", "coaching_sessions", ["agent_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_coaching_sessions_agent_id", table_name="coaching_sessions")
    op.drop_table("coaching_sessions")
