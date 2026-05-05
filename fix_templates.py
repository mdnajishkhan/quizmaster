import os

# Walk through all directories and files
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for old base.html ref
                if "quizzes/base.html" in content:
                    print(f"fixing {path}")
                    new_content = content.replace("quizzes/base.html", "core/base.html")
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                        
                # Check for other old template refs (just in case)
                if "quizzes/" in content:
                     # Be careful with this one, might replace valid text.
                     # But for 'extends' and 'include' tags it should be safe.
                     pass 

            except Exception as e:
                print(f"Skipping {path}: {e}")
