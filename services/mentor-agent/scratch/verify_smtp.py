import os
import sys
from dotenv import load_dotenv

# Load env variables
load_dotenv(override=True)

# Add mentor-agent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_smtp():
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SENDER_EMAIL", "successpath-alerts@spit.ac.in")
    
    print("--- SMTP Diagnostics ---")
    print(f"SMTP_HOST: {smtp_host}")
    print(f"SMTP_PORT: {smtp_port}")
    print(f"SMTP_USER: {smtp_user}")
    print(f"SMTP_PASSWORD raw length: {len(smtp_password) if smtp_password else 0}")
    print(f"SENDER_EMAIL: {sender_email}")
    
    if not all([smtp_host, smtp_port, smtp_user, smtp_password]):
        print("Error: Missing one or more SMTP environment variables.")
        return
        
    # Clean the password the same way database.py does
    cleaned_password = smtp_password
    if "#" in cleaned_password:
        cleaned_password = cleaned_password.split("#")[0]
    cleaned_password = cleaned_password.replace(" ", "").strip()
    
    print(f"Cleaned Password length: {len(cleaned_password)}")
    
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
        
        # Try sending a test email to the user themselves
        print(f"Sending test email to {smtp_user}...")
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "SuccessPath SMTP Connection Test"
        msg['From'] = sender_email
        msg['To'] = smtp_user
        
        html = "<p>Congratulations! Your SuccessPath SMTP outreach client is working perfectly.</p>"
        msg.attach(MIMEText(html, 'html'))
        
        server.sendmail(sender_email, smtp_user, msg.as_string())
        server.quit()
        print("Test email sent successfully!")
        
    except Exception as e:
        print(f"\nSMTP Test Failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_smtp()
