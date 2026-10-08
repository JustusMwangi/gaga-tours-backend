"""Tour domain services — business logic for tours, categories, destinations, dates, gallery."""

import math

from slugify import slugify

from app.blueprints.tours.models import (
    Destination,
    Tour,
    TourCategory,
    TourDate,
    TourGallery,
)
from app.blueprints.tours.repositories import (
    DestinationRepository,
    TourCategoryRepository,
    TourDateRepository,
    TourGalleryRepository,
    TourRepository,
)
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.extensions import db


def _strip_str_fields(data: dict) -> dict:
    """Return a copy of data with surrounding whitespace stripped from string values."""
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in data.items()}


def _tour_relations(tour) -> dict:
    """Serialize a tour's many-to-many categories and destinations."""
    return {
        "categories": [
            {"id": c.id, "name": c.name, "slug": c.slug}
            for c in tour.categories
        ],
        "destinations": [
            {"id": d.id, "name": d.name, "slug": d.slug, "country": d.country}
            for d in tour.destinations
        ],
    }


def _resolve_categories(category_ids):
    """Return TourCategory rows for the given ids (empty list if none)."""
    if not category_ids:
        return []
    return (
        db.session.query(TourCategory)
        .filter(TourCategory.id.in_(category_ids))
        .all()
    )


def _resolve_destinations(destination_ids):
    """Return Destination rows for the given ids (empty list if none)."""
    if not destination_ids:
        return []
    return (
        db.session.query(Destination)
        .filter(Destination.id.in_(destination_ids))
        .all()
    )


# ── Tour Category Service ────────────────────────────────────────────────


class TourCategoryService:
    """Static methods for tour category management."""

    @staticmethod
    def create_category(data: dict) -> dict:
        data = _strip_str_fields(data)
        repo = TourCategoryRepository(db.session)

        slug = slugify(data["name"])
        if repo.find_by_slug(slug):
            raise ConflictError(f"Category with slug '{slug}' already exists")

        category = TourCategory(
            name=data["name"],
            slug=slug,
            description=data.get("description"),
            is_active=data.get("is_active", True),
        )
        repo.create(category)
        db.session.commit()
        return category.to_dict()

    @staticmethod
    def list_categories(page: int = 1, per_page: int = 20,
                        search: str = None, is_active: bool = None) -> dict:
        repo = TourCategoryRepository(db.session)
        items, total = repo.list_all(
            page=page, per_page=per_page, search=search, is_active=is_active,
        )
        return {
            "categories": [c.to_dict() for c in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": math.ceil(total / per_page) if per_page else 0,
        }

    @staticmethod
    def get_category(category_id) -> dict:
        repo = TourCategoryRepository(db.session)
        category = repo.find_by_id(category_id)
        if not category:
            raise NotFoundError("Tour category not found")
        return category.to_dict()

    @staticmethod
    def update_category(category_id, data: dict) -> dict:
        data = _strip_str_fields(data)
        repo = TourCategoryRepository(db.session)
        category = repo.find_by_id(category_id)
        if not category:
            raise NotFoundError("Tour category not found")

        if "name" in data:
            new_slug = slugify(data["name"])
            existing = repo.find_by_slug(new_slug)
            if existing and existing.id != category_id:
                raise ConflictError(f"Category with slug '{new_slug}' already exists")
            category.name = data["name"]
            category.slug = new_slug

        if "description" in data:
            category.description = data["description"]
        if "is_active" in data:
            category.is_active = data["is_active"]

        db.session.commit()
        return category.to_dict()

    @staticmethod
    def delete_category(category_id) -> dict:
        repo = TourCategoryRepository(db.session)
        category = repo.find_by_id(category_id)
        if not category:
            raise NotFoundError("Tour category not found")

        db.session.delete(category)
        db.session.commit()
        return {"message": "Tour category deleted"}


# ── Destination Service ──────────────────────────────────────────────────


class DestinationService:
    """Static methods for destination management."""

    @staticmethod
    def create_destination(data: dict) -> dict:
        data = _strip_str_fields(data)
        repo = DestinationRepository(db.session)

        slug = slugify(data["name"])
        if repo.find_by_slug(slug):
            raise ConflictError(f"Destination with slug '{slug}' already exists")

        destination = Destination(
            name=data["name"],
            slug=slug,
            country=data.get("country"),
            description=data.get("description"),
            image_url=data.get("image_url"),
            is_active=data.get("is_active", True),
        )
        repo.create(destination)
        db.session.commit()
        return destination.to_dict()

    @staticmethod
    def list_destinations(page: int = 1, per_page: int = 20,
                          search: str = None, is_active: bool = None) -> dict:
        repo = DestinationRepository(db.session)
        items, total = repo.list_all(
            page=page, per_page=per_page, search=search, is_active=is_active,
        )
        return {
            "destinations": [d.to_dict() for d in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": math.ceil(total / per_page) if per_page else 0,
        }

    @staticmethod
    def get_destination(destination_id) -> dict:
        repo = DestinationRepository(db.session)
        destination = repo.find_by_id(destination_id)
        if not destination:
            raise NotFoundError("Destination not found")
        return destination.to_dict()

    @staticmethod
    def update_destination(destination_id, data: dict) -> dict:
        data = _strip_str_fields(data)
        repo = DestinationRepository(db.session)
        destination = repo.find_by_id(destination_id)
        if not destination:
            raise NotFoundError("Destination not found")

        if "name" in data:
            new_slug = slugify(data["name"])
            existing = repo.find_by_slug(new_slug)
            if existing and existing.id != destination_id:
                raise ConflictError(f"Destination with slug '{new_slug}' already exists")
            destination.name = data["name"]
            destination.slug = new_slug

        if "country" in data:
            destination.country = data["country"]
        if "description" in data:
            destination.description = data["description"]
        if "image_url" in data:
            destination.image_url = data["image_url"]
        if "is_active" in data:
            destination.is_active = data["is_active"]

        db.session.commit()
        return destination.to_dict()

    @staticmethod
    def delete_destination(destination_id) -> dict:
        repo = DestinationRepository(db.session)
        destination = repo.find_by_id(destination_id)
        if not destination:
            raise NotFoundError("Destination not found")

        db.session.delete(destination)
        db.session.commit()
        return {"message": "Destination deleted"}


# ── Tour Service ─────────────────────────────────────────────────────────


class TourService:
    """Static methods for tour management."""

    @staticmethod
    def create_tour(data: dict) -> dict:
        data = _strip_str_fields(data)
        repo = TourRepository(db.session)

        slug = slugify(data["title"])
        if repo.find_by_slug(slug):
            raise ConflictError(f"Tour with slug '{slug}' already exists")

        tour = Tour(
            title=data["title"],
            slug=slug,
            description=data.get("description"),
            short_description=data.get("short_description"),
            price=data.get("price"),
            currency=data.get("currency", "USD"),
            duration_days=data.get("duration_days"),
            duration_nights=data.get("duration_nights"),
            max_group_size=data.get("max_group_size"),
            difficulty_level=data.get("difficulty_level"),
            included=data.get("included"),
            excluded=data.get("excluded"),
            itinerary=data.get("itinerary"),
            status=data.get("status", "draft"),
            featured=data.get("featured", False),
            image_url=data.get("image_url"),
            meta_title=data.get("meta_title"),
            meta_description=data.get("meta_description"),
            youtube_url=data.get("youtube_url"),
        )
        repo.create(tour)  # add + flush so the tour is session-persistent
        tour.categories = _resolve_categories(data.get("category_ids"))
        tour.destinations = _resolve_destinations(data.get("destination_ids"))
        db.session.commit()
        return {**tour.to_dict(), **_tour_relations(tour)}

    @staticmethod
    def list_tours(
        page: int = 1,
        per_page: int = 20,
        search: str = None,
        status: str = None,
        category_id=None,
        destination_id=None,
        featured: bool = None,
    ) -> dict:
        repo = TourRepository(db.session)
        items, total = repo.list_all(
            page=page,
            per_page=per_page,
            search=search,
            status=status,
            category_id=category_id,
            destination_id=destination_id,
            featured=featured,
        )

        tours = []
        for tour in items:
            tours.append({**tour.to_dict(), **_tour_relations(tour)})

        return {
            "tours": tours,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": math.ceil(total / per_page) if per_page else 0,
        }

    @staticmethod
    def get_tour(tour_id) -> dict:
        repo = TourRepository(db.session)
        tour = repo.find_by_id(tour_id)
        if not tour or tour.is_deleted:
            raise NotFoundError("Tour not found")

        tour_data = {**tour.to_dict(), **_tour_relations(tour)}
        tour_data["dates"] = [d.to_dict() for d in tour.dates.order_by(TourDate.start_date.asc()).all()]
        tour_data["gallery"] = [g.to_dict() for g in tour.gallery.order_by(TourGallery.sort_order.asc()).all()]
        return tour_data

    @staticmethod
    def update_tour(tour_id, data: dict) -> dict:
        data = _strip_str_fields(data)
        repo = TourRepository(db.session)
        tour = repo.find_by_id(tour_id)
        if not tour or tour.is_deleted:
            raise NotFoundError("Tour not found")

        if "title" in data:
            new_slug = slugify(data["title"])
            existing = repo.find_by_slug(new_slug)
            if existing and existing.id != tour_id:
                raise ConflictError(f"Tour with slug '{new_slug}' already exists")
            tour.title = data["title"]
            tour.slug = new_slug

        simple_fields = [
            "description", "short_description",
            "price", "currency", "duration_days", "duration_nights",
            "max_group_size", "difficulty_level", "included", "excluded",
            "itinerary", "status", "featured", "image_url",
            "meta_title", "meta_description", "youtube_url",
        ]
        for field in simple_fields:
            if field in data:
                setattr(tour, field, data[field])

        if "category_ids" in data:
            tour.categories = _resolve_categories(data["category_ids"])
        if "destination_ids" in data:
            tour.destinations = _resolve_destinations(data["destination_ids"])

        db.session.commit()

        return {**tour.to_dict(), **_tour_relations(tour)}

    @staticmethod
    def delete_tour(tour_id) -> dict:
        repo = TourRepository(db.session)
        tour = repo.find_by_id(tour_id)
        if not tour or tour.is_deleted:
            raise NotFoundError("Tour not found")

        tour.soft_delete()
        db.session.commit()
        return {"message": "Tour deleted"}


# ── Tour Date Service ────────────────────────────────────────────────────


class TourDateService:
    """Static methods for tour date management."""

    @staticmethod
    def create_date(tour_id, data: dict) -> dict:
        tour_repo = TourRepository(db.session)
        tour = tour_repo.find_by_id(tour_id)
        if not tour or tour.is_deleted:
            raise NotFoundError("Tour not found")

        if data["start_date"] > data["end_date"]:
            raise BadRequestError("Start date must be before end date")

        date_repo = TourDateRepository(db.session)
        tour_date = TourDate(
            tour_id=tour_id,
            start_date=data["start_date"],
            end_date=data["end_date"],
            price_override=data.get("price_override"),
            max_spots=data.get("max_spots"),
            status=data.get("status", "available"),
        )
        date_repo.create(tour_date)
        db.session.commit()
        return tour_date.to_dict()

    @staticmethod
    def list_dates(tour_id) -> list:
        tour_repo = TourRepository(db.session)
        tour = tour_repo.find_by_id(tour_id)
        if not tour or tour.is_deleted:
            raise NotFoundError("Tour not found")

        date_repo = TourDateRepository(db.session)
        dates = date_repo.list_by_tour(tour_id)
        return [d.to_dict() for d in dates]

    @staticmethod
    def get_date(date_id) -> dict:
        date_repo = TourDateRepository(db.session)
        tour_date = date_repo.find_by_id(date_id)
        if not tour_date:
            raise NotFoundError("Tour date not found")
        return tour_date.to_dict()

    @staticmethod
    def update_date(date_id, data: dict) -> dict:
        date_repo = TourDateRepository(db.session)
        tour_date = date_repo.find_by_id(date_id)
        if not tour_date:
            raise NotFoundError("Tour date not found")

        if "start_date" in data:
            tour_date.start_date = data["start_date"]
        if "end_date" in data:
            tour_date.end_date = data["end_date"]
        if "price_override" in data:
            tour_date.price_override = data["price_override"]
        if "max_spots" in data:
            tour_date.max_spots = data["max_spots"]
        if "status" in data:
            tour_date.status = data["status"]

        # Validate dates after update
        if tour_date.start_date > tour_date.end_date:
            raise BadRequestError("Start date must be before end date")

        db.session.commit()
        return tour_date.to_dict()

    @staticmethod
    def delete_date(date_id) -> dict:
        date_repo = TourDateRepository(db.session)
        tour_date = date_repo.find_by_id(date_id)
        if not tour_date:
            raise NotFoundError("Tour date not found")

        date_repo.delete(tour_date)
        db.session.commit()
        return {"message": "Tour date deleted"}


# ── Tour Gallery Service ─────────────────────────────────────────────────


class TourGalleryService:
    """Static methods for tour gallery management."""

    @staticmethod
    def add_image(tour_id, data: dict) -> dict:
        tour_repo = TourRepository(db.session)
        tour = tour_repo.find_by_id(tour_id)
        if not tour or tour.is_deleted:
            raise NotFoundError("Tour not found")

        gallery_repo = TourGalleryRepository(db.session)
        item = TourGallery(
            tour_id=tour_id,
            image_url=data["image_url"],
            caption=data.get("caption"),
            sort_order=data.get("sort_order", 0),
        )
        gallery_repo.create(item)
        db.session.commit()
        return item.to_dict()

    @staticmethod
    def list_images(tour_id) -> list:
        tour_repo = TourRepository(db.session)
        tour = tour_repo.find_by_id(tour_id)
        if not tour or tour.is_deleted:
            raise NotFoundError("Tour not found")

        gallery_repo = TourGalleryRepository(db.session)
        items = gallery_repo.list_by_tour(tour_id)
        return [i.to_dict() for i in items]

    @staticmethod
    def update_image(image_id, data: dict) -> dict:
        gallery_repo = TourGalleryRepository(db.session)
        item = gallery_repo.find_by_id(image_id)
        if not item:
            raise NotFoundError("Gallery image not found")

        if "caption" in data:
            item.caption = data["caption"]
        if "sort_order" in data:
            item.sort_order = data["sort_order"]

        db.session.commit()
        return item.to_dict()

    @staticmethod
    def delete_image(image_id) -> dict:
        gallery_repo = TourGalleryRepository(db.session)
        item = gallery_repo.find_by_id(image_id)
        if not item:
            raise NotFoundError("Gallery image not found")

        gallery_repo.delete(item)
        db.session.commit()
        return {"message": "Gallery image deleted"}
