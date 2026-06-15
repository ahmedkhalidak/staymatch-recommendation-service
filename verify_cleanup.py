#!/usr/bin/env python
from app.database.session import get_engine
from sqlalchemy import text, inspect

engine = get_engine()

# Check row counts
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM user_profiles'))
    print(f'user_profiles: {result.scalar()}')
    
    result = conn.execute(text('SELECT COUNT(*) FROM questionnaire_profiles'))
    print(f'questionnaire_profiles: {result.scalar()}')
    
    result = conn.execute(text('SELECT COUNT(*) FROM user_questionnaire_answers'))
    print(f'user_questionnaire_answers: {result.scalar()}')
    
    result = conn.execute(text('SELECT COUNT(*) FROM user_search_preferences'))
    print(f'user_search_preferences: {result.scalar()}')

# Check tables
inspector = inspect(engine)
tables = inspector.get_table_names()
user_related = [t for t in tables if 'user' in t.lower() or 'questionnaire' in t.lower()]
print('\nUser and questionnaire related tables:')
for table in sorted(user_related):
    print(f'  - {table}')

# Check foreign keys
print('\nForeign keys in questionnaire_profiles:')
fks = inspector.get_foreign_keys('questionnaire_profiles')
for fk in fks:
    print(f'  - {fk["constrained_columns"]} -> {fk["referred_table"]}.{fk["referred_columns"]}')

print('\nForeign keys in user_questionnaire_answers:')
fks = inspector.get_foreign_keys('user_questionnaire_answers')
for fk in fks:
    print(f'  - {fk["constrained_columns"]} -> {fk["referred_table"]}.{fk["referred_columns"]}')

print('\nForeign keys in user_search_preferences:')
fks = inspector.get_foreign_keys('user_search_preferences')
for fk in fks:
    print(f'  - {fk["constrained_columns"]} -> {fk["referred_table"]}.{fk["referred_columns"]}')
