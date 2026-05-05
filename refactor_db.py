import os
import glob
from django.db import connection

# 1. Update Migration Files
print("--- Updating Migration Files ---")
files = glob.glob('core/migrations/*.py')
for fpath in files:
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = content.replace("'quizzes'", "'core'")
        
        if content != new_content:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {fpath}")
    except Exception as e:
        print(f"Error reading {fpath}: {e}")

# 2. Rename DB Tables and Update History
print("\n--- Renaming Database Tables ---")
queries = [
    # Rename Tables
    "RENAME TABLE quizzes_quiz TO core_quiz",
    "RENAME TABLE quizzes_question TO core_question",
    "RENAME TABLE quizzes_choice TO core_choice",
    "RENAME TABLE quizzes_attempt TO core_attempt",
    "RENAME TABLE quizzes_answer TO core_answer",
    "RENAME TABLE quizzes_quizaccessgrant TO core_quizaccessgrant",
    "RENAME TABLE quizzes_profile TO core_profile",
    "RENAME TABLE quizzes_category TO core_category",
    "RENAME TABLE quizzes_hackathonresult TO core_hackathonresult",
    "RENAME TABLE quizzes_announcement TO core_announcement",
    
    # Update Content Types
    "UPDATE django_content_type SET app_label='core' WHERE app_label='quizzes'",
    
    # Update Migrations History
    "UPDATE django_migrations SET app='core' WHERE app='quizzes'"
]

with connection.cursor() as cursor:
    for q in queries:
        try:
            cursor.execute(q)
            print(f"Executed: {q}")
        except Exception as e:
            # Table might not exist or already renamed
            print(f"Skipped/Failed: {q} \n   Reason: {e}")
