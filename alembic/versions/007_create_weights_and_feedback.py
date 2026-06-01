"""create scoring_weights + user_feedback_weights tables with composite unique constraint"""
from alembic import op
import sqlalchemy as sa


revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scoring_weights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("weight_key", sa.String(50), nullable=False),
        sa.Column("weight_value", sa.Float(), nullable=False),
        sa.Column("weight_group", sa.String(30), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("weight_key", "weight_group", name="uq_weight_key_group"),
    )
    op.create_index("idx_weights_group", "scoring_weights", ["weight_group"])

    op.create_table(
        "user_feedback_weights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("city", sa.Text()),
        sa.Column("government", sa.Text()),
        sa.Column("property_type", sa.Integer()),
        sa.Column("min_budget", sa.Float()),
        sa.Column("max_budget", sa.Float()),
        sa.Column("boost_factor", sa.Float(), server_default=sa.text("1.0")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_feedback_user", "user_feedback_weights", ["user_id"])

    op.execute("""
        INSERT INTO scoring_weights (weight_key, weight_value, weight_group, description) VALUES
        ('budget', 0.30, 'property', 'Weight for budget score in property recommendations'),
        ('location', 0.25, 'property', 'Weight for location score in property recommendations'),
        ('amenities', 0.15, 'property', 'Weight for amenities score in property recommendations'),
        ('tenant', 0.10, 'property', 'Weight for tenant compatibility score'),
        ('furnished', 0.05, 'property', 'Weight for furnished status score'),
        ('property_type', 0.10, 'property', 'Weight for property type preference score'),
        ('recency', 0.05, 'property', 'Weight for recency/newly added boost'),
        ('budget', 0.25, 'room', 'Weight for budget score in room recommendations'),
        ('location', 0.20, 'room', 'Weight for location score in room recommendations'),
        ('capacity', 0.15, 'room', 'Weight for capacity availability score'),
        ('amenities', 0.10, 'room', 'Weight for amenities score in room recommendations'),
        ('tenant', 0.10, 'room', 'Weight for tenant compatibility score'),
        ('furnished', 0.05, 'room', 'Weight for furnished status score'),
        ('room_type', 0.10, 'room', 'Weight for room type (ensuite/shared bathroom) score'),
        ('recency', 0.05, 'room', 'Weight for recency/newly added boost'),
        ('questionnaire', 0.50, 'matching', 'Weight for questionnaire similarity in roommate matching'),
        ('gender', 0.15, 'matching', 'Weight for gender compatibility in matching'),
        ('occupation', 0.10, 'matching', 'Weight for occupation similarity in matching'),
        ('age_group', 0.10, 'matching', 'Weight for age group similarity in matching'),
        ('lifestyle', 0.15, 'matching', 'Weight for lifestyle compatibility in matching')
    """)


def downgrade():
    op.drop_table("user_feedback_weights")
    op.drop_table("scoring_weights")