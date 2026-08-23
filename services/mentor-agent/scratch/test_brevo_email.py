import os
import sys
from dotenv import load_dotenv

# Load updated .env file
load_dotenv(override=True)

# Add mentor-agent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import send_outreach_email

def test_brevo():
    brevo_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("SENDER_EMAIL")
    
    print("--- Brevo API Diagnostics ---")
    print(f"BREVO_API_KEY Configured: {'Yes' if brevo_key else 'No'}")
    print(f"SENDER_EMAIL: {sender_email}")
    
    # We will send a test email to the user's/student's email address
    student_email = "aishwarya.gusinge25@spit.ac.in"
    student_name = "Test Student"
    faculty_name = "SuccessPath Admin"
    actions = ["Verify Brevo Integration", "Test Render Email Outreach"]
    
    print(f"Attempting to send email to: {student_email}")
    
    success, message = send_outreach_email(
        student_email=student_email,
        student_name=student_name,
        faculty_name=faculty_name,
        actions=actions
    )
    
    print("\n--- Result ---")
    print(f"Success: {success}")
    print(f"Message: {message}")

if __name__ == "__main__":
    test_brevo()
