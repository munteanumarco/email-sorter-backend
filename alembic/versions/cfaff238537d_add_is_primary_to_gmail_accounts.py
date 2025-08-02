"""add_is_primary_to_gmail_accounts

Revision ID: cfaff238537d
Revises: c09f24aafd00
Create Date: 2025-08-02 15:27:34.381772

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cfaff238537d'
down_revision: Union[str, Sequence[str], None] = 'c09f24aafd00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_primary column
    op.add_column('gmail_accounts', sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'))
    
    # Set the first account for each user as primary
    op.execute("""
        WITH ranked_accounts AS (
            SELECT id, user_id, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at) as rn
            FROM gmail_accounts
        )
        UPDATE gmail_accounts
        SET is_primary = true
        FROM ranked_accounts
        WHERE gmail_accounts.id = ranked_accounts.id AND ranked_accounts.rn = 1;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('gmail_accounts', 'is_primary')
