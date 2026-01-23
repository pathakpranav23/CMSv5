"""add semester_coordinators table

Revision ID: 7b1a2b9c1234
Revises: 390fa8289215
Create Date: 2026-01-17 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b1a2b9c1234'
down_revision = '390fa8289215'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'semester_coordinators',
        sa.Column('coordinator_id', sa.Integer(), primary_key=True),
        sa.Column('program_id_fk', sa.Integer(), nullable=False),
        sa.Column('semester', sa.Integer(), nullable=False),
        sa.Column('medium_tag', sa.String(length=32), nullable=True),
        sa.Column('academic_year', sa.String(length=16), nullable=False),
        sa.Column('faculty_user_id_fk', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['program_id_fk'], ['programs.program_id']),
        sa.ForeignKeyConstraint(['faculty_user_id_fk'], ['users.user_id']),
        sa.UniqueConstraint(
            'program_id_fk',
            'semester',
            'medium_tag',
            'academic_year',
            'faculty_user_id_fk',
            name='uq_semester_coordinator_scope_faculty',
        ),
    )


def downgrade():
    op.drop_table('semester_coordinators')

