from app.services.scoring.base_scorer import BaseScorer


class TenantScorer(BaseScorer):
    def score(self, user, candidate, context=None):
        allowed = context.get("allowed_tenants") if context else None
        if not allowed:
            return 0.8

        user_gender = getattr(user, "gender", "").lower()
        user_occupation = getattr(user, "occupation", "").lower()

        student_gender_mismatch = False
        worker_gender_mismatch = False

        if user_gender in ("male", "female"):
            gender_val = 0 if user_gender == "male" else 1

            if allowed.student_gender is not None and allowed.student_gender != gender_val:
                if allowed.allows_students:
                    student_gender_mismatch = True

            if allowed.worker_gender is not None and allowed.worker_gender != gender_val:
                if allowed.allows_workers:
                    worker_gender_mismatch = True

        if student_gender_mismatch or worker_gender_mismatch:
            return 0.0

        if user_occupation in ("student",) and allowed.allows_students:
            return 1.0
        if user_occupation in ("worker",) and allowed.allows_workers:
            return 1.0

        if not allowed.allows_students and not allowed.allows_workers:
            if not allowed.allows_families and not allowed.allows_children:
                return 0.0

        if allowed.allows_families or allowed.allows_children:
            return 1.0

        if allowed.allows_students or allowed.allows_workers:
            if user_occupation not in ("student", "worker"):
                return 0.5

        return 0.8