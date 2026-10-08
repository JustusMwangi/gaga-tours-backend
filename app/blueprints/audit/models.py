"""Audit Log model for tracking all significant actions."""

from sqlalchemy import Column, Index, String, Text, Uuid
from sqlalchemy.orm import relationship

from app.core.models import BaseModel, _uuid_fk
from app.extensions import db


class AuditLog(BaseModel):
    """Audit log entry recording a significant action."""

    __tablename__ = "audit_logs"

    # Actor information
    user_id = _uuid_fk("users.id")

    # Action details
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(Uuid, nullable=True, index=True)

    # Change tracking
    old_values = Column(db.JSON, nullable=True)
    new_values = Column(db.JSON, nullable=True)

    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Additional context
    description = Column(Text, nullable=True)
    extra_data = Column(db.JSON, nullable=True)

    # Relationships for eager loading
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_audit_logs_created", "created_at"),
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_id} at {self.created_at}>"
