"""Tour domain repositories — data access for tour-related models."""

from sqlalchemy import or_

from app.blueprints.tours.models import (
    Destination,
    Tour,
    TourCategory,
    TourDate,
    TourGallery,
)


class TourCategoryRepository:
    """Data access for the TourCategory model."""

    def __init__(self, session):
        self.session = session

    def find_by_id(self, category_id):
        return self.session.get(TourCategory, category_id)

    def find_by_slug(self, slug):
        return self.session.query(TourCategory).filter(
            TourCategory.slug == slug,
        ).first()

    def list_all(self, page=1, per_page=20, search=None, is_active=None):
        """Return paginated categories as (items, total)."""
        query = self.session.query(TourCategory)

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    TourCategory.name.ilike(pattern),
                    TourCategory.description.ilike(pattern),
                )
            )

        if is_active is not None:
            query = query.filter(TourCategory.is_active.is_(is_active))

        total = query.count()
        items = (
            query
            .order_by(TourCategory.name.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return items, total

    def create(self, category):
        self.session.add(category)
        self.session.flush()
        return category

    def flush(self):
        self.session.flush()


class DestinationRepository:
    """Data access for the Destination model."""

    def __init__(self, session):
        self.session = session

    def find_by_id(self, destination_id):
        return self.session.get(Destination, destination_id)

    def find_by_slug(self, slug):
        return self.session.query(Destination).filter(
            Destination.slug == slug,
        ).first()

    def list_all(self, page=1, per_page=20, search=None, is_active=None):
        """Return paginated destinations as (items, total)."""
        query = self.session.query(Destination)

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Destination.name.ilike(pattern),
                    Destination.country.ilike(pattern),
                    Destination.description.ilike(pattern),
                )
            )

        if is_active is not None:
            query = query.filter(Destination.is_active.is_(is_active))

        total = query.count()
        items = (
            query
            .order_by(Destination.name.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return items, total

    def create(self, destination):
        self.session.add(destination)
        self.session.flush()
        return destination

    def flush(self):
        self.session.flush()


class TourRepository:
    """Data access for the Tour model."""

    def __init__(self, session):
        self.session = session

    def find_by_id(self, tour_id):
        return self.session.get(Tour, tour_id)

    def find_by_slug(self, slug):
        return self.session.query(Tour).filter(
            Tour.slug == slug,
        ).first()

    def list_all(
        self,
        page=1,
        per_page=20,
        search=None,
        status=None,
        category_id=None,
        destination_id=None,
        featured=None,
    ):
        """Return paginated tours as (items, total).

        Excludes soft-deleted tours.
        """
        query = self.session.query(Tour).filter(Tour.deleted_at.is_(None))

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Tour.title.ilike(pattern),
                    Tour.short_description.ilike(pattern),
                    Tour.description.ilike(pattern),
                )
            )

        if status:
            query = query.filter(Tour.status == status)

        if category_id:
            query = query.filter(Tour.categories.any(TourCategory.id == category_id))

        if destination_id:
            query = query.filter(Tour.destinations.any(Destination.id == destination_id))

        if featured is not None:
            query = query.filter(Tour.featured.is_(featured))

        total = query.count()
        items = (
            query
            .order_by(Tour.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return items, total

    def create(self, tour):
        self.session.add(tour)
        self.session.flush()
        return tour

    def flush(self):
        self.session.flush()


class TourDateRepository:
    """Data access for the TourDate model."""

    def __init__(self, session):
        self.session = session

    def find_by_id(self, date_id):
        return self.session.get(TourDate, date_id)

    def list_by_tour(self, tour_id):
        """Return all dates for a tour, ordered by start_date."""
        return (
            self.session.query(TourDate)
            .filter(TourDate.tour_id == tour_id)
            .order_by(TourDate.start_date.asc())
            .all()
        )

    def create(self, tour_date):
        self.session.add(tour_date)
        self.session.flush()
        return tour_date

    def delete(self, tour_date):
        self.session.delete(tour_date)

    def flush(self):
        self.session.flush()


class TourGalleryRepository:
    """Data access for the TourGallery model."""

    def __init__(self, session):
        self.session = session

    def find_by_id(self, image_id):
        return self.session.get(TourGallery, image_id)

    def list_by_tour(self, tour_id):
        """Return all gallery images for a tour, ordered by sort_order."""
        return (
            self.session.query(TourGallery)
            .filter(TourGallery.tour_id == tour_id)
            .order_by(TourGallery.sort_order.asc())
            .all()
        )

    def create(self, gallery_item):
        self.session.add(gallery_item)
        self.session.flush()
        return gallery_item

    def delete(self, gallery_item):
        self.session.delete(gallery_item)

    def flush(self):
        self.session.flush()
