"""add unsubscribe status fields

Revision ID: e4e5f6789def
Revises: d3e5f6789abc
Create Date: 2024-02-04 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e4e5f6789def'
down_revision = 'd3e5f6789abc'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('emails', sa.Column('unsubscribe_status', sa.String(), nullable=True))
    op.add_column('emails', sa.Column('unsubscribed_at', sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column('emails', 'unsubscribed_at')
    op.drop_column('emails', 'unsubscribe_status')