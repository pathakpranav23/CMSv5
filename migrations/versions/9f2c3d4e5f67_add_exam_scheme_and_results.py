"""add exam scheme and result tables

Revision ID: 9f2c3d4e5f67
Revises: 7b1a2b9c1234
Create Date: 2026-01-17 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f2c3d4e5f67'
down_revision = '7b1a2b9c1234'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'exam_schemes',
        sa.Column('scheme_id', sa.Integer(), primary_key=True),
        sa.Column('program_id_fk', sa.Integer(), nullable=False),
        sa.Column('semester', sa.Integer(), nullable=False),
        sa.Column('academic_year', sa.String(length=16), nullable=False),
        sa.Column('medium_tag', sa.String(length=32), nullable=True),
        sa.Column('name', sa.String(length=128), nullable=True),
        sa.Column('max_internal_marks', sa.Float(), nullable=True),
        sa.Column('max_external_marks', sa.Float(), nullable=True),
        sa.Column('min_internal_marks', sa.Float(), nullable=True),
        sa.Column('min_external_marks', sa.Float(), nullable=True),
        sa.Column('min_total_marks', sa.Float(), nullable=True),
        sa.Column('max_total_marks', sa.Float(), nullable=True),
        sa.Column('grading_scheme_json', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['program_id_fk'], ['programs.program_id']),
        sa.UniqueConstraint(
            'program_id_fk',
            'semester',
            'medium_tag',
            'academic_year',
            name='uq_exam_scheme_scope',
        ),
    )

    op.create_table(
        'student_semester_results',
        sa.Column('result_id', sa.Integer(), primary_key=True),
        sa.Column('student_id_fk', sa.String(length=32), nullable=False),
        sa.Column('program_id_fk', sa.Integer(), nullable=False),
        sa.Column('scheme_id_fk', sa.Integer(), nullable=True),
        sa.Column('semester', sa.Integer(), nullable=False),
        sa.Column('academic_year', sa.String(length=16), nullable=False),
        sa.Column('attempt_no', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('total_credits_registered', sa.Integer(), nullable=True),
        sa.Column('total_credits_earned', sa.Integer(), nullable=True),
        sa.Column('sgpa', sa.Float(), nullable=True),
        sa.Column('cgpa', sa.Float(), nullable=True),
        sa.Column('result_status', sa.String(length=16), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['student_id_fk'], ['students.enrollment_no']),
        sa.ForeignKeyConstraint(['program_id_fk'], ['programs.program_id']),
        sa.ForeignKeyConstraint(['scheme_id_fk'], ['exam_schemes.scheme_id']),
        sa.UniqueConstraint(
            'student_id_fk',
            'semester',
            'academic_year',
            'attempt_no',
            name='uq_student_semester_attempt',
        ),
    )

    op.create_table(
        'exam_marks',
        sa.Column('exam_mark_id', sa.Integer(), primary_key=True),
        sa.Column('student_id_fk', sa.String(length=32), nullable=False),
        sa.Column('subject_id_fk', sa.Integer(), nullable=False),
        sa.Column('division_id_fk', sa.Integer(), nullable=True),
        sa.Column('scheme_id_fk', sa.Integer(), nullable=True),
        sa.Column('semester', sa.Integer(), nullable=True),
        sa.Column('academic_year', sa.String(length=16), nullable=True),
        sa.Column('attempt_no', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('internal_marks', sa.Float(), nullable=True),
        sa.Column('external_marks', sa.Float(), nullable=True),
        sa.Column('total_marks', sa.Float(), nullable=True),
        sa.Column('grade_point', sa.Float(), nullable=True),
        sa.Column('grade_letter', sa.String(length=4), nullable=True),
        sa.Column('is_absent', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['student_id_fk'], ['students.enrollment_no']),
        sa.ForeignKeyConstraint(['subject_id_fk'], ['subjects.subject_id']),
        sa.ForeignKeyConstraint(['division_id_fk'], ['divisions.division_id']),
        sa.ForeignKeyConstraint(['scheme_id_fk'], ['exam_schemes.scheme_id']),
        sa.UniqueConstraint(
            'student_id_fk',
            'subject_id_fk',
            'semester',
            'academic_year',
            'attempt_no',
            name='uq_exam_mark_attempt',
        ),
    )


def downgrade():
    op.drop_table('exam_marks')
    op.drop_table('student_semester_results')
    op.drop_table('exam_schemes')

