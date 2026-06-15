"""add unique constraint on (user_profile_id, question_id) to user_questionnaire_answers"""
from alembic import op
import sqlalchemy as sa


revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade():
    # Add UNIQUE constraint to prevent duplicate answers for same user and question
    op.create_unique_constraint(
        "uq_user_questionnaire_answers_user_profile_question",
        "user_questionnaire_answers",
        ["user_profile_id", "question_id"]
    )


def downgrade():
    op.drop_constraint(
        "uq_user_questionnaire_answers_user_profile_question",
        "user_questionnaire_answers",
        type_="unique"
    )
