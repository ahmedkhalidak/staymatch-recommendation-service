"""Check what tables actually exist in the database."""
import sys
sys.path.insert(0, '/home/ahmed-khalid/AHMED-Projects-2026/staymatch-recommendation-service')

from app.database.session import get_session
from sqlalchemy import text

session = get_session()
result = session.execute(text("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name
""")).fetchall()

print("Actual tables in database:")
for row in result:
    print(f"  - {row[0]}")

session.close()
