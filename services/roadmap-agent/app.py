from modules.roadmap_generator import generate_improvement_roadmap
from modules.career_module import generate_career_guidance

student_id = "S1001"

roadmap_result = generate_improvement_roadmap(student_id)

career_guidance = generate_career_guidance(
    gpa=7.4,
    interest="AI"
)

print("\n===== RISK PROFILE =====\n")
print(roadmap_result["risk_profile"])

print("\n===== PERSONALIZED IMPROVEMENT ROADMAP =====\n")
print(roadmap_result["roadmap"])

print("\n===== ROADMAP VALIDATION =====\n")
print(roadmap_result["validation"])

print("\n===== CAREER READINESS GUIDANCE =====\n")
print(career_guidance)