"""Tour domain models: Category, Destination, Tour, TourDate, TourGallery."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)

from app.core.models import AuditableModel
from app.extensions import db


# ── Association tables (many-to-many) ──────────────────────────────────────
# A tour can span several categories (bush, family & kids, group…) and visit
# several destinations (e.g. Amboseli + Nakuru + Maasai Mara on one safari).

tour_category_links = db.Table(
    "tour_category_links",
    Column(
        "tour_id",
        Uuid,
        ForeignKey("tours.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        Uuid,
        ForeignKey("tour_categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

tour_destination_links = db.Table(
    "tour_destination_links",
    Column(
        "tour_id",
        Uuid,
        ForeignKey("tours.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "destination_id",
        Uuid,
        ForeignKey("destinations.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class TourCategory(AuditableModel):
    __tablename__ = "tour_categories"

    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(120), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    tours = db.relationship(
        "Tour",
        secondary=tour_category_links,
        back_populates="categories",
        lazy="dynamic",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<TourCategory {self.name}>"


class Destination(AuditableModel):
    __tablename__ = "destinations"

    name = Column(String(200), unique=True, nullable=False)
    slug = Column(String(220), unique=True, nullable=False)
    country = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    tours = db.relationship(
        "Tour",
        secondary=tour_destination_links,
        back_populates="destinations",
        lazy="dynamic",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Destination {self.name}>"


class Tour(AuditableModel):
    __tablename__ = "tours"

    title = Column(String(200), nullable=False)
    slug = Column(String(220), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)
    price = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), default="USD", nullable=False)
    duration_days = Column(Integer, nullable=True)
    duration_nights = Column(Integer, nullable=True)
    max_group_size = Column(Integer, nullable=True)
    difficulty_level = Column(String(50), nullable=True)
    included = Column(Text, nullable=True)
    excluded = Column(Text, nullable=True)
    itinerary = Column(Text, nullable=True)
    status = Column(String(20), default="draft", nullable=False)  # draft/published/archived
    featured = Column(Boolean, default=False, nullable=False)
    image_url = Column(String(500), nullable=True)
    meta_title = Column(String(200), nullable=True)
    meta_description = Column(String(500), nullable=True)
    youtube_url = Column(String(500), nullable=True)

    # Relationships
    categories = db.relationship(
        "TourCategory",
        secondary=tour_category_links,
        back_populates="tours",
        lazy="selectin",
        passive_deletes=True,
    )
    destinations = db.relationship(
        "Destination",
        secondary=tour_destination_links,
        back_populates="tours",
        lazy="selectin",
        passive_deletes=True,
    )
    dates = db.relationship(
        "TourDate",
        back_populates="tour",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    gallery = db.relationship(
        "TourGallery",
        back_populates="tour",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Tour {self.title}>"


class TourDate(AuditableModel):
    __tablename__ = "tour_dates"
    __table_args__ = (
        Index("ix_tour_dates_tour_start", "tour_id", "start_date"),
    )

    tour_id = Column(
        Uuid,
        ForeignKey("tours.id", ondelete="CASCADE"),
        nullable=False,
    )
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    price_override = Column(Numeric(12, 2), nullable=True)
    max_spots = Column(Integer, nullable=True)
    spots_booked = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="available", nullable=False)  # available/full/cancelled

    # Relationships
    tour = db.relationship("Tour", back_populates="dates")

    def __repr__(self):
        return f"<TourDate {self.tour_id} {self.start_date}>"


class TourGallery(AuditableModel):
    __tablename__ = "tour_gallery"

    tour_id = Column(
        Uuid,
        ForeignKey("tours.id", ondelete="CASCADE"),
        nullable=False,
    )
    image_url = Column(String(500), nullable=False)
    caption = Column(String(300), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)

    # Relationships
    tour = db.relationship("Tour", back_populates="gallery")

    def __repr__(self):
        return f"<TourGallery {self.tour_id} #{self.sort_order}>"
