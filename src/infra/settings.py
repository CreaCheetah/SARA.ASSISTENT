import os

class Settings:
    ADMIN_USER = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASS = os.getenv("ADMIN_PASS", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    REDIS_URL = os.getenv("REDIS_URL", "")
    TTS_MODEL = os.getenv("TTS_MODEL", "gpt-4o-mini-tts")
    TTS_VOICE = os.getenv("TTS_VOICE", "marin")
    TZ = os.getenv("TZ", "Europe/Amsterdam")

settings = Settings()
