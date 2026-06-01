from app.services.scoring.base_scorer import BaseScorer


class BudgetScorer(BaseScorer):
    def score(self, user, candidate, context=None):
        monthly_rent = getattr(candidate, "month_rent", None) or getattr(candidate, "monthly_rent", None)
        if monthly_rent is None:
            return 0.5

        max_budget = getattr(user, "max_budget", None) or getattr(context, "max_budget", None)
        min_budget = getattr(user, "min_budget", None) or getattr(context, "min_budget", None)

        if max_budget is None:
            return 0.5

        if min_budget is not None and min_budget <= monthly_rent <= max_budget:
            return 1.0
        if monthly_rent <= max_budget:
            return 0.9 if min_budget is None else 1.0
        if monthly_rent <= max_budget * 1.2:
            return 0.7

        if max_budget > 0:
            return max(0.0, 1.0 - (monthly_rent - max_budget) / max_budget)
        return 0.0