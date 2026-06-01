"""create user tables (profiles, questionnaire, search preferences)"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_profiles",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("auth_user_id", UUID(as_uuid=True)),
        sa.Column("external_user_id", sa.String(255), unique=True),
        sa.Column("full_name", sa.Text()),
        sa.Column("phone", sa.String(50)),
        sa.Column("gender", sa.String(20)),
        sa.Column("birth_year", sa.Integer()),
        sa.Column("nationality", sa.String(100)),
        sa.Column("occupation", sa.String(100)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_user_profiles_auth", "user_profiles", ["auth_user_id"])
    op.create_index("idx_user_profiles_external", "user_profiles", ["external_user_id"])

    op.create_table(
        "questionnaire_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name_ar", sa.Text(), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "questionnaire_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("questionnaire_categories.id")),
        sa.Column("question_ar", sa.Text(), nullable=False),
        sa.Column("question_en", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(30), nullable=False),
        sa.Column("options_ar", JSONB()),
        sa.Column("options_en", JSONB()),
        sa.Column("weight", sa.Float(), server_default=sa.text("1.0")),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_questionnaire_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questionnaire_questions.id"), nullable=False),
        sa.Column("answer_value", sa.Text(), nullable=False),
        sa.Column("answer_scale", sa.Integer()),
        sa.Column("answered_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "question_id"),
    )
    op.create_index("idx_answers_user", "user_questionnaire_answers", ["user_id"])
    op.create_index("idx_answers_question", "user_questionnaire_answers", ["question_id"])

    op.create_table(
        "user_search_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False, unique=True),
        sa.Column("min_budget", sa.Integer()),
        sa.Column("max_budget", sa.Integer()),
        sa.Column("preferred_city", sa.Text()),
        sa.Column("preferred_government", sa.Text()),
        sa.Column("preferred_property_type", sa.String(20)),
        sa.Column("furnished", sa.Boolean()),
        sa.Column("wifi", sa.Boolean()),
        sa.Column("air_conditioning", sa.Boolean()),
        sa.Column("balcony", sa.Boolean()),
        sa.Column("private_bathroom", sa.Boolean()),
        sa.Column("tenant_type", sa.String(20)),
        sa.Column("gender_preference", sa.String(20)),
        sa.Column("shared_room", sa.Boolean()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("user_search_preferences")
    op.drop_table("user_questionnaire_answers")
    op.drop_table("questionnaire_questions")
    op.drop_table("questionnaire_categories")
    op.drop_table("user_profiles")