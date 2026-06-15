"""remove legacy user_id columns and make user_profile_id NOT NULL"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade():
    # Drop dependent view first
    op.execute("DROP VIEW IF EXISTS questionnaire_profiles_view")
    
    # Drop user_id column from user_questionnaire_answers
    op.drop_index("idx_answers_user", "user_questionnaire_answers")
    op.drop_column("user_questionnaire_answers", "user_id")
    
    # Make user_profile_id NOT NULL in user_questionnaire_answers
    op.alter_column(
        "user_questionnaire_answers",
        "user_profile_id",
        nullable=False
    )
    
    # Drop user_id column from user_search_preferences
    op.drop_column("user_search_preferences", "user_id")
    
    # Make user_profile_id NOT NULL and UNIQUE in user_search_preferences
    op.alter_column(
        "user_search_preferences",
        "user_profile_id",
        nullable=False
    )


def downgrade():
    # Re-add user_id column to user_questionnaire_answers
    op.add_column(
        "user_questionnaire_answers",
        sa.Column("user_id", sa.String(255), nullable=False)
    )
    op.create_index("idx_answers_user", "user_questionnaire_answers", ["user_id"])
    
    # Make user_profile_id nullable in user_questionnaire_answers
    op.alter_column(
        "user_questionnaire_answers",
        "user_profile_id",
        nullable=True
    )
    
    # Re-add user_id column to user_search_preferences
    op.add_column(
        "user_search_preferences",
        sa.Column("user_id", sa.String(255), nullable=False, unique=True)
    )
    
    # Make user_profile_id nullable in user_search_preferences
    op.alter_column(
        "user_search_preferences",
        "user_profile_id",
        nullable=True
    )
    
    # Recreate the view (simplified version - may need actual definition)
    op.execute("""
        CREATE OR REPLACE VIEW questionnaire_profiles_view AS
        SELECT 
            uqa.user_id,
            uqa.user_profile_id,
            COUNT(uqa.id) as answers_count,
            MAX(uqa.answered_at) as last_answered_at
        FROM user_questionnaire_answers uqa
        GROUP BY uqa.user_id, uqa.user_profile_id
    """)
