"""Require resolution notes for resolved complaints.

Revision ID: 8b8a1d6d8c32
Revises: 375b16cd6cc2
"""
from alembic import op


revision = "8b8a1d6d8c32"
down_revision = "375b16cd6cc2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_check_constraint(
        "ck_complaints_resolved_completion",
        "complaints",
        "status <> 'Resolved' OR (resolved_at IS NOT NULL AND resolution_notes IS NOT NULL)",
    )


def downgrade():
    op.drop_constraint(
        "ck_complaints_resolved_completion",
        "complaints",
        type_="check",
    )
