import requests
import json
import pprint

DASHBOARD_URL = "http://127.0.0.1:8001"
student_id = "STU202600001"

print("=== Starting Faculty Dashboard API Verification ===")

# 1. Check stats endpoint
print("\n1. Testing /api/stats...")
res = requests.get(f"{DASHBOARD_URL}/api/stats")
print(f"Status Code: {res.status_code}")
if res.status_code == 200:
    pprint.pprint(res.json())
else:
    print(f"Error: {res.text}")

# 2. Check students list endpoint
print("\n2. Testing /api/students...")
res = requests.get(f"{DASHBOARD_URL}/api/students")
print(f"Status Code: {res.status_code}")
if res.status_code == 200:
    students = res.json()
    print(f"Successfully loaded {len(students)} students.")
    print("First student sample:")
    pprint.pprint(students[0])
else:
    print(f"Error: {res.text}")

# 3. Check student details endpoint
print(f"\n3. Testing /api/students/{student_id}...")
res = requests.get(f"{DASHBOARD_URL}/api/students/{student_id}")
print(f"Status Code: {res.status_code}")
if res.status_code == 200:
    detail = res.json()
    print(f"Successfully loaded details for {detail.get('profile', {}).get('name')}.")
    print("Details summary keys:")
    print(detail.keys())
    print("Risk Profile:")
    pprint.pprint(detail.get("risk_profile"))
    print("Workflow:")
    pprint.pprint(detail.get("workflow"))
else:
    print(f"Error: {res.text}")

# 4. Check workflow status update
print(f"\n4. Updating workflow status for {student_id} to 'Intervention Pending'...")
res = requests.post(f"{DASHBOARD_URL}/api/students/{student_id}/workflow", json={"status": "Intervention Pending"})
print(f"Status Code: {res.status_code}")
if res.status_code == 200:
    print("Workflow updated:")
    pprint.pprint(res.json())

# 5. Add a persistent comment
comment_text = "Met student today. Discussed low attendance cell reference guide. Initiating RAG mentoring."
print(f"\n5. Adding comment to {student_id}...")
res = requests.post(f"{DASHBOARD_URL}/api/students/{student_id}/comments", json={"comment_text": comment_text})
print(f"Status Code: {res.status_code}")
if res.status_code == 200:
    print("Comment added successfully.")

# 6. Verify comments list
print(f"\n6. Fetching comments for {student_id}...")
res = requests.get(f"{DASHBOARD_URL}/api/students/{student_id}/comments")
print(f"Status Code: {res.status_code}")
if res.status_code == 200:
    comments = res.json()
    print(f"Loaded {len(comments)} comments. Latest comment:")
    pprint.pprint(comments[0])

print("\n=== Faculty Dashboard API Verification Finished ===")
