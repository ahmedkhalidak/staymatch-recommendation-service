"""create synced tables (properties, rooms, amenities, tenants)"""
from alembic import op
import sqlalchemy as sa


revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "synced_properties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.String(255)),
        sa.Column("name", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("street", sa.Text()),
        sa.Column("city", sa.Text()),
        sa.Column("government", sa.Text()),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("property_type", sa.Integer(), nullable=False),
        sa.Column("monthly_rent", sa.Float()),
        sa.Column("deposit", sa.Float()),
        sa.Column("size", sa.Float()),
        sa.Column("number_of_bedrooms", sa.Integer()),
        sa.Column("number_of_living_rooms", sa.Integer()),
        sa.Column("total_rooms", sa.Integer()),
        sa.Column("available_rooms", sa.Integer()),
        sa.Column("furnished", sa.Boolean()),
        sa.Column("minimum_stay", sa.Integer()),
        sa.Column("available_from", sa.DateTime()),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("last_modified", sa.DateTime()),
        sa.Column("synced_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_synced_properties_city", "synced_properties", ["city"])
    op.create_index("idx_synced_properties_government", "synced_properties", ["government"])
    op.create_index("idx_synced_properties_property_type", "synced_properties", ["property_type"])
    op.create_index("idx_synced_properties_monthly_rent", "synced_properties", ["monthly_rent"])
    op.create_index("idx_synced_properties_location", "synced_properties", ["latitude", "longitude"])
    op.create_index("idx_synced_properties_synced_at", "synced_properties", ["synced_at"])

    op.create_table(
        "synced_rooms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("synced_properties.id"), nullable=False),
        sa.Column("room_name", sa.Text()),
        sa.Column("month_rent", sa.Float()),
        sa.Column("deposit", sa.Float()),
        sa.Column("capacity", sa.Integer()),
        sa.Column("capacity_available", sa.Integer()),
        sa.Column("furnished", sa.Boolean()),
        sa.Column("ensuite_bathroom", sa.Boolean()),
        sa.Column("shared_bathroom", sa.Boolean()),
        sa.Column("balcony", sa.Boolean()),
        sa.Column("window", sa.Boolean()),
        sa.Column("pets_allowed", sa.Boolean()),
        sa.Column("minimum_stay", sa.Integer()),
        sa.Column("available_from", sa.DateTime()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("synced_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_synced_rooms_property", "synced_rooms", ["property_id"])
    op.create_index("idx_synced_rooms_month_rent", "synced_rooms", ["month_rent"])
    op.create_index("idx_synced_rooms_capacity_avail", "synced_rooms", ["capacity_available"])
    op.create_index("idx_synced_rooms_synced_at", "synced_rooms", ["synced_at"])

    op.create_table(
        "synced_amenities",
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("synced_properties.id"), nullable=False),
        sa.Column("wifi", sa.Boolean()),
        sa.Column("tv", sa.Boolean()),
        sa.Column("cooktop", sa.Boolean()),
        sa.Column("oven", sa.Boolean()),
        sa.Column("kettle", sa.Boolean()),
        sa.Column("dishwasher", sa.Boolean()),
        sa.Column("refrigerator", sa.Boolean()),
        sa.Column("microwave", sa.Boolean()),
        sa.Column("washer", sa.Boolean()),
        sa.Column("free_parking", sa.Boolean()),
        sa.Column("air_conditioning", sa.Boolean()),
        sa.Column("smoke_alarm", sa.Boolean()),
        sa.Column("fire_extinguisher", sa.Boolean()),
        sa.Column("synced_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("property_id"),
    )

    op.create_table(
        "synced_allowed_tenants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("synced_properties.id")),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("synced_rooms.id")),
        sa.Column("allows_families", sa.Boolean()),
        sa.Column("allows_children", sa.Boolean()),
        sa.Column("allows_students", sa.Boolean()),
        sa.Column("student_gender", sa.Integer()),
        sa.Column("allows_workers", sa.Boolean()),
        sa.Column("worker_gender", sa.Integer()),
        sa.Column("pets_allowed", sa.Boolean()),
        sa.Column("synced_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_synced_allowed_tenants_property", "synced_allowed_tenants", ["property_id"])
    op.create_index("idx_synced_allowed_tenants_room", "synced_allowed_tenants", ["room_id"])


def downgrade():
    op.drop_table("synced_allowed_tenants")
    op.drop_table("synced_amenities")
    op.drop_table("synced_rooms")
    op.drop_table("synced_properties")