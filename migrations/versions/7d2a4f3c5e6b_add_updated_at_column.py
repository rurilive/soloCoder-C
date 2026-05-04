"""add updated_at column

Revision ID: 7d2a4f3c5e6b
Revises: 09b2f193681f
Create Date: 2026-05-04 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d2a4f3c5e6b'
down_revision: Union[str, Sequence[str], None] = '09b2f193681f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('clipboard_items', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('clipboard_items', 'updated_at')
