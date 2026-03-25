import asyncio
import smtplib
import time
from typing import Any, Optional
from datetime import datetime, timezone, timedelta

_store: dict[str, tuple[Any, Optional[float]]] = {}
_lock = asyncio.Lock()

from jose import jwt, JWTError

async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    expires_at = time.monotonic() + ttl if ttl is not None else None
    async with _lock:
        _store[key] = (value, expires_at)

async def cache_get(key: str) -> Optional[Any]:
    async with _lock:
        entry = _store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and time.monotonic() > expires_at:
            del _store[key]
            return None
        return value


async def cache_delete(key: str) -> None:
    async with _lock:
        _store.pop(key, None)
 
from config import (
    ACCESS_TOKEN_EXPIRE_SECONDS,
    ACCESS_TOKEN_SECRET,
    ALGORITHM,
    APP_NAME,
    REFRESH_TOKEN_EXPIRE_DAYS,
    REFRESH_TOKEN_SECRET,
    SMTP_HOST,    
    SMTP_PORT,
    SMTP_USER,      
    SMTP_PASSWORD  
)

async def send_otp_email(email: str, otp: str) -> dict:
    try:
        current_year = datetime.now().year
        html_content = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: 'Helvetica', 'Arial', sans-serif; background-color: #f7f7f7; margin: 0; padding: 0; color: #333; }}
                    .email-wrapper {{ width: 100%; max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); }}
                    .header {{ background-color: #007bff; color: #ffffff; text-align: center; padding: 20px; border-radius: 8px 8px 0 0; font-size: 24px; font-weight: 600; }}
                    .content {{ padding: 30px; text-align: center; font-size: 14px; color: #555; }}
                    .otp-code {{ font-size: 32px; font-weight: bold; color: #ffffff; background-color: #007bff; padding: 15px 25px; border-radius: 8px; display: inline-block; margin-top: 20px; }}
                    .footer {{ text-align: center; font-size: 12px; color: #999; padding: 20px 0; }}
                    .footer a {{ color: #007bff; text-decoration: none; }}
                </style>
            </head>
            <body>
                <div class="email-wrapper">
                    <div class="header">OTP Verification</div>
                    <div class="content">
                        <p><span style="font-size: 24px; font-weight: bold;">Hello from, </span>
                           <span style="font-size: 28px; font-weight: bold; color: #007bff;">{APP_NAME}</span>
                        </p>
                        <p>We received a request to verify your account. Please use the following OTP code:</p>
                        <div class="otp-code">{otp}</div>
                        <p>The OTP will expire in 15 minutes.</p>
                        <p>If you did not request this, please ignore this email.</p>
                    </div>
                    <div class="footer" style="padding:8px">
                        <p>For any issues, contact us at <a href="mailto:support@lts360.com">support@lts360.com</a></p>
                        <p>&copy; {current_year} {APP_NAME}. All Rights Reserved.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "OTP Verification"
        msg["From"]    = "noreply-verification@lts360.com"
        msg["To"]      = email
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(SMTP_HOST, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(msg["From"], [email], msg.as_string())

        return {"success": True, "message": "OTP sent successfully"}
    except Exception as e:
        return {"success": False, "message": "Failed to send OTP email", "error": str(e)}

def generate_tokens(user_id: int, email: str, sign_up_method: str, last_sign_in, role: str = "User") -> dict:
    payload = {
        "sub":          str(user_id),
        "userId":       user_id,
        "email":        email,
        "lastSignIn":   str(last_sign_in),
        "signUpMethod": sign_up_method,
        "role":         role,
    }
    access_payload  = {**payload, "exp": datetime.now(timezone.utc) + timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS)}
    refresh_payload = {**payload, "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)}

    access_token  = jwt.encode(access_payload,  ACCESS_TOKEN_SECRET,  algorithm=ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, REFRESH_TOKEN_SECRET, algorithm=ALGORITHM)
    return access_token , refresh_token
