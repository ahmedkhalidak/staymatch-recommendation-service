from app.database.session import get_session
from app.database.models.property import SyncedProperty, SyncedRoom, SyncedAmenity, SyncedAllowedTenant
from app.database.models.user import UserProfile, UserSearchPreference, QuestionnaireCategory, QuestionnaireQuestion, UserQuestionnaireAnswer
from app.database.models.recommendation import PropertyRecommendation, RoomRecommendation, RoommateMatch, UserInteraction


class PropertyRepository:
    def __init__(self):
        self.session = get_session()

    def get_all_approved(self):
        return self.session.query(SyncedProperty).filter(SyncedProperty.is_approved == True).all()

    def get_by_id(self, property_id: int):
        return self.session.query(SyncedProperty).filter(SyncedProperty.id == property_id).first()

    def get_by_city(self, city: str):
        return self.session.query(SyncedProperty).filter(
            SyncedProperty.is_approved == True,
            SyncedProperty.city.ilike(f"%{city}%")
        ).all()

    def get_with_relations(self, property_id: int):
        return self.session.query(SyncedProperty)\
            .outerjoin(SyncedAmenity)\
            .outerjoin(SyncedAllowedTenant)\
            .filter(SyncedProperty.id == property_id)\
            .first()


class RoomRepository:
    def __init__(self):
        self.session = get_session()

    def get_available(self):
        return self.session.query(SyncedRoom).filter(
            SyncedRoom.is_deleted == False,
            SyncedRoom.capacity_available > 0
        ).all()

    def get_by_property(self, property_id: int):
        return self.session.query(SyncedRoom).filter(
            SyncedRoom.property_id == property_id,
            SyncedRoom.is_deleted == False
        ).all()

    def get_by_id(self, room_id: int):
        return self.session.query(SyncedRoom).filter(SyncedRoom.id == room_id).first()


class UserRepository:
    def __init__(self):
        self.session = get_session()

    def upsert_profile(self, user_id: str, data: dict):
        existing = self.session.query(UserProfile).filter(
            UserProfile.external_user_id == user_id
        ).first()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            profile = UserProfile(external_user_id=user_id, **data)
            self.session.add(profile)
        self.session.commit()
        return existing or profile

    def get_profile(self, user_id: str):
        return self.session.query(UserProfile).filter(
            UserProfile.external_user_id == user_id
        ).first()


class QuestionnaireRepository:
    def __init__(self):
        self.session = get_session()

    def get_categories(self):
        return self.session.query(QuestionnaireCategory).order_by(QuestionnaireCategory.sort_order).all()

    def get_questions(self, category_id: int = None):
        query = self.session.query(QuestionnaireQuestion).filter(QuestionnaireQuestion.is_active == True)
        if category_id:
            query = query.filter(QuestionnaireQuestion.category_id == category_id)
        return query.order_by(QuestionnaireQuestion.sort_order).all()

    def save_answers(self, user_id: str, answers: list[dict]):
        for answer in answers:
            existing = self.session.query(UserQuestionnaireAnswer).filter(
                UserQuestionnaireAnswer.user_id == user_id,
                UserQuestionnaireAnswer.question_id == answer["question_id"]
            ).first()
            if existing:
                existing.answer_value = answer["answer_value"]
                existing.answer_scale = answer.get("answer_scale")
            else:
                self.session.add(UserQuestionnaireAnswer(
                    user_id=user_id,
                    question_id=answer["question_id"],
                    answer_value=answer["answer_value"],
                    answer_scale=answer.get("answer_scale")
                ))
        self.session.commit()

    def get_answers(self, user_id: str):
        return self.session.query(UserQuestionnaireAnswer).filter(
            UserQuestionnaireAnswer.user_id == user_id
        ).all()


class SearchPreferenceRepository:
    def __init__(self):
        self.session = get_session()

    def upsert(self, user_id: str, data: dict):
        existing = self.session.query(UserSearchPreference).filter(
            UserSearchPreference.user_id == user_id
        ).first()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            pref = UserSearchPreference(user_id=user_id, **data)
            self.session.add(pref)
        self.session.commit()
        return existing or pref

    def get(self, user_id: str):
        return self.session.query(UserSearchPreference).filter(
            UserSearchPreference.user_id == user_id
        ).first()


class RecommendationRepository:
    def __init__(self):
        self.session = get_session()

    def save_property_recommendations(self, user_id: str, results: list):
        self.session.query(PropertyRecommendation).filter(
            PropertyRecommendation.user_id == user_id
        ).delete()
        for rank, (prop, score, breakdown) in enumerate(results):
            self.session.add(PropertyRecommendation(
                user_id=user_id,
                property_id=prop.id,
                score=score,
                score_breakdown=breakdown,
                rank=rank
            ))
        self.session.commit()

    def save_room_recommendations(self, user_id: str, results: list):
        self.session.query(RoomRecommendation).filter(
            RoomRecommendation.user_id == user_id
        ).delete()
        for rank, (room, score, breakdown, prop) in enumerate(results):
            self.session.add(RoomRecommendation(
                user_id=user_id,
                room_id=room.id,
                score=score,
                score_breakdown=breakdown,
                rank=rank
            ))
        self.session.commit()

    def get_property_recommendations(self, user_id: str):
        return self.session.query(PropertyRecommendation).filter(
            PropertyRecommendation.user_id == user_id
        ).order_by(PropertyRecommendation.rank).all()

    def get_room_recommendations(self, user_id: str):
        return self.session.query(RoomRecommendation).filter(
            RoomRecommendation.user_id == user_id
        ).order_by(RoomRecommendation.rank).all()


class MatchingRepository:
    def __init__(self):
        self.session = get_session()

    def save_match(self, data: dict):
        existing = self.session.query(RoommateMatch).filter(
            RoommateMatch.seeker_user_id == data["seeker_user_id"],
            RoommateMatch.room_id == data["room_id"]
        ).first()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            match = RoommateMatch(**data)
            self.session.add(match)
        self.session.commit()

    def get_matches(self, user_id: str):
        return self.session.query(RoommateMatch).filter(
            RoommateMatch.seeker_user_id == user_id
        ).order_by(RoommateMatch.room_compatibility_score.desc()).all()


class InteractionRepository:
    def __init__(self):
        self.session = get_session()

    def log(self, data: dict):
        interaction = UserInteraction(**data)
        self.session.add(interaction)
        self.session.commit()

    def get_by_user(self, user_id: str):
        return self.session.query(UserInteraction).filter(
            UserInteraction.user_id == user_id
        ).order_by(UserInteraction.created_at.desc()).limit(50).all()