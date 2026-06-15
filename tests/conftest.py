"""
Test configuration: shared mocks, fixtures, and helpers.
All tests use mock objects — no real DB connections.
"""
import sys, os, pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

class MockProperty:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if not hasattr(self, "amenities"): self.amenities = None
        if not hasattr(self, "allowed_tenants"): self.allowed_tenants = None
        if not hasattr(self, "created_at"): self.created_at = datetime.now()

class MockRoom:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if not hasattr(self, "property"): self.property = None
        if not hasattr(self, "allowed_tenants"): self.allowed_tenants = []

class MockAllowedTenant:
    def __init__(self, **kwargs):
        for k, v in kwargs.items(): setattr(self, k, v)

class MockAmenity:
    def __init__(self, **kwargs):
        for k, v in kwargs.items(): setattr(self, k, v)

class MockUser:
    def __init__(self, **kwargs):
        for k, v in kwargs.items(): setattr(self, k, v)

class MockProfile:
    def __init__(self, **kwargs):
        for k, v in kwargs.items(): setattr(self, k, v)

class MockInteraction:
    def __init__(self, **kwargs):
        for k, v in kwargs.items(): setattr(self, k, v)

@pytest.fixture
def sample_properties():
    return [
        MockProperty(id=1, name="Property A", city="Cairo", government="Cairo",
                     latitude=30.0444, longitude=31.2357,
                     property_type=0, monthly_rent=5000, furnished=True,
                     created_at=datetime(2026, 5, 25)),
        MockProperty(id=2, name="Property B", city="Alexandria", government="Alexandria",
                     latitude=31.2001, longitude=29.9187,
                     property_type=1, monthly_rent=3000, furnished=False,
                     created_at=datetime(2026, 1, 1)),
        MockProperty(id=3, name="Property C", city="Giza", government="Giza",
                     latitude=30.0131, longitude=31.2089,
                     property_type=0, monthly_rent=8000, furnished=True,
                     created_at=datetime(2026, 5, 28)),
    ]

@pytest.fixture
def sample_rooms():
    return [
        MockRoom(id=1, property_id=1, month_rent=2500, capacity=2, capacity_available=1,
                 furnished=True, ensuite_bathroom=True),
        MockRoom(id=2, property_id=1, month_rent=2000, capacity=3, capacity_available=2,
                 furnished=False, shared_bathroom=True),
        MockRoom(id=3, property_id=2, month_rent=1500, capacity=4, capacity_available=3,
                 furnished=False, shared_bathroom=True, balcony=True),
    ]

@pytest.fixture
def sample_tenant_allowed():
    return MockAllowedTenant(allows_families=False, allows_children=False,
                             allows_students=True, student_gender=0,
                             allows_workers=False, worker_gender=None, pets_allowed=False)

@pytest.fixture
def sample_tenant_female():
    return MockAllowedTenant(allows_families=False, allows_children=False,
                             allows_students=True, student_gender=1,
                             allows_workers=True, worker_gender=1, pets_allowed=False)

@pytest.fixture
def sample_amenities():
    return MockAmenity(wifi=True, air_conditioning=True, balcony=False,
                       washer=True, refrigerator=True, tv=False)

@pytest.fixture
def male_user():
    return MockUser(gender="male", occupation="student", min_budget=3000, max_budget=6000)

@pytest.fixture
def female_user():
    return MockUser(gender="female", occupation="worker", min_budget=2000, max_budget=4000)
