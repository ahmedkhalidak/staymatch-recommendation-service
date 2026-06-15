#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database.session import get_session
from app.database.models.user import QuestionnaireCategory, QuestionnaireQuestion

CATEGORIES = [
    {"name_ar": "البيانات الشخصية", "name_en": "Personal Background", "sort_order": 1},
    {"name_ar": "الروتين اليومي", "name_en": "Daily Schedule", "sort_order": 2},
    {"name_ar": "نمط الحياة", "name_en": "Lifestyle", "sort_order": 3},
    {"name_ar": "التوافق الاجتماعي", "name_en": "Social Compatibility", "sort_order": 4},
]

QUESTIONS = [
    {"category": 1, "question_ar": "كم عمرك؟", "question_en": "What is your age group?", "options_ar": ["أقل من 20", "20-24", "25-30", "أكثر من 30"], "options_en": ["Under 20", "20-24", "25-30", "30+"], "weight": 0.03, "sort_order": 1},
    {"category": 1, "question_ar": "وضعك الحالي؟", "question_en": "What is your current status?", "options_ar": ["طالب", "موظف", "عمل حر", "طالب وموظف"], "options_en": ["Student", "Employee", "Freelancer", "Working & Studying"], "weight": 0.05, "sort_order": 2},
    {"category": 1, "question_ar": "مجال دراستك أو عملك؟", "question_en": "Your field of study or work?", "options_ar": ["هندسة", "طب", "حاسبات", "أعمال", "فنون", "تعليم", "قانون", "أخرى"], "options_en": ["Engineering", "Medicine", "IT-CS", "Business", "Arts", "Education", "Law", "Other"], "weight": 0.05, "sort_order": 3},
    {"category": 2, "question_ar": "أكثر وقت مشغول في يومك؟", "question_en": "Most busy time during the day?", "options_ar": ["الصبح بدري", "متأخر الصباح", "الظهر", "المساء", "الليل"], "options_en": ["Early morning", "Late morning", "Afternoon", "Evening", "Night"], "weight": 0.10, "sort_order": 4},
    {"category": 2, "question_ar": "موعد نومك المعتاد؟", "question_en": "Typical sleeping time?", "options_ar": ["قبل 10", "10-12", "12-2 ص", "بعد 2 ص"], "options_en": ["Before 10PM", "10PM-12AM", "12AM-2AM", "After 2AM"], "weight": 0.14, "sort_order": 5},
    {"category": 2, "question_ar": "أول حاجة تعملها لما ترجع البيت؟", "question_en": "First action after returning home?", "options_ar": ["أتغسل", "أروح أوضتي", "آكل", "أتحدث مع الناس"], "options_en": ["Wash/shower", "Go to my room", "Eat", "Start socializing"], "weight": 0.04, "sort_order": 6},
    {"category": 3, "question_ar": "رد فعلك على الفوضى في الأماكن المشتركة؟", "question_en": "Reaction to mess in shared spaces?", "options_ar": ["أنضف فورًا", "أضايق لكن أستنى", "أنضف لما أفرغ", "مش مشكلة"], "options_en": ["Clean immediately", "Get annoyed but wait", "Clean when I have time", "Doesn't bother me"], "weight": 0.14, "sort_order": 7},
    {"category": 3, "question_ar": "بتقضي أيام إجازتك إزاي؟", "question_en": "How do you spend free days?", "options_ar": ["في البيت", "مع صحابي", "دراسة أو شغل", "هوايات", "زيارة أهلي"], "options_en": ["At home", "Out with friends", "Studying/working", "Hobbies", "Visiting family"], "weight": 0.03, "sort_order": 8},
    {"category": 3, "question_ar": "بتشارك في الأنشطة الجماعية؟", "question_en": "Do you participate in group activities?", "options_ar": ["بحبها دايمًا", "أحيانًا", "نادرًا", "بحب أكون لوحدي"], "options_en": ["Love it", "Sometimes", "Rarely", "Prefer alone"], "weight": 0.07, "sort_order": 9},
    {"category": 3, "question_ar": "البيئة اللي تريحك في المذاكرة أو الشغل؟", "question_en": "Preferred study/work environment?", "options_ar": ["هادئ خاص", "متوسط", "كافيهات", "أي مكان"], "options_en": ["Quiet private", "Moderate noise", "Cafes/public", "Flexible"], "weight": 0.08, "sort_order": 10},
    {"category": 4, "question_ar": "موقفك من التدخين؟", "question_en": "Smoking preference?", "options_ar": ["لا أدخن وأفضل غير مدخن", "لا أدخن ومش مشكلة", "أدخن ومش مشكلة", "أدخن وأفضل مدخن"], "options_en": ["Non-smoker prefer non-smoker", "Non-smoker okay", "Smoker okay with others", "Smoker prefer smoker"], "weight": 0.14, "sort_order": 11},
    {"category": 4, "question_ar": "أكتر حاجة بتضايقك في السكن المشترك؟", "question_en": "Biggest shared housing frustration?", "options_ar": ["الفوضى", "الضوضاء", "الفواتير", "قلة الخصوصية", "اختلاف المواعيد"], "options_en": ["Mess", "Noise", "Bills", "Lack of privacy", "Different schedules"], "weight": 0.05, "sort_order": 12},
    {"category": 4, "question_ar": "مرونتك تجاه أنماط الحياة المختلفة؟", "question_en": "Flexibility toward different lifestyles?", "options_ar": ["جداً", "نوعاً ما", "أفضل نمط مشابه", "لازم نفس أسلوب حياتي"], "options_en": ["Very flexible", "Somewhat flexible", "Prefer similar", "Must match mine"], "weight": 0.08, "sort_order": 13},
]

def seed():
    session = get_session()
    session.query(QuestionnaireQuestion).delete()
    session.query(QuestionnaireCategory).delete()
    session.commit()

    for cat_data in CATEGORIES:
        session.add(QuestionnaireCategory(**cat_data))
    session.flush()

    all_cats = session.query(QuestionnaireCategory).order_by(QuestionnaireCategory.sort_order).all()
    cat_map = {i + 1: c.id for i, c in enumerate(all_cats)}

    for q_data in QUESTIONS:
        cat_order = q_data.pop("category")
        session.add(QuestionnaireQuestion(category_id=cat_map[cat_order], **q_data))

    session.commit()
    print(f"Seeded {len(CATEGORIES)} categories and {len(QUESTIONS)} questions")

if __name__ == "__main__":
    seed()