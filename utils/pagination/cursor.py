# utils/pagination/cursor.py
import json
import hmac
import hashlib
import secrets
from typing import Optional

BASE62_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
SECRET       = "super_secret_key"

# ── Base62 encode / decode ────────────────────────────────────────────────────
def _base62_encode(data: bytes) -> str:
    num = int.from_bytes(data, "big")
    if num == 0:
        return BASE62_CHARS[0]
    result = []
    while num:
        result.append(BASE62_CHARS[num % 62])
        num //= 62
    return "".join(reversed(result))


def _base62_decode(s: str) -> bytes:
    num = 0
    for char in s:
        num = num * 62 + BASE62_CHARS.index(char)
    length = (num.bit_length() + 7) // 8
    return num.to_bytes(length, "big")


# ── Encode cursor ─────────────────────────────────────────────────────────────
def encode_cursor(obj: dict) -> str:
    json_bytes = json.dumps(obj, separators=(",", ":")).encode("utf-8")

    # first 6 bytes of HMAC-SHA256
    sig = hmac.new(SECRET.encode(), json_bytes, hashlib.sha256).digest()[:6]

    payload = json_bytes + sig
    return _base62_encode(payload)


# ── Decode cursor ─────────────────────────────────────────────────────────────
def decode_cursor(cursor: str) -> Optional[dict]:
    try:
        payload   = _base62_decode(cursor)
        json_part = payload[:-6]
        sig_part  = payload[-6:]

        expected = hmac.new(SECRET.encode(), json_part, hashlib.sha256).digest()[:6]

        # timing safe comparison — same as crypto.timingSafeEqual
        if not secrets.compare_digest(sig_part, expected):
            return None

        return json.loads(json_part.decode("utf-8"))
    except Exception:
        return None