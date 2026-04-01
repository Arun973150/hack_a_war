"""
Alert notification endpoints — Slack webhook and email via Gmail SMTP.
"""
import structlog
import httpx
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from config import settings

logger = structlog.get_logger()
router = APIRouter()


class SlackAlertRequest(BaseModel):
    regulation_title: str
    regulation_id: str
    jurisdiction: str
    risk_score: int
    severity: str
    impact_summary: str
    gaps_count: int
    webhook_url: Optional[str] = None  # override from env if provided


class EmailAlertRequest(BaseModel):
    regulation_title: str
    regulation_id: str
    jurisdiction: str
    risk_score: int
    severity: str
    impact_summary: str
    recipient_email: str


SEVERITY_EMOJI = {
    "Critical": "🔴",
    "High": "🟠",
    "Medium": "🟡",
    "Low": "🟢",
}

RISK_COLOR = {
    "Critical": "#E5484D",
    "High": "#F59E0B",
    "Medium": "#8B5CF6",
    "Low": "#22C55E",
}


@router.post("/slack")
async def send_slack_alert(request: SlackAlertRequest):
    """Send a regulatory alert to Slack via webhook."""
    webhook_url = request.webhook_url or getattr(settings, "slack_webhook_url", None)

    if not webhook_url:
        # No webhook configured — return success with note (demo mode)
        logger.info("slack_alert_demo_mode", regulation_id=request.regulation_id)
        return {
            "sent": True,
            "demo_mode": True,
            "message": "Slack webhook not configured — alert logged",
            "regulation_id": request.regulation_id,
        }

    emoji = SEVERITY_EMOJI.get(request.severity, "⚪")
    color = RISK_COLOR.get(request.severity, "#888")

    payload = {
        "text": f"{emoji} *New Regulatory Alert — Red Forge*",
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                f"*{request.regulation_title}*\n"
                                f"Jurisdiction: `{request.jurisdiction}` · "
                                f"Risk Score: `{request.risk_score}/10` · "
                                f"Severity: `{request.severity}`\n\n"
                                f"{request.impact_summary}"
                            ),
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {"type": "mrkdwn", "text": f"ID: `{request.regulation_id}` · {request.gaps_count} gaps detected · via Red Forge"},
                        ],
                    },
                ],
            }
        ],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(webhook_url, json=payload, timeout=10)
        if resp.status_code != 200:
            raise HTTPException(502, f"Slack webhook returned {resp.status_code}: {resp.text}")

    logger.info("slack_alert_sent", regulation_id=request.regulation_id, risk=request.risk_score)
    return {"sent": True, "regulation_id": request.regulation_id}


@router.post("/email")
async def send_email_alert(request: EmailAlertRequest):
    """Send email alert via Gmail SMTP using app password."""
    sender = settings.smtp_sender_email
    app_password = settings.smtp_app_password

    if not sender or not app_password:
        logger.info("email_alert_demo_mode", regulation_id=request.regulation_id)
        return {
            "sent": True,
            "demo_mode": True,
            "message": "Gmail SMTP not configured — alert logged",
            "recipient": request.recipient_email,
        }

    try:
        emoji = SEVERITY_EMOJI.get(request.severity, "⚪")
        subject = f"{emoji} [{request.severity}] Regulatory Alert — {request.regulation_title}"

        html_body = f"""
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#0D0D12;color:#EDEDEF;padding:32px;border-radius:12px">
  <h2 style="margin:0 0 8px;font-size:20px;color:#EDEDEF">{request.regulation_title}</h2>
  <div style="display:flex;gap:12px;margin-bottom:20px">
    <span style="background:#E5484D22;color:#E5484D;border:1px solid #E5484D44;padding:3px 10px;border-radius:20px;font-size:13px;font-weight:600">{request.severity}</span>
    <span style="background:#ffffff11;color:#8B8D97;padding:3px 10px;border-radius:20px;font-size:13px">{request.jurisdiction}</span>
  </div>
  <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
    <tr>
      <td style="padding:12px;background:#ffffff08;border:1px solid #ffffff12;border-radius:8px;text-align:center">
        <div style="font-size:28px;font-weight:700;color:#E5484D;font-family:monospace">{request.risk_score}/10</div>
        <div style="font-size:11px;color:#4A4C57;text-transform:uppercase;letter-spacing:.04em">Risk Score</div>
      </td>
    </tr>
  </table>
  <p style="color:#8B8D97;line-height:1.6;margin:0 0 20px">{request.impact_summary}</p>
  <hr style="border:none;border-top:1px solid #ffffff12;margin:20px 0">
  <p style="font-size:11px;color:#4A4C57;margin:0">Sent by Red Forge · Regulation ID: <code style="font-family:monospace">{request.regulation_id}</code></p>
</div>
"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = request.recipient_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, app_password)
            server.sendmail(sender, request.recipient_email, msg.as_string())

        logger.info("email_alert_sent", regulation_id=request.regulation_id, to=request.recipient_email)
        return {"sent": True, "recipient": request.recipient_email}

    except Exception as e:
        logger.error("email_alert_failed", error=str(e))
        return {"sent": False, "error": str(e)}
