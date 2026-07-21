import os

filepath = r"c:\Users\aishw\SAR-Student-Success-Retention\services\mentor-agent\static\index.html"
with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "<body>" in line.lower() or "</body>" in line.lower() or "<main>" in line.lower() or "</main>" in line.lower() or "<script>" in line.lower():
        print(f"Line {i+1}: {line.strip()[:100]}")
