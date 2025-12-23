"""Async HTTP client for the existing backend API.

This client wraps the backend REST API with:
- Automatic retries with exponential backoff
- Timeout configuration
- Structured error handling
"""
from __future__ import annotations

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from mcp_server.errors import ToolError


class ExistingBackendClient:
    """Async HTTP client for the existing backend API."""

    def __init__(self, base_url: str, access_token: str):
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {access_token}"}
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=httpx.Timeout(5.0, connect=2.0),
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    def _raise_for_status(self, resp: httpx.Response) -> None:
        """Convert HTTP errors to ToolError."""
        if resp.status_code == 401:
            raise ToolError("UNAUTHORIZED", "Unauthorized")
        if resp.status_code == 403:
            raise ToolError("FORBIDDEN", "Forbidden")
        if resp.status_code == 404:
            raise ToolError("NOT_FOUND", "Not found")
        if resp.is_error:
            raise ToolError(
                "UPSTREAM_ERROR",
                "Backend error",
                {"status": resp.status_code, "body": resp.text[:500]},
            )

    @retry(
        reraise=True,
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.2, min=0.2, max=1.0),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
    )
    async def get_latest_order(self) -> dict:
        """Get the latest order for the authenticated user."""
        try:
            resp = await self._client.get("/v1/me/orders/latest")
            self._raise_for_status(resp)
            return resp.json()
        except httpx.TimeoutException:
            raise ToolError("UPSTREAM_TIMEOUT", "Backend timeout")

    @retry(
        reraise=True,
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.2, min=0.2, max=1.0),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
    )
    async def get_order_status(self, order_id: str) -> dict:
        """Get status for a specific order."""
        try:
            resp = await self._client.get(f"/v1/orders/{order_id}/status")
            self._raise_for_status(resp)
            return resp.json()
        except httpx.TimeoutException:
            raise ToolError("UPSTREAM_TIMEOUT", "Backend timeout")

    @retry(
        reraise=True,
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.2, min=0.2, max=1.0),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
    )
    async def request_cancellation(self, order_id: str, idempotency_key: str) -> dict:
        """Request order cancellation (idempotent)."""
        try:
            resp = await self._client.post(
                f"/v1/orders/{order_id}/cancel",
                headers={"Idempotency-Key": idempotency_key},
                json={},
            )
            self._raise_for_status(resp)
            return resp.json()
        except httpx.TimeoutException:
            raise ToolError("UPSTREAM_TIMEOUT", "Backend timeout")

    @retry(
        reraise=True,
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=0.2, min=0.2, max=1.0),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
    )
    async def create_order(self, items: list[dict]) -> dict:
        """Create a new order with the given items."""
        try:
            resp = await self._client.post(
                "/v1/orders",
                json={"items": items},
            )
            self._raise_for_status(resp)
            return resp.json()
        except httpx.TimeoutException:
            raise ToolError("UPSTREAM_TIMEOUT", "Backend timeout")

