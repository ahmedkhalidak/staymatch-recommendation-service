"""truncate development data from user-related tables"""
from alembic import op
import sqlalchemy as sa


revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade():
    # Truncate in reverse dependency order to respect foreign keys
    op.execute("TRUNCATE TABLE user_questionnaire_answers RESTART IDENTITY CASCADE")
    op.execute("TRUNCATE TABLE questionnaire_profiles RESTART IDENTITY CASCADE")
    op.execute("TRUNCATE TABLE user_search_preferences RESTART IDENTITY CASCADE")
    op.execute("TRUNCATE TABLE user_profiles RESTART IDENTITY CASCADE")


def downgrade():
    # No rollback for data truncation
    pass
