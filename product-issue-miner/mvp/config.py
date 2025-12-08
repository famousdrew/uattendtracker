"""Configuration for the MVP."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Zendesk
    ZENDESK_SUBDOMAIN = os.getenv("ZENDESK_SUBDOMAIN")
    ZENDESK_EMAIL = os.getenv("ZENDESK_EMAIL")
    ZENDESK_API_TOKEN = os.getenv("ZENDESK_API_TOKEN")
    ZENDESK_BRAND_ID = os.getenv("ZENDESK_BRAND_ID")

    # Anthropic
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    @classmethod
    def validate(cls) -> list[str]:
        """Return list of missing required config values."""
        missing = []
        if not cls.ZENDESK_SUBDOMAIN:
            missing.append("ZENDESK_SUBDOMAIN")
        if not cls.ZENDESK_EMAIL:
            missing.append("ZENDESK_EMAIL")
        if not cls.ZENDESK_API_TOKEN:
            missing.append("ZENDESK_API_TOKEN")
        if not cls.ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY")
        return missing
