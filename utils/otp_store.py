from datetime import datetime, timedelta

# In-memory store
_otp_store: dict[str, dict] = {}

async def save_otp(key: str, otp: str, email: str, expires_minutes: int = 15):
    _otp_store[key] = {
        "otp": otp,
        "email": email,
        "expires_at": datetime.utcnow() + timedelta(minutes=expires_minutes)
    }

async def get_otp(key: str):
    data = _otp_store.get(key)
    if not data:
        return None
    if datetime.utcnow() > data["expires_at"]:
        del _otp_store[key]
        return None
    return data

async def delete_otp(key: str):
    _otp_store.pop(key, None)

async def is_expired(key: str) -> bool:
    return await get_otp(key) is None