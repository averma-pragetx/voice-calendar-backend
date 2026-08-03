"""
Twilio status callback: hit after each outbound SMS with delivery status
(queued/sent/delivered/failed). Register this URL as the StatusCallback
on the Twilio number / in send_sms if you want per-message tracking.
"""
import logging

from fastapi import APIRouter, Request

logger = logging.getLogger("sms_webhook")

router = APIRouter(prefix="/api/sms", tags=["twilio-sms-webhook"])


@router.post("/webhook")
async def sms_status_callback(request: Request):
    # ponytail: no X-Twilio-Signature validation, add if this becomes attack-relevant
    form = await request.form()
    logger.info(
        "SMS status: sid=%s status=%s to=%s error=%s",
        form.get("MessageSid"), form.get("MessageStatus"), form.get("To"), form.get("ErrorCode"),
    )
    return {"status": "ok"}
