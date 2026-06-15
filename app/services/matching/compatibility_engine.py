from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import asyncio

from app.database.session import get_session
from app.database.models.user import UserQuestionnaireAnswer
from app.repositories.questionnaire_repo import QuestionnaireRepository
from app.services.property_api_client import get_property_api_client
from app.services.matching.feature_encoding import (
    weighted_similarity,
    load_questionnaire_weights_and_metadata,
)


class CompatibilityEngine:
    def __init__(self):
        self.session = get_session()
        self.questionnaire_repo = QuestionnaireRepository()
        # Load dynamic weights and metadata
        self.weights, self.question_metadata, self.smoking_question_id = load_questionnaire_weights_and_metadata()
        # Identify age and occupation question IDs using matching_key
        self.age_question_id = self._find_question_by_matching_key("age")
        self.occupation_question_id = self._find_question_by_matching_key("occupation")

    def _find_question_by_matching_key(self, matching_key: str) -> Optional[int]:
        """Find question ID by matching_key."""
        for qid, meta in self.question_metadata.items():
            if meta.get("matching_key") == matching_key:
                return qid
        return None

    def _check_tenant_eligibility(self, seeker_profile, room_data: dict) -> bool:
        """Check if seeker is eligible for room based on tenant restrictions.
        
        Args:
            seeker_profile: UserProfile object
            room_data: Dictionary from API containing room and allowedTenants data
        
        Returns:
            True if eligible, False otherwise
        """
        if not seeker_profile:
            return True

        # Get allowedTenants from API payload
        allowed_tenants = room_data.get("allowedTenants")
        if not allowed_tenants:
            return True

        gender = (seeker_profile.get("gender") or "").lower()
        occupation = (seeker_profile.get("occupation") or "").lower()
        is_student = occupation == "student"
        is_worker = occupation == "worker"

        # Check gender restrictions
        if gender:
            sg = allowed_tenants.get("studentGender")
            wg = allowed_tenants.get("workerGender")

            if sg and allowed_tenants.get("allowsStudents"):
                if sg.lower() != gender:
                    return False

            if wg and allowed_tenants.get("allowsWorkers"):
                if wg.lower() != gender:
                    return False

        # Check occupation restrictions
        students_only = (
            allowed_tenants.get("allowsStudents") and
            not allowed_tenants.get("allowsWorkers") and
            not allowed_tenants.get("allowsFamilies")
        )
        workers_only = (
            allowed_tenants.get("allowsWorkers") and
            not allowed_tenants.get("allowsStudents") and
            not allowed_tenants.get("allowsFamilies")
        )

        if students_only and not is_student:
            return False
        if workers_only and not is_worker:
            return False

        return True

    async def _get_user_profile_from_api(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch user profile from .NET API."""
        api_client = get_property_api_client()
        profile = await api_client.get_user_profile(user_id)
        
        if not profile:
            return None
        
        # Normalize profile data to match expected structure
        return {
            "gender": profile.get("gender"),
            "birth_year": self._extract_birth_year(profile.get("birthDate")),
            "occupation": profile.get("jobTitle") or profile.get("fieldOfStudy"),
            "nationality": profile.get("nationality"),
            "city": profile.get("city"),
        }
    
    def _extract_birth_year(self, birth_date: Optional[str]) -> Optional[int]:
        """Extract birth year from birth date string."""
        if not birth_date:
            return None
        try:
            # Handle various date formats
            if "-" in birth_date:
                return int(birth_date.split("-")[0])
            return int(birth_date[:4])
        except (ValueError, IndexError):
            return None

    async def compute_for_user(self, seeker_id: str) -> dict:
        """Compute roommate compatibility for a user across all available rooms.
        
        Fetches rooms from .NET API instead of local sync tables.
        Returns live compatibility scores without database storage.
        """
        seeker_answers = self._get_answers_as_dict(seeker_id)
        seeker_profile = await self._get_user_profile_from_api(seeker_id)

        if not seeker_answers and not seeker_profile:
            return {"status": "skipped", "reason": "no data", "matches": []}

        # Fetch properties with rooms from .NET API
        api_client = get_property_api_client()
        properties = await api_client.get_all_properties_with_rooms()

        # Flatten rooms from all properties
        rooms = []
        for prop in properties:
            prop_rooms = prop.get("rooms", [])
            for room in prop_rooms:
                # Add property context to room data
                room_data = {
                    **room,
                    "property_id": prop.get("id"),
                    "property_city": prop.get("city"),
                    "property_government": prop.get("government"),
                }
                # Filter for available rooms only
                if room.get("capacityAvailable", 0) > 0:
                    rooms.append(room_data)

        matches = []
        
        for room_data in rooms:
            if not self._check_tenant_eligibility(seeker_profile, room_data):
                continue

            room_id = room_data.get("id")
            property_id = room_data.get("property_id")

            # Fetch occupants from .NET API
            occupants = await api_client.get_room_occupants(room_id)
            if not occupants:
                matches.append({
                    "room_id": room_id,
                    "property_id": property_id,
                    "room_compatibility_score": 0.65,
                    "roommate_count": 0,
                    "explanation": "Room is empty",
                })
                continue

            pairwise_scores = []
            roommate_details = []

            for occ_user_id in occupants:
                if occ_user_id == seeker_id:
                    continue

                occ_answers = self._get_answers_as_dict(occ_user_id)
                occ_profile = await self._get_user_profile_from_api(occ_user_id)

                if occ_answers and seeker_answers:
                    score = self._compute_pairwise(
                        seeker_answers, occ_answers,
                        seeker_profile, occ_profile
                    )
                else:
                    score = self._profile_only_score(seeker_profile, occ_profile)

                # Include all pairwise scores in aggregation (no threshold filtering)
                pairwise_scores.append(score)
                roommate_details.append({
                    "user_id": occ_user_id,
                    "score": round(score, 4),
                })

            if not pairwise_scores:
                continue

            room_capacity = room_data.get("capacity", 1)
            room_score = self._aggregate_room_score(pairwise_scores, room_capacity, len(occupants))
            
            matches.append({
                "room_id": room_id,
                "property_id": property_id,
                "room_compatibility_score": round(room_score, 4),
                "roommate_count": len(pairwise_scores),
                "roommate_details": roommate_details,
            })

        matches.sort(key=lambda m: m["room_compatibility_score"], reverse=True)
        return {"status": "completed", "seeker_user_id": seeker_id, "matches_count": len(matches), "matches": matches}

    async def compute_property_and_room_scores(self, seeker_id: str, property_id: int) -> dict:
        """Compute property-level and room-level compatibility scores for a user.
        
        Uses .NET API to fetch occupants and calculates live compatibility scores.
        
        Args:
            seeker_id: User ID seeking accommodation
            property_id: Property ID to compute compatibility for
        
        Returns:
            Dictionary with property_match_score and room_match_scores, or error if property not found
        """
        # Validate property exists first
        api_client = get_property_api_client()
        property_check = await api_client.property_exists(property_id)
        
        if not property_check["exists"]:
            return {
                "property_id": property_id,
                "error": property_check.get("error", "Property not found")
            }
        
        seeker_answers = self._get_answers_as_dict(seeker_id)
        seeker_profile = await self._get_user_profile_from_api(seeker_id)

        if not seeker_answers and not seeker_profile:
            return {
                "property_id": property_id,
                "property_match_score": 0.5,
                "rooms": []
            }
        
        # Fetch all occupants in the property with their room assignments
        property_occupants = await api_client.get_property_occupants(property_id)
        if not property_occupants:
            return {
                "property_id": property_id,
                "property_match_score": 0.65,
                "rooms": []
            }

        # Group occupants by room
        rooms_map = {}
        all_occupants = []
        
        for occ in property_occupants:
            user_id = occ.get("userId")
            room_id = occ.get("roomId")
            
            # Skip the seeker if they're already in the property
            if user_id == seeker_id:
                continue
            
            all_occupants.append(user_id)
            
            if room_id not in rooms_map:
                rooms_map[room_id] = []
            rooms_map[room_id].append(user_id)

        if not all_occupants:
            return {
                "property_id": property_id,
                "property_match_score": 0.65,
                "rooms": []
            }

        # Calculate pairwise scores for all occupants in property
        all_pairwise_scores = []
        room_scores = {}

        for room_id, occupants in rooms_map.items():
            room_pairwise_scores = []
            
            for occ_user_id in occupants:
                occ_answers = self._get_answers_as_dict(occ_user_id)
                occ_profile = await self._get_user_profile_from_api(occ_user_id)

                if occ_answers and seeker_answers:
                    score = self._compute_pairwise(
                        seeker_answers, occ_answers,
                        seeker_profile, occ_profile
                    )
                else:
                    score = self._profile_only_score(seeker_profile, occ_profile)

                # Include all pairwise scores in aggregation (no threshold filtering)
                room_pairwise_scores.append(score)
                all_pairwise_scores.append(score)

            # Calculate room-level score (average of pairwise scores in that room)
            if room_pairwise_scores:
                room_score = sum(room_pairwise_scores) / len(room_pairwise_scores)
                room_scores[room_id] = {
                    "room_id": room_id,
                    "room_match_score": round(room_score, 4),
                    "occupants_count": len(room_pairwise_scores)
                }

        # Calculate property-level score (average of all pairwise scores in property)
        # Fallback to 0.65 only when no occupants exist (handled earlier)
        # If occupants exist, always calculate actual average even if scores are low
        if all_pairwise_scores:
            property_score = sum(all_pairwise_scores) / len(all_pairwise_scores)
        else:
            # This should only happen if all_occupants was empty (handled earlier)
            # or if all scores failed to compute (edge case)
            property_score = 0.65

        # Build response
        rooms_list = list(room_scores.values())
        rooms_list.sort(key=lambda r: r["room_match_score"], reverse=True)

        return {
            "property_id": property_id,
            "property_match_score": round(property_score, 4),
            "rooms": rooms_list
        }

    async def compute_properties_match_scores(self, seeker_id: str, property_ids: list) -> dict:
        """Compute property match scores for specified properties.
        
        Fetches occupants for multiple properties in parallel and computes
        property-level compatibility scores for each property.
        
        Args:
            seeker_id: User ID seeking accommodation
            property_ids: List of property IDs to compute scores for
        
        Returns:
            Dictionary with property_id -> property_match_score mapping, or error for invalid properties
        """
        seeker_answers = self._get_answers_as_dict(seeker_id)
        seeker_profile = await self._get_user_profile_from_api(seeker_id)

        if not seeker_answers and not seeker_profile:
            return {
                "status": "skipped",
                "reason": "no data",
                "properties": []
            }

        api_client = get_property_api_client()
        
        # Validate all properties exist in parallel
        async def check_property(property_id: int):
            check = await api_client.property_exists(property_id)
            return property_id, check
        
        checks = await asyncio.gather(*[check_property(pid) for pid in property_ids])
        property_checks = {pid: check for pid, check in checks}
        
        # Fetch occupants for valid properties in parallel
        valid_property_ids = [pid for pid, check in property_checks.items() if check["exists"]]
        
        if valid_property_ids:
            occupants_map = await api_client.get_multiple_property_occupants(valid_property_ids)
        else:
            occupants_map = {}
        
        property_scores = []
        
        for property_id in property_ids:
            property_check = property_checks.get(property_id)
            
            if not property_check["exists"]:
                # Property not found - add error entry
                property_scores.append({
                    "property_id": property_id,
                    "error": property_check.get("error", "Property not found")
                })
                continue
            
            # Property exists - fetch occupants and compute score
            property_occupants = occupants_map.get(property_id, [])
            
            if not property_occupants:
                # No occupants, give a default score
                property_scores.append({
                    "property_id": property_id,
                    "property_match_score": 0.65
                })
                continue
            
            # Get all occupant user IDs
            all_occupants = []
            for occ in property_occupants:
                user_id = occ.get("userId")
                if user_id == seeker_id:
                    continue
                all_occupants.append(user_id)
            
            if not all_occupants:
                property_scores.append({
                    "property_id": property_id,
                    "property_match_score": 0.65
                })
                continue
            
            # Calculate pairwise scores for all occupants
            pairwise_scores = []
            for occ_user_id in all_occupants:
                occ_answers = self._get_answers_as_dict(occ_user_id)
                occ_profile = await self._get_user_profile_from_api(occ_user_id)
                
                if occ_answers and seeker_answers:
                    score = self._compute_pairwise(
                        seeker_answers, occ_answers,
                        seeker_profile, occ_profile
                    )
                else:
                    score = self._profile_only_score(seeker_profile, occ_profile)
                
                # Include all pairwise scores in aggregation (no threshold filtering)
                pairwise_scores.append(score)
            
            # Calculate property-level score
            if pairwise_scores:
                property_score = sum(pairwise_scores) / len(pairwise_scores)
            else:
                property_score = 0.65
            
            property_scores.append({
                "property_id": property_id,
                "property_match_score": round(property_score, 4)
            })
        
        return {
            "status": "completed",
            "seeker_user_id": seeker_id,
            "properties": property_scores
        }

    def _compute_pairwise(self, answers_a: dict, answers_b: dict, profile_a=None, profile_b=None) -> float:
        # Exclude age and occupation questions from questionnaire scoring to avoid duplicate counting
        # These are handled separately via profile fields below
        filtered_answers_a = {k: v for k, v in answers_a.items() if int(k) not in [self.age_question_id, self.occupation_question_id]}
        filtered_answers_b = {k: v for k, v in answers_b.items() if int(k) not in [self.age_question_id, self.occupation_question_id]}
        
        # Also filter weights to exclude age and occupation questions
        filtered_weights = {k: v for k, v in self.weights.items() if k not in [self.age_question_id, self.occupation_question_id]}
        
        q_score = weighted_similarity(
            filtered_answers_a, 
            filtered_answers_b,
            filtered_weights,
            self.question_metadata,
            self.smoking_question_id
        )

        occupation_sim = 1.0
        if profile_a and profile_b and profile_a.get("occupation") and profile_b.get("occupation"):
            occ_a = profile_a.get("occupation", "").lower() if profile_a.get("occupation") else ""
            occ_b = profile_b.get("occupation", "").lower() if profile_b.get("occupation") else ""
            occupation_sim = 1.0 if occ_a == occ_b else 0.5

        age_sim = 1.0
        if profile_a and profile_b and profile_a.get("birth_year") and profile_b.get("birth_year"):
            age_diff = abs(profile_a.get("birth_year") - profile_b.get("birth_year"))
            age_sim = max(0.0, 1.0 - age_diff / 20.0)

        return 0.85 * q_score + 0.08 * occupation_sim + 0.07 * age_sim

    def _profile_only_score(self, profile_a, profile_b) -> float:
        if not profile_a or not profile_b:
            return 0.5
        
        # Handle both dict and object profiles
        def get_attr(profile, key, default=None):
            if isinstance(profile, dict):
                return profile.get(key, default)
            return getattr(profile, key, default)
        
        occ_a = get_attr(profile_a, 'occupation', '')
        occ_b = get_attr(profile_b, 'occupation', '')
        occ = 1.0 if (occ_a or "").lower() == (occ_b or "").lower() else 0.5
        
        age = 0.5
        birth_a = get_attr(profile_a, 'birth_year')
        birth_b = get_attr(profile_b, 'birth_year')
        if birth_a and birth_b:
            age = max(0.0, 1.0 - abs(birth_a - birth_b) / 20.0)
        
        return 0.6 * occ + 0.4 * age

    def _aggregate_room_score(self, pairwise_scores: list[float], total_capacity: int, occupant_count: int) -> float:
        if not pairwise_scores:
            return 0.65
        min_s = min(pairwise_scores)
        avg_s = sum(pairwise_scores) / len(pairwise_scores)
        agg = 0.6 * min_s + 0.4 * avg_s
        empty = max(0, total_capacity - occupant_count)
        agg += min(0.1, empty * 0.03)
        return min(1.0, agg)

    def _get_answers_as_dict(self, user_id: str) -> dict:
        answers = self.session.query(UserQuestionnaireAnswer).filter(
            UserQuestionnaireAnswer.user_id == user_id
        ).all()
        result = {}
        for a in answers:
            val = a.answer_scale if a.answer_scale is not None else a.answer_value
            result[str(a.question_id)] = val
        return result