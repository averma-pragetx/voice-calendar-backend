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

    # --- Booking confirmation emails (sent via Gmail SMTP) ---
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    google_sender_id: str = ""  # e.g. someone@gmail.com
    google_sender_app_specific_password: str = ""  # generated at myaccount.google.com/apppasswords
    booking_notification_email: str = ""  # hardcoded recipient (the customer/receiver)

    # --- Booking confirmation SMS (sent via Twilio) ---
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""  # Twilio number SMS is sent from, E.164
    twilio_status_callback_url: str = ""  # e.g. https://voice-calendar-backend.pragetx.ai/api/sms/webhook

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
