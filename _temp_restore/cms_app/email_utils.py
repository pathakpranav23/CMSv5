import smtplib
from email.message import EmailMessage
from flask import current_app


def send_email(subject: str, to_address: str, text_body: str, html_body: str = None) -> bool:
    """Send an email using SMTP settings from Flask app config.

    Expected config keys:
      MAIL_HOST, MAIL_PORT, MAIL_USER, MAIL_PASSWORD, MAIL_FROM,
      MAIL_USE_TLS (default True), MAIL_USE_SSL (default False)
    """
    cfg = current_app.config
    host = cfg.get("MAIL_HOST")
    port = int(cfg.get("MAIL_PORT", 587))
    user = cfg.get("MAIL_USER")
    password = cfg.get("MAIL_PASSWORD")
    mail_from = cfg.get("MAIL_FROM") or user or "noreply@example.com"
    use_tls = bool(cfg.get("MAIL_USE_TLS", True))
    use_ssl = bool(cfg.get("MAIL_USE_SSL", False))

    if not host:
        current_app.logger.warning("MAIL_HOST not configured; skipping email send.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = to_address
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port) as server:
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port) as server:
                if use_tls:
                    server.starttls()
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email to {to_address}: {e}")
        return False