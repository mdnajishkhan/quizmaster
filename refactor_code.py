import os
import glob

# Files to scan in 'core' and 'training'
files_to_scan = glob.glob('core/*.py') + glob.glob('training/*.py') + glob.glob('recgetup/*.py')

print(f"Scanning {len(files_to_scan)} files for 'quizzes' references...")

for fpath in files_to_scan:
    if fpath.endswith('refactor_db.py') or fpath.endswith('refactor_training.py') or fpath.endswith('refactor_code.py'):
        continue
        
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Naive replacement of imports and string references
        # 1. "from quizzes" -> "from core"
        # 2. "import quizzes" -> "import core"
        # 3. "quizzes.models" -> "core.models"
        # 4. "quizzes.views" -> "core.views"
        # 5. "quizzes.urls" -> "core.urls"
        # 6. "'quizzes'" -> "'core'" (Be careful with this one)
        # 7. "quizzes/" -> "core/" (Templates)
        
        new_content = content.replace("from quizzes", "from core")
        new_content = new_content.replace("import quizzes", "import core")
        new_content = new_content.replace("app_name = 'quizzes'", "app_name = 'core'")
        new_content = new_content.replace('app_name = "quizzes"', 'app_name = "core"')
        
        # Template paths
        new_content = new_content.replace("'quizzes/", "'core/")
        new_content = new_content.replace('"quizzes/', '"core/')
        
        # Configs
        new_content = new_content.replace("quizzes.apps.QuizzesConfig", "core.apps.CoreConfig")
        
        if content != new_content:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {fpath}")
            
    except Exception as e:
        print(f"Error processing {fpath}: {e}")
