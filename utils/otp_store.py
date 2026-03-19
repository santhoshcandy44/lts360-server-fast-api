import redis.asyncio as redis
import json
from config import REDIS_URL

r = redis.from_url(REDIS_URL)

async def save_otp(key: str, otp: str, email: str, expires_minutes: int = 15):
    data = {"otp": otp, "email": email}
    await r.setex(key, expires_minutes * 60, json.dumps(data))

async def get_otp(key: str):
    val = await r.get(key)
    return json.loads(val) if val else None

async def delete_otp(key: str):
    await r.delete(key)

async def is_expired(key: str) -> bool:
    return not await r.exists(key)