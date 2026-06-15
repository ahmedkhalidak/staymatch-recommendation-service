"""add matching_key to questionnaire_questions for reliable question identification"""
from alembic import op
import sqlalchemy as sa


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("questionnaire_questions", sa.Column("matching_key", sa.String(50), nullable=True))
    op.create_index("idx_questionnaire_matching_key", "questionnaire_questions", ["matching_key"])


def downgrade():
    op.drop_index("idx_questionnaire_matching_key", table_name="questionnaire_questions")
    op.drop_column("questionnaire_questions", "matching_key")
