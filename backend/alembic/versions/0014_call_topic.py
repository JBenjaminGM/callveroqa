"""Motivo de la llamada

Anade `calls.topic`: por que llamo el cliente, detectado por la IA. Es lo que
permite pasar de "como lo hizo el asesor" a "que nos estan pidiendo": un jefe
puede entrenar a un asesor flojo, pero si el 30 % de las llamadas son por un
cobro mal explicado, eso se arregla en el producto, no con coaching.

Indexada porque el panel agrupa por ella en cada consulta del periodo.

Revision ID: 0014
Revises: 0013
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("calls", sa.Column("topic", sa.String(length=60), nullable=True))
    op.create_index("ix_calls_topic", "calls", ["topic"])


def downgrade() -> None:
    op.drop_index("ix_calls_topic", table_name="calls")
    op.drop_column("calls", "topic")
