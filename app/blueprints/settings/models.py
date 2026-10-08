"""Application settings model (singleton)."""

from sqlalchemy import Column, String, Text

from app.core.models import BaseModel


class AppSettings(BaseModel):
    """Singleton row storing application-wide settings."""

    __tablename__ = "app_settings"

    app_name = Column(String(255), nullable=False, default="My App")

    # Regional
    timezone = Column(String(50), nullable=False, default="UTC")
    currency = Column(String(3), nullable=False, default="USD")
    locale = Column(String(10), nullable=False, default="en-US")

    # Display formats
    date_format = Column(String(20), nullable=False, default="DD/MM/YYYY")
    time_format = Column(String(10), nullable=False, default="24h")

    # Business info
    business_name = Column(String(255), nullable=True)
    business_address = Column(String(500), nullable=True)
    business_phone = Column(String(50), nullable=True)
    business_email = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<AppSettings {self.app_name}>"
