import os
import bcrypt
import secrets
import json
import base64
from datetime import datetime, timezone, timedelta
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from jose import jwt, JWTError
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import (
    ACCESS_TOKEN_SECRET,
    REFRESH_TOKEN_SECRET,
    FCM_TOKEN_SECRET,
    PROFILE_PIC_MEDIA_ENCRYPTION,
    APP_NAME,
    OAUTH_GOOGLE_WEB_CLIENT_ID,
    OAUTH_GOOGLE_ANDROID_CLIENT_ID,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    ACCESS_TOKEN_EXPIRE_SECONDS,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

async def generate_salt() -> str:
    return bcrypt.gensalt(rounds=10).decode("utf-8")

async def generate_pepper() -> str:
    return secrets.token_bytes(16).hex()


async def hash_password(password: str, salt: str) -> str:
    return bcrypt.hashpw(password.encode(), salt.encode()).decode("utf-8")

async def compare_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

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

    access_token  = jwt.encode(access_payload,  ACCESS_TOKEN_SECRET,  algorithm="HS256")
    refresh_token = jwt.encode(refresh_payload, REFRESH_TOKEN_SECRET, algorithm="HS256")
    return {"accessToken": access_token, "refreshToken": refresh_token}


def generate_forgot_password_token(user_id: int, email: str) -> str:
    payload = {
        "userId": user_id,
        "email":  email,
        "exp":    datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, ACCESS_TOKEN_SECRET, algorithm="HS256")


def decode_forgot_password_token(token: str) -> dict:
    try:
        return jwt.decode(token, ACCESS_TOKEN_SECRET, algorithms=["HS256"])
    except JWTError:
        raise ValueError("Invalid or expired token")


async def verify_id_token(id_token_str: str) -> dict:
    try:
        client_ids = [OAUTH_GOOGLE_WEB_CLIENT_ID, OAUTH_GOOGLE_ANDROID_CLIENT_ID]
        payload = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            audience=None,
        )
        if payload.get("aud") not in client_ids:
            raise ValueError("Invalid audience")
        if not payload:
            raise ValueError("Invalid token payload")
        return payload
    except Exception:
        raise ValueError("Failed to verify ID Token")


def generate_otp() -> str:
    import random
    return str(random.randint(100000, 999999))


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


# ── AES Encrypt / Decrypt (FCM token) ─────────────────────────────────────────
def _get_fcm_key() -> bytes:
    return FCM_TOKEN_SECRET.ljust(32, "0")[:32].encode()


def encrypt(text: str) -> str:
    iv  = os.urandom(16)
    key = _get_fcm_key()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    # pad to 16 bytes
    padded = text.encode()
    pad_len = 16 - (len(padded) % 16)
    padded += bytes([pad_len] * pad_len)
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return iv.hex() + ":" + encrypted.hex()


def decrypt(text: str) -> str:
    parts     = text.split(":")
    iv        = bytes.fromhex(parts[0])
    encrypted = bytes.fromhex(":".join(parts[1:]))
    key       = _get_fcm_key()
    cipher    = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(encrypted) + decryptor.finalize()
    pad_len   = decrypted[-1]
    return decrypted[:-pad_len].decode("utf-8")


def _get_media_key() -> bytes:
    return PROFILE_PIC_MEDIA_ENCRYPTION.ljust(32, "0")[:32].encode()


def generate_short_encrypted_url(path: str) -> str | None:
    try:
        key       = _get_media_key()
        timestamp = int(datetime.now().timestamp() * 1000)
        data      = json.dumps({"path": path, "timestamp": timestamp}).encode("utf-8")
        iv        = os.urandom(16)
        cipher    = Cipher(algorithms.AES(key), modes.CTR(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(data) + encryptor.finalize()
        token     = base64.b64encode(iv).decode() + ":" + base64.b64encode(encrypted).decode()
        from urllib.parse import quote
        return f"images?q={quote(token)}"
    except Exception:
        return None


def verify_short_encrypted_url(token: str) -> dict | None:
    if not token:
        return None
    try:
        parts = token.split(":")
        if len(parts) < 2:
            return None
        iv        = base64.b64decode(parts[0])
        encrypted = base64.b64decode(":".join(parts[1:]))
        key       = _get_media_key()
        cipher    = Cipher(algorithms.AES(key), modes.CTR(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted) + decryptor.finalize()
        return json.loads(decrypted.decode("utf-8"))
    except Exception:
        return None