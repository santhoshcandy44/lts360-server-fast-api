import json
import asyncio
from aiokafka import AIOKafkaConsumer
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.database import AsyncSessionLocal
from models.user import User, FCMToken
from utils.fcm import send_fcm_notification, decode_fcm_token
from config.config import PROFILE_BASE_URL

async def start_local_job_notifications_consumer():
    consumer = AIOKafkaConsumer(
        "local-job-application-notifications",
        bootstrap_servers="localhost:9092",
        group_id="notification-group",
        auto_offset_reset="latest",
    )

    await consumer.start()
    print("Kafka: start_local_job_notifications_consumer started running")

    try:
        async for message in consumer:
            try:
                payload     = json.loads(message.value.decode())
                user_id     = payload["user_id"]
                candidate_id = payload["candidate_id"]
                applicant_id = payload["applicant_id"]
                local_job_title = payload["local_job_title"]

                async with AsyncSessionLocal() as db:
                    fcm_token = await db.scalar(
                        select(FCMToken.fcm_token)
                        .where(FCMToken.user_id == user_id)
                    )

                    candidate = await db.scalar(
                        select(User)
                        .options(selectinload(User.location))
                        .where(User.user_id == candidate_id)
                    )

                if fcm_token and candidate:
                    data = {
                        "applicant_id":   applicant_id,
                        "local_job_title": local_job_title,
                        "user": {
                            "user_id":              candidate.user_id,
                            "first_name":           candidate.first_name,
                            "last_name":            candidate.last_name,
                            "about":                candidate.about,
                            "email":                candidate.email,
                            "is_email_verified":    bool(candidate.is_email_verified),
                            "phone_country_code":   candidate.phone_country_code,
                            "phone_number":         candidate.phone_number,
                            "is_phone_verified":    bool(candidate.is_phone_verified),
                            "profile_pic_url":      f"{PROFILE_BASE_URL}/{candidate.profile_pic_url}" if candidate.profile_pic_url else None,
                            "profile_pic_url_96x96": f"{PROFILE_BASE_URL}/{candidate.profile_pic_url_96x96}" if candidate.profile_pic_url_96x96 else None,
                            "account_type":         candidate.account_type,
                            "created_at":           str(candidate.created_at.year) if candidate.created_at else None,
                            "location": {
                                "latitude":      float(candidate.location.latitude),
                                "longitude":     float(candidate.location.longitude),
                                "geo":           candidate.location.geo,
                                "location_type": candidate.location.location_type,
                                "updated_at":    str(candidate.location.updated_at),
                            } if candidate.location else None,
                        }
                    }

                    decoded_token = decode_fcm_token(fcm_token)
                    await send_fcm_notification(
                        f"business_local_job_application:{user_id}:{applicant_id}",
                        decoded_token,
                        "business_local_job_application",
                        "Someone applied local job",
                        json.dumps(data)
                    )

            except Exception as e:
                print(f"Error processing message: {e}")

    finally:
        await consumer.stop()


async def start_consumers():
    asyncio.create_task(start_local_job_notifications_consumer())