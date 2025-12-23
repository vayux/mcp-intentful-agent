"""Mock backend simulating an existing orders API.

This is a simple FastAPI server that simulates a production backend system.
It provides REST endpoints for order management:
- GET /v1/me/orders/latest: Get the most recent order
- GET /v1/orders/{id}/status: Get order status
- POST /v1/orders/{id}/cancel: Cancel an order (idempotent)
- POST /v1/orders: Create a new order

In a real system, this would be your existing production backend
that the MCP server wraps with intentful tools.
"""
from __future__ import annotations

import random
import string
from typing import Optional

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Mock Orders Backend",
    description="Simulates an existing production backend API",
)

# In-memory "database"
ORDERS: dict[str, dict] = {
    "ORD-12345": {
        "orderId": "ORD-12345",
        "status": "DELAYED",
        "items": [{"name": "Widget", "qty": 2}],
        "total": 49.99,
        "cancelled": False,
    },
    "ORD-67890": {
        "orderId": "ORD-67890",
        "status": "SHIPPED",
        "items": [{"name": "Gadget", "qty": 1}],
        "total": 99.99,
        "cancelled": False,
    },
}

LATEST_ORDER_ID = "ORD-12345"

# Product catalog for the mock
PRODUCTS = {
    "widget": {"name": "Widget", "price": 24.99},
    "gadget": {"name": "Gadget", "price": 99.99},
    "gizmo": {"name": "Gizmo", "price": 49.99},
    "doohickey": {"name": "Doohickey", "price": 19.99},
    "thingamajig": {"name": "Thingamajig", "price": 74.99},
}


class OrderItem(BaseModel):
    product_name: str
    quantity: int = 1


class CreateOrderRequest(BaseModel):
    items: list[OrderItem]


def verify_token(authorization: Optional[str]) -> None:
    """Simple token verification (use proper JWT validation in production)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    # In production: validate JWT signature, expiry, issuer, audience


@app.get("/v1/me/orders/latest")
def get_latest_order(authorization: str = Header(...)):
    """Get the most recent order for the authenticated user."""
    verify_token(authorization)
    order = ORDERS.get(LATEST_ORDER_ID)
    if not order:
        raise HTTPException(status_code=404, detail="No orders found")
    return order


@app.get("/v1/orders/{order_id}/status")
def get_order_status(order_id: str, authorization: str = Header(...)):
    """Get status for a specific order."""
    verify_token(authorization)
    order = ORDERS.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "orderId": order_id,
        "status": order["status"],
        "cancelled": order["cancelled"],
    }


@app.post("/v1/orders/{order_id}/cancel")
def cancel_order(
    order_id: str,
    authorization: str = Header(...),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Cancel an order (idempotent)."""
    verify_token(authorization)
    order = ORDERS.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order["cancelled"]:
        return {
            "orderId": order_id,
            "status": "ALREADY_CANCELLED",
            "idempotencyKey": idempotency_key,
        }

    # Perform cancellation
    order["cancelled"] = True
    order["status"] = "CANCELLED"
    return {
        "orderId": order_id,
        "status": "CANCELLED",
        "idempotencyKey": idempotency_key,
    }


@app.post("/v1/orders")
def create_order(
    request: CreateOrderRequest,
    authorization: str = Header(...),
):
    """Create a new order."""
    global LATEST_ORDER_ID
    verify_token(authorization)

    if not request.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    # Build order items and calculate total
    order_items = []
    total = 0.0

    for item in request.items:
        product_key = item.product_name.lower()
        product = PRODUCTS.get(product_key)
        if not product:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown product: {item.product_name}. Available: {', '.join(PRODUCTS.keys())}",
            )
        order_items.append({"name": product["name"], "qty": item.quantity})
        total += product["price"] * item.quantity

    # Generate order ID
    suffix = "".join(random.choices(string.digits, k=5))
    order_id = f"ORD-{suffix}"

    # Create order
    order = {
        "orderId": order_id,
        "status": "PROCESSING",
        "items": order_items,
        "total": round(total, 2),
        "cancelled": False,
    }
    ORDERS[order_id] = order
    LATEST_ORDER_ID = order_id

    return order


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


def run():
    """Entry point for the mock backend."""
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    run()

