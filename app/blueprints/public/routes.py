"""Public API routes — no authentication required.

Serves published tour data and accepts inquiry/subscriber submissions.
Used by the public-facing Next.js site.
"""

import math
import secrets

from flask import Blueprint, jsonify, request
from marshmallow import Schema, fields, validate, ValidationError as MarshmallowValidationError
from sqlalchemy import or_

from app.core.exceptions import NotFoundError, ValidationError
from app.extensions import db, limiter

public_bp = Blueprint("public", __name__)


# ── Schemas ──────────────────────────────────────────────────────────────


class PublicTourListQuerySchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=12, validate=validate.Range(min=1, max=50))
    search = fields.String(load_default=None)
    category_id = fields.UUID(load_default=None)
    destination_id = fields.UUID(load_default=None)
    featured = fields.Boolean(load_default=None)
    sort = fields.String(
        load_default="recommended",
        validate=validate.OneOf(["recommended", "duration_desc", "duration_asc"]),
    )


class PublicInquirySchema(Schema):
    first_name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    last_name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(required=True)
    phone = fields.String(validate=validate.Length(max=30))
    tour_id = fields.UUID(load_default=None)
    message = fields.String()
    travel_date = fields.Date(load_default=None)
    group_size_adults = fields.Integer(load_default=1, validate=validate.Range(min=1))
    group_size_children = fields.Integer(load_default=0, validate=validate.Range(min=0))
    budget = fields.Float(load_default=None)
    currency = fields.String(load_default="USD", validate=validate.Length(max=3))
    privacy_consent = fields.Boolean(required=True)


class PublicSubscriberSchema(Schema):
    email = fields.Email(required=True)
    name = fields.String(validate=validate.Length(max=200))
    privacy_consent = fields.Boolean(required=True)


class DataRequestSchema(Schema):
    email = fields.Email(required=True)
    request_type = fields.String(
        required=True,
        validate=validate.OneOf(["export", "deletion"]),
    )


# ── Consent helper ──────────────────────────────────────────────────────


def _record_consent(email: str, purpose: str, consent_given: bool = True):
    """Create an immutable consent record."""
    from app.blueprints.consent.models import ConsentRecord

    record = ConsentRecord(
        email=email.lower(),
        purpose=purpose,
        consent_given=consent_given,
        ip_address=request.remote_addr,
        user_agent=(request.headers.get("User-Agent") or "")[:500],
        source="website",
    )
    db.session.add(record)


# ── Helpers ──────────────────────────────────────────────────────────────


def _tour_to_dict(tour):
    """Serialize a Tour for public consumption."""
    return {
        "id": str(tour.id),
        "title": tour.title,
        "slug": tour.slug,
        "description": tour.description,
        "highlights": tour.short_description,
        "base_price_adult": str(tour.price) if tour.price else None,
        "base_price_child": None,
        "currency": tour.currency,
        "duration_days": tour.duration_days,
        "duration_nights": tour.duration_nights,
        "max_group_size": tour.max_group_size,
        "difficulty": tour.difficulty_level,
        "is_featured": tour.featured,
        "featured_image_url": tour.image_url,
        "status": tour.status,
        "categories": [
            {"id": str(c.id), "name": c.name, "slug": c.slug}
            for c in tour.categories
        ],
        "destinations": [
            {
                "id": str(d.id),
                "name": d.name,
                "slug": d.slug,
                "country": d.country,
            }
            for d in tour.destinations
        ],
        "created_at": tour.created_at.isoformat() if tour.created_at else None,
        "updated_at": tour.updated_at.isoformat() if tour.updated_at else None,
    }


def _tour_detail_to_dict(tour):
    """Serialize a Tour with dates and gallery."""
    data = _tour_to_dict(tour)
    data["included"] = tour.included
    data["excluded"] = tour.excluded
    data["itinerary"] = tour.itinerary
    data["meta_title"] = tour.meta_title
    data["meta_description"] = tour.meta_description
    data["youtube_url"] = tour.youtube_url
    data["gallery"] = [
        {
            "id": str(img.id),
            "image_url": img.image_url,
            "caption": img.caption,
            "sort_order": img.sort_order,
        }
        for img in sorted(tour.gallery, key=lambda g: g.sort_order)
    ]
    data["tour_dates"] = [
        {
            "id": str(td.id),
            "tour_id": str(td.tour_id),
            "start_date": td.start_date.isoformat() if td.start_date else None,
            "end_date": td.end_date.isoformat() if td.end_date else None,
            "price_adult_override": str(td.price_override) if td.price_override else None,
            "price_child_override": None,
            "total_capacity": td.max_spots,
            "booked_count": td.spots_booked,
            "available_capacity": (td.max_spots - td.spots_booked) if td.max_spots else None,
            "status": td.status,
        }
        for td in sorted(tour.dates, key=lambda d: d.start_date)
    ]
    return data


# ── Images ───────────────────────────────────────────────────────────────


@public_bp.route("/images/<uuid:file_id>", methods=["GET"])
def public_image(file_id):
    """Serve image content directly. No auth required."""
    from flask import send_file
    from app.blueprints.files.models import File
    from app.core.storage import download_file as storage_download

    f = db.session.get(File, file_id)
    if not f or f.deleted_at is not None:
        raise NotFoundError("Image not found")

    data = storage_download(f.file_path)
    response = send_file(
        data,
        mimetype=f.mime_type,
        download_name=f.original_filename,
    )
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


# ── Tours ────────────────────────────────────────────────────────────────


@public_bp.route("/tours", methods=["GET"])
def list_tours():
    """List published tours (public)."""
    from app.blueprints.tours.models import Tour

    schema = PublicTourListQuerySchema()
    try:
        params = schema.load(request.args)
    except MarshmallowValidationError as e:
        raise ValidationError("Invalid query parameters", errors=e.messages)

    query = db.session.query(Tour).filter(
        Tour.status == "published",
        Tour.deleted_at.is_(None),
    )

    if params.get("search"):
        pattern = f"%{params['search']}%"
        query = query.filter(
            or_(Tour.title.ilike(pattern), Tour.short_description.ilike(pattern))
        )
    if params.get("category_id"):
        from app.blueprints.tours.models import TourCategory
        query = query.filter(Tour.categories.any(TourCategory.id == params["category_id"]))
    if params.get("destination_id"):
        from app.blueprints.tours.models import Destination
        query = query.filter(Tour.destinations.any(Destination.id == params["destination_id"]))
    if params.get("featured") is not None:
        query = query.filter(Tour.featured.is_(params["featured"]))

    sort = params["sort"]
    if sort == "duration_desc":
        order_by = Tour.duration_days.desc()
    elif sort == "duration_asc":
        order_by = Tour.duration_days.asc()
    else:
        order_by = Tour.featured.desc(), Tour.created_at.desc()

    total = query.count()
    page = params["page"]
    per_page = params["per_page"]
    tours = (
        query.order_by(*order_by) if isinstance(order_by, tuple) else query.order_by(order_by)
    )
    tours = tours.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "tours": [_tour_to_dict(t) for t in tours],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if per_page else 0,
    }), 200


@public_bp.route("/tours/<slug>", methods=["GET"])
def get_tour_by_slug(slug):
    """Get a published tour by slug (public)."""
    from app.blueprints.tours.models import Tour

    tour = db.session.query(Tour).filter(
        Tour.slug == slug,
        Tour.status == "published",
        Tour.deleted_at.is_(None),
    ).first()

    if not tour:
        raise NotFoundError("Tour not found")

    return jsonify(_tour_detail_to_dict(tour)), 200


# ── Categories ───────────────────────────────────────────────────────────


@public_bp.route("/categories", methods=["GET"])
def list_categories():
    """List active tour categories (public)."""
    from app.blueprints.tours.models import TourCategory

    categories = db.session.query(TourCategory).filter(
        TourCategory.is_active.is_(True),
        TourCategory.deleted_at.is_(None),
    ).order_by(TourCategory.name).all()

    return jsonify({
        "categories": [
            {
                "id": str(c.id),
                "name": c.name,
                "slug": c.slug,
                "description": c.description,
                "is_active": c.is_active,
            }
            for c in categories
        ]
    }), 200


# ── Destinations ─────────────────────────────────────────────────────────


@public_bp.route("/destinations", methods=["GET"])
@public_bp.route("/destinations/<slug>", methods=["GET"])
def list_destinations(slug=None):
    """List active destinations or get one by slug (public)."""
    from app.blueprints.tours.models import Destination

    if slug:
        dest = db.session.query(Destination).filter(
            Destination.slug == slug,
            Destination.is_active.is_(True),
            Destination.deleted_at.is_(None),
        ).first()
        if not dest:
            raise NotFoundError("Destination not found")
        return jsonify({
            "id": str(dest.id),
            "name": dest.name,
            "slug": dest.slug,
            "country": dest.country,
            "description": dest.description,
            "image_url": dest.image_url,
            "is_active": dest.is_active,
        }), 200

    destinations = db.session.query(Destination).filter(
        Destination.is_active.is_(True),
        Destination.deleted_at.is_(None),
    ).order_by(Destination.name).all()

    return jsonify({
        "destinations": [
            {
                "id": str(d.id),
                "name": d.name,
                "slug": d.slug,
                "country": d.country,
                "description": d.description,
                "image_url": d.image_url,
                "is_active": d.is_active,
            }
            for d in destinations
        ]
    }), 200


# ── Inquiries ────────────────────────────────────────────────────────────


@public_bp.route("/inquiries", methods=["POST"])
def submit_inquiry():
    """Submit a tour inquiry from the public site."""
    from app.blueprints.inquiries.services import InquiryService

    schema = PublicInquirySchema()
    try:
        data = schema.load(request.get_json() or {})
    except MarshmallowValidationError as e:
        raise ValidationError("Validation failed", errors=e.messages)

    if not data.get("privacy_consent"):
        raise ValidationError(
            "Privacy consent is required",
            errors={"privacy_consent": ["You must accept the privacy policy."]},
        )

    purpose = "booking_inquiry" if data.get("tour_id") else "contact_inquiry"
    _record_consent(data["email"], purpose)

    inquiry_data = {k: v for k, v in data.items() if k != "privacy_consent"}
    inquiry_data["source"] = "website"
    result = InquiryService.create_inquiry(inquiry_data)

    db.session.commit()

    return jsonify({"id": str(result["id"]), "message": "Inquiry submitted successfully"}), 201


# ── Subscribers ──────────────────────────────────────────────────────────


@public_bp.route("/subscribe", methods=["POST"])
def subscribe():
    """Subscribe to newsletter from the public site."""
    from app.blueprints.public.models import Subscriber

    schema = PublicSubscriberSchema()
    try:
        data = schema.load(request.get_json() or {})
    except MarshmallowValidationError as e:
        raise ValidationError("Validation failed", errors=e.messages)

    if not data.get("privacy_consent"):
        raise ValidationError(
            "Privacy consent is required",
            errors={"privacy_consent": ["You must accept the privacy policy."]},
        )

    existing = db.session.query(Subscriber).filter(
        Subscriber.email == data["email"].lower()
    ).first()

    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.unsubscribed_at = None
            existing.name = data.get("name") or existing.name
            if not existing.unsubscribe_token:
                existing.unsubscribe_token = secrets.token_urlsafe(32)
        _record_consent(data["email"], "newsletter")
        db.session.commit()
        return jsonify({"message": "Subscribed successfully"}), 200

    subscriber = Subscriber(
        email=data["email"].lower(),
        name=data.get("name"),
    )
    db.session.add(subscriber)
    _record_consent(data["email"], "newsletter")
    db.session.commit()

    return jsonify({"message": "Subscribed successfully"}), 201


# ── Unsubscribe ──────────────────────────────────────────────────────────


@public_bp.route("/unsubscribe/<token>", methods=["GET"])
def unsubscribe(token):
    """Unsubscribe from the newsletter via unique token."""
    from datetime import datetime, timezone
    from app.blueprints.public.models import Subscriber

    subscriber = db.session.query(Subscriber).filter_by(
        unsubscribe_token=token,
    ).first()

    if not subscriber:
        raise NotFoundError("Invalid or expired unsubscribe link")

    if not subscriber.is_active:
        return jsonify({"message": "You are already unsubscribed"}), 200

    subscriber.is_active = False
    subscriber.unsubscribed_at = datetime.now(timezone.utc)
    _record_consent(subscriber.email, "newsletter", consent_given=False)
    db.session.commit()

    return jsonify({"message": "You have been unsubscribed successfully"}), 200


# ── Data Rights (GDPR) ──────────────────────────────────────────────────


@public_bp.route("/data-request", methods=["POST"])
@limiter.limit("3 per hour")
def data_request():
    """Request data export or deletion (GDPR Art. 15/17)."""
    schema = DataRequestSchema()
    try:
        data = schema.load(request.get_json() or {})
    except MarshmallowValidationError as e:
        raise ValidationError("Validation failed", errors=e.messages)

    from app.blueprints.consent.tasks import process_data_export, process_data_deletion

    if data["request_type"] == "export":
        process_data_export.delay(data["email"])
    else:
        process_data_deletion.delay(data["email"])

    return jsonify({
        "message": (
            "If we have data associated with this email address, "
            "we will process your request and contact you within 30 days."
        ),
    }), 202
