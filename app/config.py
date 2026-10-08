"""Environment-based configuration classes."""

import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://petro:petro@localhost:5432/book_sheilla"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT (PyJWT)
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret")
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 3600))  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES", 2592000))  # 30 days

    # Celery
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # Mail (Flask-Mail / SMTP)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@example.com")
    MAIL_REPLY_TO = os.environ.get("MAIL_REPLY_TO")

    # Frontend URL (for email links: verification, password reset, invitations)
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:8081")

    # MinIO / S3 file storage
    MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "")
    MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "")
    MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "app-files")
    MINIO_SECURE = os.environ.get("MINIO_SECURE", "false").lower() == "true"
    MINIO_PRESIGNED_URL_EXPIRY = int(os.environ.get("MINIO_PRESIGNED_URL_EXPIRY", "3600"))

    # CORS
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite:///test.db")

    # Deterministic secrets for tests
    SECRET_KEY = "test-secret-key"
    JWT_SECRET_KEY = "test-jwt-secret-key-for-testing-only"

    # In-memory Celery (no Redis required)
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"

    # Suppress emails during tests
    MAIL_SUPPRESS_SEND = True

    # MinIO test-specific values
    MINIO_ENDPOINT = "localhost:9000"
    MINIO_ACCESS_KEY = "test-access-key"
    MINIO_SECRET_KEY = "test-secret-key"
    MINIO_BUCKET = "test-files"


class ProductionConfig(Config):
    DEBUG = False

    # Connection pool tuning for PostgreSQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
