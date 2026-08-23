import os
import sys
from dotenv import load_dotenv

# Load env variables
load_dotenv(override=True)

# Add mentor-agent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_real_send():
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SENDER_EMAIL", "successpath-alerts@spit.ac.in")
    
    # Target student email
    student_email = "aishwarya.gusinge25@spit.ac.in"
    student_name = "Sakshi Patil"
    faculty_name = "Dr. Sharma"
    actions = ["Maintain current study habits", "Attend all classes"]
    
    print("--- SMTP Real Send Diagnostics ---")
    print(f"SMTP_HOST: {smtp_host}")
    print(f"SMTP_PORT: {smtp_port}")
    print(f"SMTP_USER: {smtp_user}")
    print(f"SENDER_EMAIL: {sender_email}")
    print(f"To Student Email: {student_email}")
    
    if not all([smtp_host, smtp_port, smtp_user, smtp_password]):
        print("Error: Missing one or more SMTP environment variables.")
        return
        
    cleaned_password = smtp_password
    if "#" in cleaned_password:
        cleaned_password = cleaned_password.split("#")[0]
    cleaned_password = cleaned_password.replace(" ", "").strip()
    
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    try:
        print("Connecting to SMTP server...")
        server = smtplib.SMTP(smtp_host, int(smtp_port))
        print("SMTP server connected. Starting TLS...")
        server.starttls()
        print("TLS started. Attempting login...")
        server.login(smtp_user, cleaned_password)
        print("Login successful!")
        
        print(f"Building and sending email to {student_email}...")
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Academic Intervention Plan Approved - SuccessPath"
        msg['From'] = sender_email
        msg['To'] = student_email
        
        actions_li = "".join(f"<li>{action}</li>" for action in actions)
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333333; max-width: 600px; margin: 0 auto; border: 1px solid #dddddd; padding: 20px; border-radius: 8px;">
            <h2>SuccessPath Test</h2>
            <p>Dear {student_name},</p>
            <p>Your academic advisor, {faculty_name}, has approved your intervention plan.</p>
            <ul>{actions_li}</ul>
          </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))
        
        server.sendmail(sender_email, student_email, msg.as_string())
        server.quit()
        print("Real email sent successfully!")
        
    except Exception as e:
        print(f"\nSMTP Real Send Failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_real_send()
