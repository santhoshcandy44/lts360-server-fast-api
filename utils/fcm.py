# utils/fcm_utils.py
import os
import json
import time
import math
import base64
import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from config import FCM_TOKEN_SECRET

_SERVICE_ACCOUNT_PATH = os.path.join(os.path.dirname(__file__), "../config/service_account.json")
with open(_SERVICE_ACCOUNT_PATH, "r") as f:
    _KEY_JSON = json.load(f)

async def get_access_token() -> str:
    audience = "https://oauth2.googleapis.com/token"

    jwt_header = {"alg": "RS256", "typ": "JWT"}
    jwt_claims = {
        "iss":   _KEY_JSON["client_email"],
        "scope": "https://www.googleapis.com/auth/cloud-platform",
        "aud":   audience,
        "exp":   int(time.time()) + 3600,
        "iat":   int(time.time()),
    }

    header_enc = base64.urlsafe_b64encode(json.dumps(jwt_header).encode()).rstrip(b"=").decode()
    claims_enc = base64.urlsafe_b64encode(json.dumps(jwt_claims).encode()).rstrip(b"=").decode()
    signing_input = f"{header_enc}.{claims_enc}"

    private_key = serialization.load_pem_private_key(
        _KEY_JSON["private_key"].encode(),
        password=None,
        backend=default_backend()
    )
    signature = private_key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    signature_enc = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()

    jwt_token = f"{signing_input}.{signature_enc}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion":  jwt_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()["access_token"]


def decode_fcm_token(text: str) -> str:
    parts       = text.split(":")
    iv          = bytes.fromhex(parts[0])
    encrypted   = bytes.fromhex(":".join(parts[1:]))
    key         = FCM_TOKEN_SECRET.ljust(32, "0")[:32].encode()
    cipher      = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor   = cipher.decryptor()
    decrypted   = decryptor.update(encrypted) + decryptor.finalize()
    # remove padding
    pad_len     = decrypted[-1]
    return decrypted[:-pad_len].decode("utf-8")


async def send_fcm_notification(key: str, fcm_token: str, type: str, title: str, data: dict):
    access_token = await get_access_token()
    url          = "https://fcm.googleapis.com/v1/projects/lts360/messages:send"

    payload        = {"type": type, "title": title, "data": data}
    payload_string = json.dumps(payload)
    byte_size      = len(payload_string.encode("utf-8"))

    MAX_PAYLOAD_SIZE = 4 * 1024  # 4 KB

    async with httpx.AsyncClient() as client:

        if byte_size > MAX_PAYLOAD_SIZE:
            parts    = math.ceil(byte_size / MAX_PAYLOAD_SIZE)
            chunks   = [
                {
                    "partNumber": str(i + 1),
                    "totalParts": str(parts),
                    "data":       payload_string[i * MAX_PAYLOAD_SIZE:(i + 1) * MAX_PAYLOAD_SIZE],
                    "key":        key,
                }
                for i in range(parts)
            ]

            responses = []
            for chunk in chunks:
                notification_payload = {
                    "message": {
                        "token": fcm_token,
                        "data":  {
                            "partNumber": chunk["partNumber"],
                            "totalParts": chunk["totalParts"],
                            "data":       chunk["data"],
                            "key":        chunk["key"],
                        },
                        "android": {"priority": "high"},
                    }
                }
                response = await client.post(
                    url,
                    json=notification_payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type":  "application/json",
                    },
                )
                response.raise_for_status()
                responses.append(response.json())

            return responses

        else:
            notification_payload = {
                "message": {
                    "token": fcm_token,
                    "data":  {
                        "partNumber": "1",
                        "totalParts": "1",
                        "data":       payload_string,
                        "key":        key,
                    },
                    "android": {"priority": "high"},
                }
            }
            response = await client.post(
                url,
                json=notification_payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type":  "application/json",
                },
            )
            response.raise_for_status()
            return response.json()