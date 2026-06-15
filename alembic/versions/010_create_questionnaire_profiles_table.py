"""create questionnaire_profiles table with FK to user_profiles"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "questionnaire_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("user_profiles.id"), nullable=False),
        sa.Column("completion_percentage", sa.Integer(), server_default=sa.text("0")),
        sa.Column("last_answered_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("idx_questionnaire_profiles_user", "questionnaire_profiles", ["user_id"])


def downgrade():
    op.drop_index("idx_questionnaire_profiles_user", "questionnaire_profiles")
    op.drop_table("questionnaire_profiles")
