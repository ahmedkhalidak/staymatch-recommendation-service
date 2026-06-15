"""add created_at and updated_at to user_questionnaire_answers"""
from alembic import op
import sqlalchemy as sa


revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user_questionnaire_answers",
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("current_timestamp"), nullable=True)
    )
    op.add_column(
        "user_questionnaire_answers",
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("current_timestamp"), nullable=True)
    )
    
    # Set created_at to answered_at for existing records
    op.execute("""
        UPDATE user_questionnaire_answers 
        SET created_at = answered_at, updated_at = answered_at 
        WHERE created_at IS NULL
    """)


def downgrade():
    op.drop_column("user_questionnaire_answers", "updated_at")
    op.drop_column("user_questionnaire_answers", "created_at")
