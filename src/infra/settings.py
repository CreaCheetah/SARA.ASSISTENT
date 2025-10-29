import os

class Settings:
    ADMIN_USER = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASS = os.getenv("ADMIN_PASS", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    REDIS_URL = os.getenv("REDIS_URL", "")

    TTS_MODEL = os.getenv("TTS_MODEL", "gpt-4o-mini-tts")
    TTS_VOICE = os.getenv("TTS_VOICE", "marin")

    TZ = os.getenv("TZ", "Europe/Amsterdam")

    # MODE: 'dev' (testmodus) of 'prod' (live)
    SARA_MODE = os.getenv("SARA_MODE", "dev")

    # Telefooninstellingen
    TWILIO_NUMBER = os.getenv("TWILIO_NUMBER", "")
    FORWARD_LIVE = os.getenv("FORWARD_LIVE", "")
    FAILSAFE_NUMBER = os.getenv("FAILSAFE_NUMBER", "")

settings = Settings()

def is_dev() -> bool:
    """Geeft True als de applicatie in testmodus draait."""
    return (settings.SARA_MODE or "dev").lower() == "dev"

def is_prod() -> bool:
    """Geeft True als de applicatie in live modus draait."""
    return not is_dev()
