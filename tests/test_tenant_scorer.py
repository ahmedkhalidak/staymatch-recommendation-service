"""Unit tests for TenantScorer — strict gender filtering + occupation."""
import pytest
from app.services.scoring.tenant_scorer import TenantScorer
from tests.conftest import MockUser, MockProperty, MockAllowedTenant, MockAmenity

scorer = TenantScorer()

class TestTenantScorer:
    def test_male_student_male_property(self):
        """Male student looking at male-only student property → 1.0"""
        user = MockUser(gender="male", occupation="student")
        tenant = MockAllowedTenant(allows_students=True, student_gender=0,
                                    allows_workers=False, worker_gender=None,
                                    allows_families=False, allows_children=False)
        context = {"allowed_tenants": tenant}
        assert scorer.score(user, None, context) == 1.0

    def test_male_student_female_property(self):
        """Male student looking at female-only property → BLOCKED (0.0)"""
        user = MockUser(gender="male", occupation="student")
        tenant = MockAllowedTenant(allows_students=True, student_gender=1)
        context = {"allowed_tenants": tenant}
        assert scorer.score(user, None, context) == 0.0

    def test_female_worker_female_property(self):
        """Female worker looking at female-only worker property → 1.0"""
        user = MockUser(gender="female", occupation="worker")
        tenant = MockAllowedTenant(allows_workers=True, worker_gender=1,
                                    allows_students=False, student_gender=None,
                                    allows_families=False, allows_children=False)
        context = {"allowed_tenants": tenant}
        assert scorer.score(user, None, context) == 1.0

    def test_female_worker_male_property(self):
        """Female worker looking at male-only → BLOCKED"""
        user = MockUser(gender="female", occupation="worker")
        tenant = MockAllowedTenant(allows_workers=True, worker_gender=0)
        context = {"allowed_tenants": tenant}
        assert scorer.score(user, None, context) == 0.0

    def test_no_gender_restriction(self):
        """No tenant restrictions → flexible 0.8"""
        user = MockUser(gender="male", occupation="student")
        tenant = MockAllowedTenant(allows_students=False, allows_workers=False,
                                    allows_families=False, allows_children=False,
                                    student_gender=None, worker_gender=None)
        context = {"allowed_tenants": tenant}
        assert scorer.score(user, None, context) == 0.8

    def test_allows_families(self):
        """Allows families → 1.0 regardless of gender"""
        user = MockUser(gender="male", occupation="student")
        tenant = MockAllowedTenant(allows_families=True, allows_children=True,
                                    allows_students=False, allows_workers=False)
        context = {"allowed_tenants": tenant}
        assert scorer.score(user, None, context) == 1.0

    def test_no_allowed_tenant(self):
        """No allowed_tenants at all → flexible"""
        user = MockUser(gender="male", occupation="student")
        context = {}
        assert scorer.score(user, None, context) == 0.8

    def test_student_worker_mismatch(self):
        """Worker looking at student-only with no worker allowed → BLOCKED"""
        user = MockUser(gender="male", occupation="worker")
        tenant = MockAllowedTenant(allows_students=True, student_gender=0,
                                    allows_workers=False,
                                    allows_families=False, allows_children=False,
                                    worker_gender=None)
        context = {"allowed_tenants": tenant}
        assert scorer.score(user, None, context) == 0.0
