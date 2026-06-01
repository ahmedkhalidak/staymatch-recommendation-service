from app.services.scoring.base_scorer import BaseScorer


class BudgetScorer(BaseScorer):
    def score(self, user, candidate, context=None):
        monthly_rent = getattr(candidate, "month_rent", None) or getattr(candidate, "monthly_rent", None)
        if monthly_rent is None:
            return 0.5

        max_budget = None
        min_budget = None

        if hasattr(user, "max_budget") and getattr(user, "max_budget") is not None:
            max_budget = user.max_budget
            min_budget = getattr(user, "min_budget", None)
        elif context and isinstance(context, dict):
            max_budget = context.get("max_budget")
            min_budget = context.get("min_budget")

        if max_budget is None:
            return 0.5

        if min_budget is not None and monthly_rent < min_budget:
            return max(0.0, monthly_rent / min_budget)

        if min_budget is not None and monthly_rent <= max_budget:
            return 1.0
        if monthly_rent <= max_budget:
            return 0.9
        if monthly_rent <= max_budget * 1.2:
            return 0.7

        if max_budget > 0:
            return max(0.0, 1.0 - (monthly_rent - max_budget) / max_budget)
        return 0.0
