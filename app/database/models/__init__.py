from app.database.models.base import Base
from app.database.models.property import SyncedProperty, SyncedRoom, SyncedAmenity, SyncedAllowedTenant
from app.database.models.user import UserProfile, QuestionnaireCategory, QuestionnaireQuestion, UserQuestionnaireAnswer, UserSearchPreference
from app.database.models.recommendation import PropertyRecommendation, RoomRecommendation, RoommateMatch, UserInteraction
from app.database.models.matching import PropertyEmbedding, UserEmbedding