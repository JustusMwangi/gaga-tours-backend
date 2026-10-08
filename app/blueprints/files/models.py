"""File storage models."""

from sqlalchemy import Column, Index, String, Text, BigInteger
from sqlalchemy.orm import relationship

from app.core.models import AuditableModel
from app.extensions import db


class File(AuditableModel):
    """File metadata for objects stored in MinIO.

    Inherits from AuditableModel:
    - id (UUID)
    - created_at, updated_at (DateTime)
    - created_by, updated_by (UUID, FK to users)
    - deleted_at (DateTime, for soft delete)
    """

    __tablename__ = "files"

    # File metadata
    filename = Column(String(255), nullable=False)  # UUID-based unique filename
    original_filename = Column(String(255), nullable=False)  # User-provided name
    file_path = Column(String(1024), nullable=False)  # Full path in bucket

    # File properties
    size = Column(BigInteger, nullable=False)  # Size in bytes
    mime_type = Column(String(255), nullable=False)

    # Optional description
    description = Column(Text, nullable=True)

    # Relationships
    uploader = relationship(
        "User", foreign_keys="File.created_by", backref="uploaded_files"
    )

    __table_args__ = (
        Index("ix_files_created", "created_at"),
    )

    def __repr__(self):
        return f"<File {self.original_filename} ({self.id})>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "filename": self.filename,
            "original_filename": self.original_filename,
            "size": self.size,
            "mime_type": self.mime_type,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
        }
