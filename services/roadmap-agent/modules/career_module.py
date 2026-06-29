from agents.roadmap_agent import ask_gemini_text


def generate_career_guidance(gpa: float, interest: str):
    recommendations = {
        "AI": ["Python", "Machine Learning", "Deep Learning"],
        "Web Development": ["HTML/CSS", "React", "Node.js"],
        "Cybersecurity": ["Networking", "Linux", "Ethical Hacking"],
        "Data Science": ["Python", "SQL", "Statistics"],
    }

    skills = recommendations.get(
        interest,
        ["Python", "Communication", "Problem Solving"]
    )

    prompt = f"""
You are an experienced career mentor for engineering students.

Student GPA: {gpa}
Career Interest: {interest}
Suggested Skills: {skills}

Create career guidance in clean MARKDOWN format.

Rules:
- Do not return JSON.
- Do not write one long paragraph.
- Use clear headings.
- Use short bullet points.
- Keep it practical and motivating.
- Mention the student's GPA respectfully, not negatively.
- Give actionable next steps.
- Keep the total response between 500 and 700 words.

Return exactly in this format:

# 🎯 Career Summary

# ✅ Why This Field Suits You

# 🧠 Core Skills to Learn

# 🗓️ 8-Week Learning Roadmap

# 🚀 Projects to Build

# 📚 Certifications / Courses

# 💼 Internship Preparation Advice

# 🌟 Final Motivation
"""

    return ask_gemini_text(prompt)