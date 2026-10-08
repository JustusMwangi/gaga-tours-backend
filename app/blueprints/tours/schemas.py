"""Tour domain schemas for request/response validation."""

from marshmallow import Schema, fields, validate


# ── Request schemas ───────────────────────────────────────────────────────


class CreateCategorySchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(allow_none=True)
    is_active = fields.Boolean(load_default=True)


class UpdateCategorySchema(Schema):
    name = fields.String(validate=validate.Length(min=1, max=100))
    description = fields.String(allow_none=True)
    is_active = fields.Boolean()


class CategoryListQuerySchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    search = fields.String(load_default=None)
    is_active = fields.Boolean(load_default=None)


class CreateDestinationSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=200))
    country = fields.String(validate=validate.Length(max=100), allow_none=True)
    description = fields.String(allow_none=True)
    image_url = fields.String(validate=validate.Length(max=500), allow_none=True)
    is_active = fields.Boolean(load_default=True)


class UpdateDestinationSchema(Schema):
    name = fields.String(validate=validate.Length(min=1, max=200))
    country = fields.String(validate=validate.Length(max=100), allow_none=True)
    description = fields.String(allow_none=True)
    image_url = fields.String(validate=validate.Length(max=500), allow_none=True)
    is_active = fields.Boolean()


class DestinationListQuerySchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    search = fields.String(load_default=None)
    is_active = fields.Boolean(load_default=None)


class CreateTourSchema(Schema):
    title = fields.String(required=True, validate=validate.Length(min=1, max=200))
    description = fields.String(allow_none=True)
    short_description = fields.String(validate=validate.Length(max=500), allow_none=True)
    category_ids = fields.List(fields.UUID(), load_default=list)
    destination_ids = fields.List(fields.UUID(), load_default=list)
    price = fields.Decimal(as_string=True, allow_none=True)
    currency = fields.String(validate=validate.Length(max=3), load_default="USD")
    duration_days = fields.Integer(allow_none=True)
    duration_nights = fields.Integer(allow_none=True)
    max_group_size = fields.Integer(allow_none=True)
    difficulty_level = fields.String(validate=validate.Length(max=50), allow_none=True)
    included = fields.String(allow_none=True)
    excluded = fields.String(allow_none=True)
    itinerary = fields.String(allow_none=True)
    status = fields.String(
        validate=validate.OneOf(["draft", "published", "archived"]),
        load_default="draft",
    )
    featured = fields.Boolean(load_default=False)
    image_url = fields.String(validate=validate.Length(max=500), allow_none=True)
    meta_title = fields.String(validate=validate.Length(max=200), allow_none=True)
    meta_description = fields.String(validate=validate.Length(max=500), allow_none=True)
    youtube_url = fields.String(validate=validate.Length(max=500), allow_none=True)


class UpdateTourSchema(Schema):
    title = fields.String(validate=validate.Length(min=1, max=200))
    description = fields.String(allow_none=True)
    short_description = fields.String(validate=validate.Length(max=500), allow_none=True)
    category_ids = fields.List(fields.UUID())
    destination_ids = fields.List(fields.UUID())
    price = fields.Decimal(as_string=True, allow_none=True)
    currency = fields.String(validate=validate.Length(max=3))
    duration_days = fields.Integer(allow_none=True)
    duration_nights = fields.Integer(allow_none=True)
    max_group_size = fields.Integer(allow_none=True)
    difficulty_level = fields.String(validate=validate.Length(max=50), allow_none=True)
    included = fields.String(allow_none=True)
    excluded = fields.String(allow_none=True)
    itinerary = fields.String(allow_none=True)
    status = fields.String(validate=validate.OneOf(["draft", "published", "archived"]))
    featured = fields.Boolean()
    image_url = fields.String(validate=validate.Length(max=500), allow_none=True)
    meta_title = fields.String(validate=validate.Length(max=200), allow_none=True)
    meta_description = fields.String(validate=validate.Length(max=500), allow_none=True)
    youtube_url = fields.String(validate=validate.Length(max=500), allow_none=True)


class TourListQuerySchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    search = fields.String(load_default=None)
    status = fields.String(
        validate=validate.OneOf(["draft", "published", "archived"]),
        load_default=None,
    )
    category_id = fields.UUID(load_default=None)
    destination_id = fields.UUID(load_default=None)
    featured = fields.Boolean(load_default=None)


class CreateTourDateSchema(Schema):
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    price_override = fields.Decimal(as_string=True, allow_none=True)
    max_spots = fields.Integer(allow_none=True)
    status = fields.String(
        validate=validate.OneOf(["available", "full", "cancelled"]),
        load_default="available",
    )


class UpdateTourDateSchema(Schema):
    start_date = fields.Date()
    end_date = fields.Date()
    price_override = fields.Decimal(as_string=True, allow_none=True)
    max_spots = fields.Integer(allow_none=True)
    status = fields.String(validate=validate.OneOf(["available", "full", "cancelled"]))


class CreateGalleryItemSchema(Schema):
    image_url = fields.String(required=True, validate=validate.Length(min=1, max=500))
    caption = fields.String(validate=validate.Length(max=300), allow_none=True)
    sort_order = fields.Integer(load_default=0)


class UpdateGalleryItemSchema(Schema):
    caption = fields.String(validate=validate.Length(max=300), allow_none=True)
    sort_order = fields.Integer()


# ── Response schemas ──────────────────────────────────────────────────────


class CategoryResponseSchema(Schema):
    id = fields.UUID()
    name = fields.String()
    slug = fields.String()
    description = fields.String()
    is_active = fields.Boolean()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class CategoryListResponseSchema(Schema):
    categories = fields.List(fields.Nested(CategoryResponseSchema))
    total = fields.Integer()
    page = fields.Integer()
    per_page = fields.Integer()
    pages = fields.Integer()


class DestinationResponseSchema(Schema):
    id = fields.UUID()
    name = fields.String()
    slug = fields.String()
    country = fields.String()
    description = fields.String()
    image_url = fields.String()
    is_active = fields.Boolean()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class DestinationListResponseSchema(Schema):
    destinations = fields.List(fields.Nested(DestinationResponseSchema))
    total = fields.Integer()
    page = fields.Integer()
    per_page = fields.Integer()
    pages = fields.Integer()


class TourDateResponseSchema(Schema):
    id = fields.UUID()
    tour_id = fields.UUID()
    start_date = fields.Date()
    end_date = fields.Date()
    price_override = fields.Decimal(as_string=True)
    max_spots = fields.Integer()
    spots_booked = fields.Integer()
    status = fields.String()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class GalleryItemResponseSchema(Schema):
    id = fields.UUID()
    tour_id = fields.UUID()
    image_url = fields.String()
    caption = fields.String()
    sort_order = fields.Integer()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class TourCategoryBriefSchema(Schema):
    id = fields.UUID()
    name = fields.String()
    slug = fields.String()


class DestinationBriefSchema(Schema):
    id = fields.UUID()
    name = fields.String()
    slug = fields.String()
    country = fields.String()


class TourResponseSchema(Schema):
    """Tour summary for list views (includes nested categories/destinations)."""
    id = fields.UUID()
    title = fields.String()
    slug = fields.String()
    short_description = fields.String()
    categories = fields.List(fields.Nested(TourCategoryBriefSchema))
    destinations = fields.List(fields.Nested(DestinationBriefSchema))
    price = fields.Decimal(as_string=True)
    currency = fields.String()
    duration_days = fields.Integer()
    duration_nights = fields.Integer()
    status = fields.String()
    featured = fields.Boolean()
    image_url = fields.String()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class TourListResponseSchema(Schema):
    tours = fields.List(fields.Nested(TourResponseSchema))
    total = fields.Integer()
    page = fields.Integer()
    per_page = fields.Integer()
    pages = fields.Integer()


class TourDetailResponseSchema(Schema):
    """Full tour detail with dates and gallery."""
    id = fields.UUID()
    title = fields.String()
    slug = fields.String()
    description = fields.String()
    short_description = fields.String()
    categories = fields.List(fields.Nested(TourCategoryBriefSchema))
    destinations = fields.List(fields.Nested(DestinationBriefSchema))
    price = fields.Decimal(as_string=True)
    currency = fields.String()
    duration_days = fields.Integer()
    duration_nights = fields.Integer()
    max_group_size = fields.Integer()
    difficulty_level = fields.String()
    included = fields.String()
    excluded = fields.String()
    itinerary = fields.String()
    status = fields.String()
    featured = fields.Boolean()
    image_url = fields.String()
    meta_title = fields.String()
    meta_description = fields.String()
    youtube_url = fields.String()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    dates = fields.List(fields.Nested(TourDateResponseSchema))
    gallery = fields.List(fields.Nested(GalleryItemResponseSchema))
