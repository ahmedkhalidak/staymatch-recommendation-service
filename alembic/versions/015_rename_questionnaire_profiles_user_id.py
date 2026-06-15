"""rename questionnaire_profiles.user_id to user_profile_id for consistency"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade():
    # Rename user_id column to user_profile_id in questionnaire_profiles
    op.alter_column(
        "questionnaire_profiles",
        "user_id",
        new_column_name="user_profile_id"
    )
    
    # Rename index for consistency
    op.drop_index("idx_questionnaire_profiles_user", "questionnaire_profiles")
    op.create_index("idx_questionnaire_profiles_user", "questionnaire_profiles", ["user_profile_id"])


def downgrade():
    # Revert column name back to user_id
    op.alter_column(
        "questionnaire_profiles",
        "user_profile_id",
        new_column_name="user_id"
    )
    
    # Revert index name
    op.drop_index("idx_questionnaire_profiles_user", "questionnaire_profiles")
    op.create_index("idx_questionnaire_profiles_user", "questionnaire_profiles", ["user_id"])
