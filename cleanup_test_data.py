#!/usr/bin/env python
from app.database.session import get_engine
from sqlalchemy import text

engine = get_engine()
with engine.begin() as conn:
    conn.execute(text('TRUNCATE TABLE user_questionnaire_answers, questionnaire_profiles, user_profiles RESTART IDENTITY CASCADE'))
    print('Cleaned up test data')
