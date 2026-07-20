import requests
import json

BASE_URL = "http://127.0.0.1:8000"
student_id = "STU202600011"

print("--- Start API Verification ---")

# 1. Health check
res = requests.get(f"{BASE_URL}/health")
print(f"Health Check: {res.status_code} - {res.json()}")

# 2. Fetch companies list
res = requests.get(f"{BASE_URL}/api/companies")
print(f"Fetch Companies: {res.status_code} - Loaded {len(res.json())} companies")

# 3. Read student progress (pre-requisite data exists in DB)
res = requests.get(f"{BASE_URL}/api/students/{student_id}/progress")
print(f"Student Progress: {res.status_code}")
progress = res.json()
print(f"Name: {progress.get('name')}, Risk Score: {progress.get('risk_profile', {}).get('risk_score')}")

# 4. Generate intervention
print("Invoking LangGraph workflow to generate intervention plan...")
res = requests.post(f"{BASE_URL}/api/interventions", json={"student_id": student_id})
print(f"Generate Intervention Code: {res.status_code}")
if res.status_code == 200:
    plan = res.json()
    intervention_id = plan.get("intervention_id")
    print(f"Generated Intervention ID: {intervention_id}")
    print(f"Risk Band: {plan.get('risk_band')}")
    print(f"Status: {plan.get('status')}")
    print(f"Summary: {plan.get('student_summary')}")
    print(f"Priority: {plan.get('priority_level')}")
    print(f"Actions count: {len(plan.get('recommended_actions', []))}")
    print(f"Follow-up: {plan.get('follow_up_plan')}")
    print(f"Tools Executed: {plan.get('tools_called')}")
    
    # 5. Approve intervention
    print(f"Approving intervention {intervention_id} as 'Dr. Sarah Patel'...")
    res_app = requests.post(f"{BASE_URL}/api/interventions/{intervention_id}/approve", json={"approved_by": "Dr. Sarah Patel"})
    print(f"Approve Response: {res_app.status_code} - {res_app.json()}")
    
    # 6. Fetch latest intervention
    print("Fetching latest intervention to check persistence...")
    res_lat = requests.get(f"{BASE_URL}/api/students/{student_id}/interventions/latest")
    print(f"Latest Intervention Status: {res_lat.status_code}")
    latest = res_lat.json()
    print(f"Verified Saved ID: {latest.get('intervention_id')}")
    print(f"Verified Status: {latest.get('status')}")
    print(f"Verified Approved By: {latest.get('approved_by')}")
    print(f"Verified Approved At: {latest.get('approved_at')}")

print("--- End API Verification ---")
