"""Usuarios activables

Añade `users.active`. Un cliente necesita poder dar de baja a alguien que se va
sin borrar su historial: las llamadas, revisiones y respuestas del asesor siguen
teniendo sentido, pero la cuenta deja de entrar.

Revision ID: 0012
Revises: 0011
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "active")
