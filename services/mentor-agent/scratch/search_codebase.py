import os

search_dir = r"c:\Users\aishw\SAR-Student-Success-Retention"
exclude_dirs = {".git", "venv", "__pycache__", "chroma_db"}
exclude_extensions = {".db", ".pyc", ".png", ".jpg", ".jpeg", ".ico"}

patterns = ["login as a mentor", "login as mentor", "login as a", "mentor login", "login-btn"]

found = []

for root, dirs, files in os.walk(search_dir):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for file in files:
        if any(file.endswith(ext) for ext in exclude_extensions):
            continue
        filepath = os.path.join(root, file)
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    line_lower = line.lower()
                    for p in patterns:
                        if p in line_lower:
                            found.append({
                                "file": filepath,
                                "line_num": line_num,
                                "pattern": p,
                                "line": line.strip()
                            })
        except Exception as e:
            pass

print(f"Found {len(found)} matches:")
for item in found:
    print(f"File: {item['file']}:{item['line_num']} (Matched '{item['pattern']}')")
    print(f"  Line: {item['line']}")
    print("-" * 50)
