# Faculty Dashboard API — Setup Guide (for Person D)

Steps to get the Faculty Dashboard API running locally so you can test against it.

---

## Step 1 — Get the code

```bash
git fetch origin
git checkout feature/student-dashboard
git pull origin feature/student-dashboard
```

---

## Step 2 — Project Structure

```text
student_dashboard/
├── datasets/
│   └── student_success_dataset_30000.csv
├── docs/
├── pages/
├── research/
├── services/
│   └── dashboard/
│       └── api.py          ← the API you need
├── app.py
├── database.py
├── dashboard.db
├── requirements.txt
└── utils.py
```

---

## Step 3 — Install Dependencies

From the project root (`student_dashboard/`):

```bash
pip install -r requirements.txt
```

If that doesn't cover it, install directly:

```bash
pip install fastapi uvicorn
```

---

## Step 4 — Start the API

From the project root:

```bash
cd services/dashboard
uvicorn api:app --port 8002
```

---

## Step 5 — Verify It's Running

Open in browser:

```
http://127.0.0.1:8002/docs
```

Or check health directly:

```
http://127.0.0.1:8002/health
```

Expected response:
```json
{"status": "ok", "service": "dashboard-api"}
```

---

## Step 6 — Test the Endpoint You'll Use

```
GET http://127.0.0.1:8002/intervention/{student_id}
```

Example:
```
GET http://127.0.0.1:8002/intervention/STU202600001
```

Returns the latest **approved** intervention plan for that student, or a 404 if none exists yet.

---

## Notes

- `dashboard.db` is already included in the branch — no need to run `database.py` yourself unless it's missing.
- Only `status = approved` plans are ever returned — pending or rejected plans are never visible through this API.
- Full field reference and response format: see `faculty_dashboard_api_for_person_d.md`.