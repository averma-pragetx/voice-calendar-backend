"""
Centralized configuration, loaded from environment variables (.env file).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Which calendar backend is active ---
    calendar_provider: str = "apple"  # "apple" or "google"

    # --- Apple iCloud CalDAV (used when calendar_provider == "apple") ---
    apple_id: str = ""  # e.g. someone@icloud.com
    apple_app_specific_password: str = ""  # generated at appleid.apple.com
    apple_provider_id: str = ""  # provider-side iCloud account, mirrored on every write
    apple_app_specific_provider_password: str = ""
    apple_caldav_url: str = "https://caldav.icloud.com"
    calendar_name: str | None = None  # if None, uses the first/default calendar found
    default_timezone: str = "Asia/Kolkata"  # used when creating events

    # --- Google Calendar (used when calendar_provider == "google") ---
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""  # obtained once via scripts/google_oauth_setup.py
    google_calendar_id: str = "primary"

    # --- ElevenLabs: one agent per calendar provider, picked at call-trigger time ---
    elevenlabs_api_key: str
    elevenlabs_google_agent_id: str = ""
    elevenlabs_google_agent_phone_number_id: str = ""
    elevenlabs_apple_agent_id: str = ""
    elevenlabs_apple_agent_phone_number_id: str = ""

    # --- Security for the webhook tool endpoints ElevenLabs will call mid-conversation ---
    tool_webhook_secret: str

    # --- Booking confirmation emails (sent via iCloud Mail SMTP, reuses Apple credentials) ---
    smtp_host: str = "smtp.mail.me.com"
    smtp_port: int = 587
    booking_notification_email: str = ""  # hardcoded recipient (the customer/receiver)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
