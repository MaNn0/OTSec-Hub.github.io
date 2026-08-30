import httpx
import os
from fastapi import HTTPException, status

#captcha : gets real cloudflare secret or fallbacks to "always pass"
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY") or "1x0000000000000000000000000000000AA"
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

async def verify_turnstile_token(token: str, remote_ip: str = None) -> bool:
    """Verifies the Turnstile CAPTCHA token directly with Cloudflare."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAPTCHA verification failed: Token missing."
        )

    payload = {
        "secret": TURNSTILE_SECRET_KEY,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(TURNSTILE_VERIFY_URL, data=payload, timeout=5.0)
            result = response.json()
            
            if not result.get("success"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CAPTCHA verification failed: Invalid or expired token."
                )
            return True
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="CAPTCHA verification service currently unavailable."
            )