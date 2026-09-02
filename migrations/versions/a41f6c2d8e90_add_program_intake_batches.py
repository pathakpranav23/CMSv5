"""add program intake batches and nullable student admission mapping

Revision ID: a41f6c2d8e90
Revises: 9f2c3d4e5f67
Create Date: 2026-08-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "a41f6c2d8e90"
down_revision = "9f2c3d4e5f67"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "program_intake_batches",
        sa.Column("intake_batch_id", sa.Integer(), primary_key=True),
        sa.Column("program_id_fk", sa.Integer(), nullable=False),
        sa.Column("admission_academic_year", sa.String(length=16), nullable=False),
        sa.Column("approved_intake", sa.Integer(), nullable=False),
        sa.Column("default_division_capacity", sa.Integer(), nullable=False),
        sa.Column("medium_tag", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("approved_by_user_id_fk", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["program_id_fk"], ["programs.program_id"]),
        sa.ForeignKeyConstraint(["approved_by_user_id_fk"], ["users.user_id"]),
        sa.UniqueConstraint("program_id_fk", "admission_academic_year", "medium_tag", name="uq_program_intake_batch_scope"),
    )
    with op.batch_alter_table("students") as batch_op:
        batch_op.add_column(sa.Column("admission_academic_year", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("intake_batch_id_fk", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_students_intake_batch", "program_intake_batches", ["intake_batch_id_fk"], ["intake_batch_id"])


def downgrade():
    with op.batch_alter_table("students") as batch_op:
        batch_op.drop_constraint("fk_students_intake_batch", type_="foreignkey")
        batch_op.drop_column("intake_batch_id_fk")
        batch_op.drop_column("admission_academic_year")
    op.drop_table("program_intake_batches")
