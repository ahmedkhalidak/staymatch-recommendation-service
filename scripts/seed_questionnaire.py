#!/usr/bin/env python3
"""
16 questions: personality + lifestyle + social + financial + career/study.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database.session import get_session
from app.database.models.user import QuestionnaireCategory, QuestionnaireQuestion


CATEGORIES = [
    {"name_ar": "الشخصية والدراسة/العمل", "name_en": "Personality & Career", "sort_order": 1},
    {"name_ar": "نمط الحياة", "name_en": "Lifestyle & Habits", "sort_order": 2},
    {"name_ar": "التواصل والمعيشة", "name_en": "Social & Cohabitation", "sort_order": 3},
    {"name_ar": "المالية والنظافة", "name_en": "Finance & Cleanliness", "sort_order": 4},
]

QUESTIONS = [
    # --- 1. Career/Study ---
    {
        "category": 1,
        "question_ar": "إيه وضعك دلوقتي؟",
        "question_en": "What is your current status?",
        "question_type": "multiple_choice",
        "options_ar": ["طالب", "موظف", "عمل حر/فري لانس", "ريادي أعمال", "باحث عن عمل"],
        "options_en": ["Student", "Employee", "Freelancer", "Entrepreneur", "Job Seeker"],
        "weight": 1.0, "sort_order": 1,
    },
    {
        "category": 1,
        "question_ar": "لو طالب، إيه كليتك أو تخصصك؟",
        "question_en": "If student, what is your college or major?",
        "question_type": "multiple_choice",
        "options_ar": ["هندسة", "طب", "صيدلة", "علوم/حاسبات", "حقوق", "تجارة", "آداب", "تربية", "فنون", "أخرى"],
        "options_en": ["Engineering", "Medicine", "Pharmacy", "Sciences/CS", "Law", "Business", "Arts", "Education", "Fine Arts", "Other"],
        "weight": 0.7, "sort_order": 2,
    },
    {
        "category": 1,
        "question_ar": "كيف تصف شخصيتك؟",
        "question_en": "How would you describe your personality?",
        "question_type": "multiple_choice",
        "options_ar": ["منظم جدًا — بحب النظام والمواعيد", "اجتماعي — بحب الناس والجو", "هادئ — بحب العزلة والهدوء", "مرن — ماشي مع التيار"],
        "options_en": ["Organized — love structure and punctuality", "Social — love people and energy", "Quiet — prefer solitude and calm", "Flexible — go with the flow"],
        "weight": 0.9, "sort_order": 3,
    },

    # --- 2. Lifestyle ---
    {
        "category": 2,
        "question_ar": "إيه نظام نومك؟",
        "question_en": "What is your sleep schedule?",
        "question_type": "multiple_choice",
        "options_ar": ["بدري جدًا — أصحى من ٥-٧ ص", "متوسط — ٧-٩ ص", "متأخر — ٩-١٢ ص", "بوم نايت — أصحى بالليل"],
        "options_en": ["Early bird — wake 5-7 AM", "Moderate — 7-9 AM", "Late — 9 AM-12 PM", "Night owl — sleep by day"],
        "weight": 1.0, "sort_order": 4,
    },
    {
        "category": 2,
        "question_ar": "بتدخن ولا لأ؟",
        "question_en": "Do you smoke?",
        "question_type": "multiple_choice",
        "options_ar": ["لا نهائيًا", "سجائر", "شيشة", "Vape", "أحيانًا اجتماعيًا"],
        "options_en": ["Never", "Cigarettes", "Shisha", "Vape", "Occasionally socially"],
        "weight": 1.0, "sort_order": 5,
    },
    {
        "category": 2,
        "question_ar": "بتجيب زوار كتير في البيت؟",
        "question_en": "How often do you host visitors at home?",
        "question_type": "multiple_choice",
        "options_ar": ["نادر جدًا — مرة في الشهر", "أحيانًا — أسبوعيًا", "كتير — مرتين تلاتة في الأسبوع", "دايمًا — كل يوم تقريبًا"],
        "options_en": ["Rarely — once a month", "Sometimes — weekly", "Often — 2-3 times a week", "Always — almost daily"],
        "weight": 0.8, "sort_order": 6,
    },
    {
        "category": 2,
        "question_ar": "مستوى الضوضاء اللي تريحك في البيت؟",
        "question_en": "Noise level you're comfortable with at home?",
        "question_type": "multiple_choice",
        "options_ar": ["هادي جدًا (مكتبة)", "هادي نسبيًا", "معتدل", "عادي — مفيش مشكلة"],
        "options_en": ["Very quiet (library)", "Relatively quiet", "Moderate", "Fine — no issue"],
        "weight": 0.7, "sort_order": 7,
    },
    {
        "category": 2,
        "question_ar": "بتتمرن أو بتعمل رياضة؟",
        "question_en": "Do you exercise or play sports?",
        "question_type": "multiple_choice",
        "options_ar": ["يوميًا", "٣-٤ مرات في الأسبوع", "مرة في الأسبوع", "نادرًا", "لا خالص"],
        "options_en": ["Daily", "3-4 times a week", "Once a week", "Rarely", "Never"],
        "weight": 0.5, "sort_order": 8,
    },

    # --- 3. Social & Cohabitation ---
    {
        "category": 3,
        "question_ar": "إزاي بتتعامل مع الخلاف مع زميل السكن؟",
        "question_en": "How do you handle conflict with a roommate?",
        "question_type": "multiple_choice",
        "options_ar": ["أواجه فورًا وبصراحة", "أنتظر الوقت المناسب", "أتجنب وأمشي", "أفضل شخص وسيط"],
        "options_en": ["Address directly immediately", "Wait for right time", "Avoid and move on", "Prefer a mediator"],
        "weight": 0.9, "sort_order": 9,
    },
    {
        "category": 3,
        "question_ar": "كم مرة تحب تتفاعل مع زميل السكن؟",
        "question_en": "How often do you want to interact with your roommate?",
        "question_type": "multiple_choice",
        "options_ar": ["كل واحد في حاله", "كلام يومي عادي", "جلسات أسبوعيًا", "قضاء معظم الوقت سوا"],
        "options_en": ["Each in their own space", "Daily casual chat", "Weekly hangouts", "Most time together"],
        "weight": 0.8, "sort_order": 10,
    },
    {
        "category": 3,
        "question_ar": "إيه رأيك في مشاركة الأكل والأغراض؟",
        "question_en": "How do you feel about sharing food and items?",
        "question_type": "multiple_choice",
        "options_ar": ["كل حاجة مشتركة", "بعض الحاجات الأساسية", "ممنوع — كل واحد أكلوه وأغراضه"],
        "options_en": ["Everything shared", "Some basic items", "No — keep separate"],
        "weight": 0.6, "sort_order": 11,
    },
    {
        "category": 3,
        "question_ar": "موقفك من استضافة الأصدقاء في البيت؟",
        "question_en": "Your stance on hosting friends at home?",
        "question_type": "multiple_choice",
        "options_ar": ["ممنوع تمامًا", "مسموح بإخطار", "مسموح بحرية", "حسب الاتفاق"],
        "options_en": ["Not allowed", "Allowed with notice", "Freely allowed", "Depends on agreement"],
        "weight": 0.7, "sort_order": 12,
    },

    # --- 4. Finance & Cleanliness ---
    {
        "category": 4,
        "question_ar": "إزاي تقسم الفواتير (كهربا، ميا، نت)؟",
        "question_en": "How to split bills (electricity, water, internet)?",
        "question_type": "multiple_choice",
        "options_ar": ["بالتساوي", "حسب الاستخدام", "كل واحد حصته", "صندوق مشترك شهري"],
        "options_en": ["Equally", "By usage", "Each pays share", "Monthly joint fund"],
        "weight": 0.9, "sort_order": 13,
    },
    {
        "category": 4,
        "question_ar": "التزامك بدفع الإيجار والفواتير؟",
        "question_en": "Your commitment to paying rent/bills on time?",
        "question_type": "multiple_choice",
        "options_ar": ["دايمًا في الميعاد بالظبط", "في الميعاد غالبًا", "أحيانًا بتأخر", "بنسى — محتاج تذكير"],
        "options_en": ["Always exactly on time", "Mostly on time", "Sometimes late", "I forget — need reminders"],
        "weight": 1.0, "sort_order": 14,
    },
    {
        "category": 4,
        "question_ar": "مستوى النضافة اللي يريحك في الأماكن المشتركة؟",
        "question_en": "Cleanliness level you prefer in shared spaces?",
        "question_type": "multiple_choice",
        "options_ar": ["متعقّد — لازم كل حاجة نضيفة دايمًا", "مرتب — بنضف بانتظام", "عادي — بنضف لما أحتاج", "عادي — الفوضى مش مشكلة"],
        "options_en": ["Obsessed — always spotless", "Tidy — clean regularly", "Normal — clean when needed", "Casual — clutter is fine"],
        "weight": 1.0, "sort_order": 15,
    },
    {
        "category": 4,
        "question_ar": "تقسيم مهام النضافة: إيه المناسب ليك؟",
        "question_en": "Chores division: what works for you?",
        "question_type": "multiple_choice",
        "options_ar": ["جدول أسبوعي منظم", "بالتناوب", "كل واحد ينضف ورا نفسه", "أدفع لخدمة نظافة"],
        "options_en": ["Organized weekly schedule", "Rotation", "Each cleans after self", "Hire a cleaning service"],
        "weight": 0.9, "sort_order": 16,
    },
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