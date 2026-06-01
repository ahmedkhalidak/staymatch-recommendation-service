from app.services.scoring.base_scorer import BaseScorer


class TenantScorer(BaseScorer):
    MATCH = 1.0
    BLOCKED = 0.0
    FLEXIBLE = 0.8

    def score(self, user, candidate, context=None):
        allowed = context.get("allowed_tenants") if context else None
        user_gender = (getattr(user, "gender", "") or "").lower()
        user_occupation = (getattr(user, "occupation", "") or "").lower()

        if not allowed:
            return self.FLEXIBLE

        if user_gender == "male":
            gender_val = 0
        elif user_gender == "female":
            gender_val = 1
        else:
            gender_val = None

        # Strict checks: if property has gender restrictions, apply them
        if gender_val is not None:
            sg = getattr(allowed, "student_gender", None)
            wg = getattr(allowed, "worker_gender", None)

            if sg is not None and allowed.allows_students:
                if sg != gender_val:
                    return self.BLOCKED

            if wg is not None and allowed.allows_workers:
                if wg != gender_val:
                    return self.BLOCKED

        # Occupation matching
        is_student = user_occupation == "student"
        is_worker = user_occupation == "worker"

        # If property has specific occupation restrictions
        students_only = allowed.allows_students and not allowed.allows_workers and not allowed.allows_families
        workers_only = allowed.allows_workers and not allowed.allows_students and not allowed.allows_families

        if students_only and not is_student:
            return self.BLOCKED
        if workers_only and not is_worker:
            return self.BLOCKED

        # Positive matches
        if is_student and allowed.allows_students:
            return self.MATCH
        if is_worker and allowed.allows_workers:
            return self.MATCH
        if allowed.allows_families or allowed.allows_children:
            return self.MATCH

        # Flexible
        return self.FLEXIBLE
