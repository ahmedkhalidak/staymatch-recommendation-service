"""enhance user profile fields for .NET API sync"""
from alembic import op
import sqlalchemy as sa


revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to user_profiles
    op.add_column("user_profiles", sa.Column("first_name", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("last_name", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("birth_date", sa.DateTime(), nullable=True))
    op.add_column("user_profiles", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("user_profiles", sa.Column("governorate", sa.String(100), nullable=True))
    op.add_column("user_profiles", sa.Column("university", sa.String(100), nullable=True))
    op.add_column("user_profiles", sa.Column("field_of_study", sa.String(100), nullable=True))
    op.add_column("user_profiles", sa.Column("job_title", sa.String(100), nullable=True))
    op.add_column("user_profiles", sa.Column("about_me", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("status", sa.String(50), nullable=True))
    op.add_column("user_profiles", sa.Column("is_profile_complete", sa.Boolean(), nullable=True, server_default="false"))


def downgrade():
    # Drop new columns
    op.drop_column("user_profiles", "is_profile_complete")
    op.drop_column("user_profiles", "status")
    op.drop_column("user_profiles", "about_me")
    op.drop_column("user_profiles", "job_title")
    op.drop_column("user_profiles", "field_of_study")
    op.drop_column("user_profiles", "university")
    op.drop_column("user_profiles", "governorate")
    op.drop_column("user_profiles", "city")
    op.drop_column("user_profiles", "birth_date")
    op.drop_column("user_profiles", "last_name")
    op.drop_column("user_profiles", "first_name")
