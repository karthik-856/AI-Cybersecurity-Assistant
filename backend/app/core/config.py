from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    database_url: str

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # ------------------------------------------------------------------
    # SMTP / Email
    # ------------------------------------------------------------------
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str = "ZUKA Security Operations Center"

    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False

    # ------------------------------------------------------------------
    # Authentication / OTP
    # ------------------------------------------------------------------
    otp_secret: str | None = None
    otp_expiry_minutes: int = 10
    otp_resend_seconds: int = 60
    otp_max_attempts: int = 5

    # Frontend URL
    frontend_base_url: str = "http://127.0.0.1:5173"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost,http://127.0.0.1"
    enable_in_process_replay: bool = True

    # ------------------------------------------------------------------
    # Persistent Web Push / VAPID
    # ------------------------------------------------------------------
    vapid_public_key: str | None = None
    vapid_private_key_path: str = "backend/vapid_private.pem"
    vapid_subject: str = "mailto:admin@zuka.local"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()