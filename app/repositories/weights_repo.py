from app.database.session import get_session
from app.database.models.recommendation import ScoringWeight, UserFeedbackWeight


class WeightRepository:
    def __init__(self):
        self.session = get_session()

    def get_weights(self, group: str) -> dict:
        rows = self.session.query(ScoringWeight).filter(
            ScoringWeight.weight_group == group
        ).all()
        return {r.weight_key: r.weight_value for r in rows}

    def update_weight(self, key: str, group: str, value: float):
        existing = self.session.query(ScoringWeight).filter(
            ScoringWeight.weight_key == key,
            ScoringWeight.weight_group == group
        ).first()
        if existing:
            existing.weight_value = value
            self.session.commit()
        return existing

    def get_all_weights(self) -> list:
        return self.session.query(ScoringWeight).order_by(
            ScoringWeight.weight_group, ScoringWeight.weight_key
        ).all()


class FeedbackRepository:
    def __init__(self):
        self.session = get_session()

    def get_user_feedback(self, user_id: str):
        return self.session.query(UserFeedbackWeight).filter(
            UserFeedbackWeight.user_id == user_id
        ).first()

    def upsert_feedback(self, user_id: str, data: dict):
        existing = self.get_user_feedback(user_id)
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            entry = UserFeedbackWeight(user_id=user_id, **data)
            self.session.add(entry)
        self.session.commit()

    def delete_user_feedback(self, user_id: str):
        self.session.query(UserFeedbackWeight).filter(
            UserFeedbackWeight.user_id == user_id
        ).delete()
        self.session.commit()