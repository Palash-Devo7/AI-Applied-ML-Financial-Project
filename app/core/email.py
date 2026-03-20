"""Email sending via Resend."""
import structlog
import resend

from app.config import get_settings

logger = structlog.get_logger(__name__)


def send_verification_email(to_email: str, token: str) -> bool:
    """Send email verification link. Returns True on success."""
    settings = get_settings()
    if not settings.resend_api_key:
        logger.warning("resend_api_key_not_set_email_skipped")
        return False

    resend.api_key = settings.resend_api_key
    verify_url = f"{settings.frontend_url}/auth/verify?token={token}"

    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
        <h1 style="font-size: 24px; font-weight: 700; color: #0f0f17; margin-bottom: 8px;">
            Verify your email
        </h1>
        <p style="color: #6b7280; font-size: 15px; margin-bottom: 24px;">
            Thanks for signing up for QuantCortex. Click the button below to verify your email address.
        </p>
        <a href="{verify_url}"
           style="display: inline-block; background: #4f46e5; color: #fff;
                  padding: 12px 24px; border-radius: 8px; text-decoration: none;
                  font-weight: 600; font-size: 15px;">
            Verify Email
        </a>
        <p style="color: #9ca3af; font-size: 13px; margin-top: 24px;">
            This link expires in 24 hours. If you didn't create an account, ignore this email.
        </p>
        <p style="color: #9ca3af; font-size: 13px;">
            Or copy this link: <br/>
            <span style="color: #4f46e5;">{verify_url}</span>
        </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": to_email,
            "subject": "Verify your QuantCortex account",
            "html": html,
        })
        logger.info("verification_email_sent", email=to_email[:3] + "***")
        return True
    except Exception as e:
        logger.error("verification_email_failed", error=str(e))
        return False


def send_welcome_email(to_email: str) -> bool:
    """Send welcome email after successful verification."""
    settings = get_settings()
    if not settings.resend_api_key:
        return False

    resend.api_key = settings.resend_api_key

    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
        <h1 style="font-size: 24px; font-weight: 700; color: #0f0f17; margin-bottom: 8px;">
            Welcome to QuantCortex
        </h1>
        <p style="color: #6b7280; font-size: 15px; margin-bottom: 24px;">
            Your account is verified. You have <strong>10 free credits per day</strong> to explore
            AI-powered research on BSE-listed Indian companies.
        </p>
        <a href="{settings.frontend_url}"
           style="display: inline-block; background: #4f46e5; color: #fff;
                  padding: 12px 24px; border-radius: 8px; text-decoration: none;
                  font-weight: 600; font-size: 15px;">
            Start researching
        </a>
        <p style="color: #9ca3af; font-size: 13px; margin-top: 24px;">
            Try searching for TATASTEEL, RELIANCE, or INFY to get started.
        </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": to_email,
            "subject": "Welcome to QuantCortex — you're all set",
            "html": html,
        })
        return True
    except Exception as e:
        logger.error("welcome_email_failed", error=str(e))
        return False
