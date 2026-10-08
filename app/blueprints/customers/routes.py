"""Customer management routes."""

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from app.blueprints.customers.schemas import (
    CreateCustomerSchema,
    CustomerDetailResponseSchema,
    CustomerListQuerySchema,
    CustomerListResponseSchema,
    UpdateCustomerSchema,
)
from app.blueprints.customers.services import CustomerService
from app.core.constants import Permissions
from app.core.decorators import audit_action, require_permission
from app.core.exceptions import ValidationError as AppValidationError

customers_bp = Blueprint("customers", __name__)


@customers_bp.route("/", methods=["GET"])
@require_permission(Permissions.CUSTOMERS_VIEW)
def list_customers():
    schema = CustomerListQuerySchema()
    try:
        params = schema.load(request.args)
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = CustomerService.list_customers(
        page=params["page"],
        per_page=params["per_page"],
        search=params.get("search"),
        source=params.get("source"),
        is_active=params.get("is_active"),
    )
    return jsonify(CustomerListResponseSchema().dump(result)), 200


@customers_bp.route("/", methods=["POST"])
@audit_action("customers.create", resource_type="customer")
@require_permission(Permissions.CUSTOMERS_MANAGE)
def create_customer():
    schema = CreateCustomerSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = CustomerService.create_customer(data)
    return jsonify(CustomerDetailResponseSchema().dump(result)), 201


@customers_bp.route("/<uuid:customer_id>", methods=["GET"])
@require_permission(Permissions.CUSTOMERS_VIEW)
def get_customer(customer_id):
    result = CustomerService.get_customer(customer_id)
    return jsonify(CustomerDetailResponseSchema().dump(result)), 200


@customers_bp.route("/<uuid:customer_id>", methods=["PUT"])
@audit_action("customers.update", resource_type="customer",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("customer_id")))
@require_permission(Permissions.CUSTOMERS_MANAGE)
def update_customer(customer_id):
    schema = UpdateCustomerSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = CustomerService.update_customer(customer_id, data)
    return jsonify(CustomerDetailResponseSchema().dump(result)), 200


@customers_bp.route("/<uuid:customer_id>", methods=["DELETE"])
@audit_action("customers.delete", resource_type="customer",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("customer_id")))
@require_permission(Permissions.CUSTOMERS_MANAGE)
def delete_customer(customer_id):
    result = CustomerService.delete_customer(customer_id)
    return jsonify(result), 200
