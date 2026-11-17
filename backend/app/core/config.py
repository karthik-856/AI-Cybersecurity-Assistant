from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator, field_validator, SecretStr


class Settings(BaseSettings):
    app_env: str = "development"
    auth_rate_limit_enabled: bool = True
    frontend_dist_dir: str = "frontend/dist"
    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    database_url: str

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_postgres_url(cls, value):
        if isinstance(value, str) and value.startswith(("postgres://", "postgresql://")):
            return "postgresql+psycopg2://" + value.split("://", 1)[1]
        return value

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
    enable_in_process_replay: bool = False

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.app_env == "production":
            for name, value in (("JWT_SECRET_KEY", self.jwt_secret_key), ("OTP_SECRET", self.otp_secret)):
                if not value or len(value) < 32 or "CHANGE_THIS" in value or "generate_a_random" in value:
                    raise ValueError(f"{name} must be a generated secret of at least 32 characters in production.")
            if self.jwt_secret_key == self.otp_secret:
                raise ValueError("JWT_SECRET_KEY and OTP_SECRET must be different.")
        return self

    # ------------------------------------------------------------------
    # Persistent Web Push / VAPID
    # ------------------------------------------------------------------
    vapid_public_key: str | None = None
    vapid_private_key: SecretStr | None = None
    vapid_private_key_path: str = "backend/vapid_private.pem"
    vapid_subject: str = "mailto:admin@zuka.local"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
