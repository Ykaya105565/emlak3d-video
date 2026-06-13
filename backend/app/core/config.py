from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    render_worker_url: str = "http://localhost:8001"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    # DB
    database_url: str = "postgresql+asyncpg://emlak:emlak_pass@localhost:5432/emlakdb"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_bucket_gml: str = "gml-files"
    minio_bucket_photos: str = "property-photos"
    minio_bucket_videos: str = "rendered-videos"

    # JWT
    jwt_secret_key: str = "change-this-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30

    # Google
    google_maps_api_key: str = ""

    # Claude API
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    # TTS
    tts_provider: str = "google"
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    google_tts_api_key: str = ""

    # Render
    render_output_dir: str = "/tmp/renders"
    max_cost_per_video_usd: float = 5.0

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
