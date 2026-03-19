
import os

from dotenv import load_dotenv

load_dotenv() 

ACCESS_TOKEN_SECRET  = os.getenv("ACCESS_TOKEN_SECRET")
REFRESH_TOKEN_SECRET = os.getenv("REFRESH_TOKEN_SECRET")
ALGORITHM            = os.getenv("ALGORITHM", "HS256")
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "30"))

API_DOC_BASE_URL = os.getenv("API_DOC_BASE_URL", "http://localhost:8000")

DATABASE_URL = os.getenv("DATABASE_URL")

APP_NAME    = os.getenv("APP_NAME", "LTS360 Server")
DEBUG       = os.getenv("DEBUG", "false").lower() == "true"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")