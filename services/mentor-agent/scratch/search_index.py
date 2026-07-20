import os

filepath = r"c:\Users\aishw\SAR-Student-Success-Retention\services\mentor-agent\static\index.html"
with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

search_terms = ["intervention", "generate", "faculty", "mentor", "student"]
for i, line in enumerate(lines):
    for term in search_terms:
        if term in line.lower():
            print(f"Line {i+1}: {line.strip()[:100]}")
            break
