"""add clipboard_files table and file_count column

Revision ID: 3f8a9c7d5e2b
Revises: 7d2a4f3c5e6b
Create Date: 2026-05-04 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f8a9c7d5e2b'
down_revision: Union[str, Sequence[str], None] = '7d2a4f3c5e6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('clipboard_files',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('item_id', sa.String(length=8), nullable=False),
        sa.Column('filename', sa.String(length=512), nullable=False),
        sa.Column('original_path', sa.String(length=1024), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('stored_filename', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clipboard_files_id'), 'clipboard_files', ['id'], unique=False)
    op.create_index(op.f('ix_clipboard_files_item_id'), 'clipboard_files', ['item_id'], unique=False)
    
    op.add_column('clipboard_items', sa.Column('file_count', sa.Integer(), nullable=True, server_default='1'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('clipboard_items', 'file_count')
    
    op.drop_index(op.f('ix_clipboard_files_item_id'), table_name='clipboard_files')
    op.drop_index(op.f('ix_clipboard_files_id'), table_name='clipboard_files')
    op.drop_table('clipboard_files')
