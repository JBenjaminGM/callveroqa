"""Retencion de audios

Anade `calls.audio_deleted_at`: cuando la politica de retencion borra la
grabacion, la llamada se queda con su transcripcion y su nota —que es lo que
tiene valor— y marca cuando dejo de existir el audio, para poder explicarlo en
la ficha en vez de dar un error raro al darle a reproducir.

Revision ID: 0013
Revises: 0012
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("calls", sa.Column("audio_deleted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("calls", "audio_deleted_at")
