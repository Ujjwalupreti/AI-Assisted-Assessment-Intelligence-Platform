"""
Email Service for QIS Platform.
Handles transactional emails including Email Verification and Password Reset.
Supports SMTP with TLS, with graceful fallback to local development outbox file logging.
"""

import os
import smtplib
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Optional, Dict, Any, List

class EmailService:
    def __init__(self):
        self.host = os.environ.get('EMAIL_HOST', '')
        self.port = int(os.environ.get('EMAIL_PORT', '587'))
        self.username = os.environ.get('EMAIL_USERNAME', '')
        self.password = os.environ.get('EMAIL_PASSWORD', '')
        self.sender = os.environ.get('EMAIL_FROM', 'no-reply@qis-assessment.com')
        self.use_tls = os.environ.get('EMAIL_USE_TLS', 'true').lower() in ('true', '1')
        self.frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:5173').rstrip('/')

        # Outbox log path for development & testing verification
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.outbox_dir = os.path.join(self.base_dir, 'instance')
        os.makedirs(self.outbox_dir, exist_ok=True)
        self.outbox_file = os.path.join(self.outbox_dir, 'mail_outbox.jsonl')

    def is_configured(self) -> bool:
        """Check if live SMTP credentials are configured."""
        return bool(self.host and self.username and self.password)

    def _log_to_dev_outbox(self, email_type: str, recipient: str, subject: str, link: str, metadata: Optional[Dict[str, Any]] = None):
        """Record dispatched email into local development outbox file for testing and inspection."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": email_type,
            "recipient": recipient,
            "subject": subject,
            "link": link,
            "metadata": metadata or {}
        }
        try:
            with open(self.outbox_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"[EmailService Outbox Error] Could not write to outbox: {e}")

        print(f"\n[DEV MAIL OUTBOX] [{email_type}] To: {recipient}")
        print(f"  Subject: {subject}")
        print(f"  Action Link: {link}\n")

    def send_email(self, to_email: str, subject: str, html_content: str, text_content: str) -> bool:
        """Send email via SMTP if configured, otherwise dispatch to dev outbox."""
        if not self.is_configured():
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender
            msg["To"] = to_email

            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            msg.attach(part1)
            msg.attach(part2)

            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.sender, [to_email], msg.as_string())
            return True
        except Exception as e:
            print(f"[EmailService Error] Failed to send email via SMTP to {to_email}: {e}")
            return False

    def send_verification_email(self, recipient_email: str, recipient_name: str, token: str) -> bool:
        """Generate and send account email verification message."""
        verify_url = f"{self.frontend_url}/verify-email?token={token}"
        display_name = recipient_name or recipient_email.split('@')[0]
        subject = "Verify Your QIS Account"

        text_content = f"""Hello {display_name},

Thank you for registering on the QIS AI-Assisted Assessment Intelligence Platform.

Please verify your email address by visiting the following link:
{verify_url}

This verification link will expire in 24 hours.

If you did not create this account, no action is needed.

Best regards,
The QIS Team
"""

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 20px; }}
    .card {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
    .header {{ text-align: center; margin-bottom: 24px; }}
    .logo {{ font-size: 20px; font-weight: 700; color: #2563eb; }}
    .title {{ font-size: 18px; font-weight: 600; margin: 16px 0 8px; color: #0f172a; }}
    .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff !important; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; margin: 20px 0; }}
    .footer {{ font-size: 12px; color: #64748b; margin-top: 24px; border-top: 1px solid #e2e8f0; padding-top: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="logo">QIS Platform</div>
      <div class="title">Verify Your Email Address</div>
    </div>
    <p>Hello <strong>{display_name}</strong>,</p>
    <p>Welcome to the <strong>AI-Assisted Assessment Intelligence Platform</strong>. Please confirm your email address by clicking the button below:</p>
    <div style="text-align: center;">
      <a href="{verify_url}" class="btn" target="_blank">Verify Email Address</a>
    </div>
    <p style="font-size: 13px; color: #64748b;">Or copy and paste this link into your browser:<br>
      <a href="{verify_url}" style="color: #2563eb; word-break: break-all;">{verify_url}</a>
    </p>
    <p style="font-size: 13px; color: #64748b;">This link will expire in 24 hours. If you did not create an account, you can safely ignore this email.</p>
    <div class="footer">
      &copy; {datetime.utcnow().year} QIS Platform &bull; Automated Assessment & Proctoring System
    </div>
  </div>
</body>
</html>
"""

        # Log to local dev outbox for audit and testing
        self._log_to_dev_outbox("VERIFICATION", recipient_email, subject, verify_url, {"token": token})
        return self.send_email(recipient_email, subject, html_content, text_content)

    def send_password_reset_email(self, recipient_email: str, recipient_name: str, token: str) -> bool:
        """Generate and send password reset recovery link."""
        reset_url = f"{self.frontend_url}/reset-password?token={token}"
        display_name = recipient_name or recipient_email.split('@')[0]
        subject = "Reset Your QIS Password"

        text_content = f"""Hello {display_name},

A password reset request was received for your QIS Platform account.

To reset your password, please open the following link:
{reset_url}

This link is valid for 1 hour and can only be used once.

If you did not request a password reset, please ignore this email or review your account security immediately.

Best regards,
The QIS Team
"""

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 20px; }}
    .card {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
    .header {{ text-align: center; margin-bottom: 24px; }}
    .logo {{ font-size: 20px; font-weight: 700; color: #2563eb; }}
    .title {{ font-size: 18px; font-weight: 600; margin: 16px 0 8px; color: #0f172a; }}
    .btn {{ display: inline-block; background-color: #dc2626; color: #ffffff !important; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; margin: 20px 0; }}
    .footer {{ font-size: 12px; color: #64748b; margin-top: 24px; border-top: 1px solid #e2e8f0; padding-top: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="logo">QIS Platform</div>
      <div class="title">Password Reset Request</div>
    </div>
    <p>Hello <strong>{display_name}</strong>,</p>
    <p>We received a request to reset your password for your QIS account. Click the button below to choose a new password:</p>
    <div style="text-align: center;">
      <a href="{reset_url}" class="btn" target="_blank">Reset Password</a>
    </div>
    <p style="font-size: 13px; color: #64748b;">Or copy and paste this link into your browser:<br>
      <a href="{reset_url}" style="color: #2563eb; word-break: break-all;">{reset_url}</a>
    </p>
    <p style="font-size: 13px; color: #64748b;">This link will expire in <strong>1 hour</strong> and can only be used once. If you did not request this, your account is still secure and you may safely disregard this message.</p>
    <div class="footer">
      &copy; {datetime.utcnow().year} QIS Platform &bull; Automated Assessment & Proctoring System
    </div>
  </div>
</body>
</html>
"""

        # Log to local dev outbox for audit and testing
        self._log_to_dev_outbox("PASSWORD_RESET", recipient_email, subject, reset_url, {"token": token})
        return self.send_email(recipient_email, subject, html_content, text_content)

# Global singleton email service
email_service = EmailService()

