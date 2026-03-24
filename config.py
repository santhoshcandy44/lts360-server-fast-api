# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # load .env once here — no need to call it anywhere else

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
JOB_DATABASE_URL = os.getenv("JOB_DATABASE_URL")

# ── App ──────────────────────────────────────────────────────────────────────
APP_NAME    = os.getenv("APP_NAME", "FastAPI App")
DEBUG       = os.getenv("DEBUG", "false").lower() == "true"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

# Auth extras
ACCESS_TOKEN_SECRET  = os.getenv("ACCESS_TOKEN_SECRET")
ALGORITHM            = os.getenv("ALGORITHM", "HS256")

REFRESH_TOKEN_SECRET          = os.getenv("REFRESH_TOKEN_SECRET")
FORGOT_PASSWORD_TOKEN_SECRET  = os.getenv("ACCESS_TOKEN_SECRET")
ACCESS_TOKEN_EXPIRE_SECONDS = int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", "60"))
REFRESH_TOKEN_EXPIRE_DAYS   = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "90"))
GOOGLE_CLIENT_ID              = os.getenv("GOOGLE_CLIENT_ID")


BASE_URL =  os.getenv("BASE_URL")
PROFILE_BASE_URL              = os.getenv("PROFILE_BASE_URL")
MEDIA_BASE_URL =  os.getenv("MEDIA_BASE_URL")

# Google OAuth
OAUTH_GOOGLE_WEB_CLIENT_ID      = os.getenv("OAUTH_GOOGLE_WEB_CLIENT_ID")
OAUTH_GOOGLE_ANDROID_CLIENT_ID  = os.getenv("OAUTH_GOOGLE_ANDROID_CLIENT_ID")

# Encryption
FCM_TOKEN_SECRET                = os.getenv("FCM_TOKEN_SECRET")
PROFILE_PIC_MEDIA_ENCRYPTION    = os.getenv("PROFILE_PIC_MEDIA_ENCRYPTION")

# SMTP
SMTP_HOST     = os.getenv("SMTP_HOST")
SMTP_PORT     = os.getenv("SMTP_PORT")
SMTP_USER     = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


#s3
S3_BUCKET_NAME     = os.getenv("S3_BUCKET_NAME")
S3_BUCKET_REGION     = os.getenv("S3_BUCKET_REGION")
S3_BUCKET_ACCESS_KEY     = os.getenv("S3_BUCKET_ACCESS_KEY")
S3_BUCKET_SECRET_KEY     = os.getenv("S3_BUCKET_SECRET_KEY")

#Redsi
REDIS_URL =  os.getenv("REDIS_URL", "redis://doc.example.com")

#Resposne
API_DOC_BASE_URL = os.getenv("API_DOC_BASE_URL", "https://doc.example.com")

# App
APP_NAME = os.getenv("APP_NAME", "LTS360")