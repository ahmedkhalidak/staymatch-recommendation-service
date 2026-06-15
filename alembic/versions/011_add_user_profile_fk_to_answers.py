"""add user_profile_id foreign key to user_questionnaire_answers"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user_questionnaire_answers",
        sa.Column("user_profile_id", UUID(as_uuid=True), sa.ForeignKey("user_profiles.id"), nullable=True)
    )
    op.create_index("idx_answers_user_profile", "user_questionnaire_answers", ["user_profile_id"])


def downgrade():
    op.drop_index("idx_answers_user_profile", "user_questionnaire_answers")
    op.drop_column("user_questionnaire_answers", "user_profile_id")
