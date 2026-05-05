import os
import glob

print("--- Updating Training Migration Files ---")
files = glob.glob('training/migrations/*.py')
for fpath in files:
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace dependencies on 'quizzes' with 'core'
        new_content = content.replace("'quizzes'", "'core'")
        
        if content != new_content:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {fpath}")
    except Exception as e:
        print(f"Error reading {fpath}: {e}")
