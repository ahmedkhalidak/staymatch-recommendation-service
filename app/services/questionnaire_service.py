from app.repositories.questionnaire_repo import QuestionnaireRepository


class QuestionnaireService:
    def __init__(self):
        self.repo = QuestionnaireRepository()
        
        # Machine key mapping for questions (question_id -> machine_key)
        self.question_key_map = {
            1: "age_group",
            2: "occupation_status",
            3: "study_or_work_field",
            4: "busiest_time",
            5: "sleep_time",
            6: "first_activity_home",
            7: "mess_tolerance",
            8: "free_day_style",
            9: "group_activity_preference",
            10: "study_environment",
            11: "smoking_preference",
            12: "biggest_shared_living_issue",
            13: "flexibility_level",
        }
        
        # Reverse mapping (machine_key -> question_id)
        self.key_question_map = {v: k for k, v in self.question_key_map.items()}

    def get_all_questions(self):
        categories = self.repo.get_categories()
        result = []
        for cat in categories:
            questions = cat.get("questions", [])
            result.append({
                "category": {
                    "id": cat["id"],
                    "name_ar": cat["name_ar"],
                    "name_en": cat["name_en"],
                },
                "questions": [
                    self._transform_question(q)
                    for q in questions
                ]
            })
        return result
    
    def _transform_question(self, question):
        """Transform question to new API contract format."""
        machine_key = self.question_key_map.get(question.id, f"question_{question.id}")
        
        # Transform options from arrays to map with 1-based numbering
        options_map = {}
        if question.options_ar and question.options_en:
            for i, (ar, en) in enumerate(zip(question.options_ar, question.options_en)):
                options_map[str(i + 1)] = {  # 1-based numbering
                    "ar": ar,
                    "en": en
                }
        
        return {
            "id": question.id,
            "key": machine_key,
            "question_ar": question.question_ar,
            "question_en": question.question_en,
            "question_type": question.question_type,
            "weight": question.weight,
            "options": options_map
        }
    
    def transform_answers_to_map(self, answers_dict):
        """Transform answers from question_id keys to machine_key keys (convert 0-based to 1-based)."""
        transformed = {}
        for question_id, answer_scale in answers_dict.items():
            machine_key = self.question_key_map.get(int(question_id), f"question_{question_id}")
            # Convert 0-based storage to 1-based API response
            transformed[machine_key] = answer_scale + 1
        return transformed
    
    def transform_answers_from_map(self, answers_map):
        """Transform answers from machine_key keys to question_id keys."""
        transformed = {}
        for machine_key, answer_scale in answers_map.items():
            question_id = self.key_question_map.get(machine_key)
            if question_id is None:
                # Unknown key, try to parse as question_id
                try:
                    question_id = int(machine_key.replace("question_", ""))
                except ValueError:
                    continue
            transformed[str(question_id)] = answer_scale
        return transformed
    
    def validate_answers_against_options(self, answers_map):
        """Validate that answer values are within valid option ranges for each question.
        
        Raises ValueError with detailed message if validation fails.
        """
        # Get all questions with their option counts
        questions = self.repo.get_questions()
        
        # Build a map of machine_key -> option_count
        option_counts = {}
        for q in questions:
            machine_key = self.question_key_map.get(q.id, f"question_{q.id}")
            if q.options_ar:
                option_counts[machine_key] = len(q.options_ar)
        
        # Validate each answer
        for machine_key, answer_scale in answers_map.items():
            if machine_key not in option_counts:
                raise ValueError(f"Unknown question key: {machine_key}")
            
            max_option = option_counts[machine_key]
            if answer_scale < 1:
                raise ValueError(f"Answer for {machine_key} must be >= 1 (got {answer_scale})")
            if answer_scale > max_option:
                raise ValueError(f"Answer for {machine_key} must be <= {max_option} (got {answer_scale})")
        
        return True