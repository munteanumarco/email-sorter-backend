"""add unsubscribe tracking

Revision ID: d3e5f6789abc
Revises: cfaff238537d
Create Date: 2025-08-03 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd3e5f6789abc'
down_revision = 'cfaff238537d'
branch_labels = None
depends_on = None

def upgrade():
    # Add unsubscribe tracking columns
    op.add_column('emails', sa.Column('unsubscribed_at', sa.DateTime(), nullable=True))
    op.add_column('emails', sa.Column('unsubscribe_status', sa.String(), nullable=True))

def downgrade():
    # Remove unsubscribe tracking columns
    op.drop_column('emails', 'unsubscribed_at')
    op.drop_column('emails', 'unsubscribe_status')