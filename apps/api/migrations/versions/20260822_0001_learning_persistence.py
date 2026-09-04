"""Create course, learner profile, mastery and learning event tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260822_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "course_versions",
        sa.Column("course_id", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "course_id IN ('c', 'python', 'data_structures')",
            name=op.f("ck_course_versions_course_id_allowed"),
        ),
        sa.PrimaryKeyConstraint("course_id", "version", name=op.f("pk_course_versions")),
    )
    op.create_index(
        "uq_course_versions_one_active",
        "course_versions",
        ["course_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "learner_profiles",
        sa.Column("student_id", sa.String(length=128), nullable=False),
        sa.Column("course_id", sa.String(length=32), nullable=False),
        sa.Column("course_version", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "course_id IN ('c', 'python', 'data_structures')",
            name=op.f("ck_learner_profiles_course_id_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["course_id", "course_version"],
            ["course_versions.course_id", "course_versions.version"],
            name=op.f("fk_learner_profiles_course_id_course_versions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("student_id", "course_id", name=op.f("pk_learner_profiles")),
    )

    op.create_table(
        "mastery_states",
        sa.Column("student_id", sa.String(length=128), nullable=False),
        sa.Column("course_id", sa.String(length=32), nullable=False),
        sa.Column("knowledge_point_id", sa.String(length=80), nullable=False),
        sa.Column("score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("evidence_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "evidence_count >= 0",
            name=op.f("ck_mastery_states_evidence_count_nonnegative"),
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name=op.f("ck_mastery_states_revision_positive"),
        ),
        sa.CheckConstraint(
            "score >= 0 AND score <= 1",
            name=op.f("ck_mastery_states_score_range"),
        ),
        sa.ForeignKeyConstraint(
            ["student_id", "course_id"],
            ["learner_profiles.student_id", "learner_profiles.course_id"],
            name=op.f("fk_mastery_states_student_id_learner_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "student_id",
            "course_id",
            "knowledge_point_id",
            name=op.f("pk_mastery_states"),
        ),
    )
    op.create_index(
        "ix_mastery_states_course_knowledge",
        "mastery_states",
        ["course_id", "knowledge_point_id"],
    )

    op.create_table(
        "learning_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("student_id", sa.String(length=128), nullable=False),
        sa.Column("course_id", sa.String(length=32), nullable=False),
        sa.Column("course_version", sa.String(length=32), nullable=False),
        sa.Column("knowledge_point_id", sa.String(length=80), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("evidence_summary", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "course_id IN ('c', 'python', 'data_structures')",
            name=op.f("ck_learning_events_course_id_allowed"),
        ),
        sa.CheckConstraint(
            "event_type IN ('assessment.completed', 'practice.submitted', "
            "'code.verified', 'profile.updated', 'recommendation.generated')",
            name=op.f("ck_learning_events_event_type_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["course_id", "course_version"],
            ["course_versions.course_id", "course_versions.version"],
            name=op.f("fk_learning_events_course_id_course_versions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id", "course_id"],
            ["learner_profiles.student_id", "learner_profiles.course_id"],
            name=op.f("fk_learning_events_student_id_learner_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("event_id", name=op.f("pk_learning_events")),
    )
    op.create_index(
        "ix_learning_events_student_course_time",
        "learning_events",
        ["student_id", "course_id", "occurred_at"],
    )
    op.create_index("ix_learning_events_trace_id", "learning_events", ["trace_id"])


def downgrade() -> None:
    op.drop_index("ix_learning_events_trace_id", table_name="learning_events")
    op.drop_index("ix_learning_events_student_course_time", table_name="learning_events")
    op.drop_table("learning_events")
    op.drop_index("ix_mastery_states_course_knowledge", table_name="mastery_states")
    op.drop_table("mastery_states")
    op.drop_table("learner_profiles")
    op.drop_index("uq_course_versions_one_active", table_name="course_versions")
    op.drop_table("course_versions")
