"""Add immutable audit records for evidence-driven mastery updates."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260822_0002"
down_revision: str | None = "20260822_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mastery_update_audits",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", sa.String(length=128), nullable=False),
        sa.Column("course_id", sa.String(length=32), nullable=False),
        sa.Column("knowledge_point_id", sa.String(length=80), nullable=False),
        sa.Column("previous_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("new_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("previous_evidence_count", sa.Integer(), nullable=False),
        sa.Column("new_evidence_count", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("evidence_value", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("evidence_weight", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("reason_code", sa.String(length=48), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "new_score >= 0 AND new_score <= 1",
            name=op.f("ck_mastery_update_audits_new_score_range"),
        ),
        sa.CheckConstraint(
            "previous_score IS NULL OR (previous_score >= 0 AND previous_score <= 1)",
            name=op.f("ck_mastery_update_audits_previous_score_range"),
        ),
        sa.CheckConstraint(
            "evidence_value >= 0 AND evidence_value <= 1",
            name=op.f("ck_mastery_update_audits_evidence_value_range"),
        ),
        sa.CheckConstraint(
            "evidence_weight > 0 AND evidence_weight <= 1",
            name=op.f("ck_mastery_update_audits_evidence_weight_range"),
        ),
        sa.CheckConstraint(
            "previous_evidence_count >= 0 "
            "AND new_evidence_count = previous_evidence_count + 1",
            name=op.f("ck_mastery_update_audits_evidence_count_step"),
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_mastery_update_audits_revision_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["learning_events.event_id"],
            name=op.f("fk_mastery_update_audits_event_id_learning_events"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id", "course_id", "knowledge_point_id"],
            [
                "mastery_states.student_id",
                "mastery_states.course_id",
                "mastery_states.knowledge_point_id",
            ],
            name=op.f("fk_mastery_update_audits_student_id_mastery_states"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("event_id", name=op.f("pk_mastery_update_audits")),
    )
    op.create_index(
        "ix_mastery_audits_student_course_time",
        "mastery_update_audits",
        ["student_id", "course_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_mastery_audits_student_course_time",
        table_name="mastery_update_audits",
    )
    op.drop_table("mastery_update_audits")
