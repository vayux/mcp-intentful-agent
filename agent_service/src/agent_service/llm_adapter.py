"""LLM adapter with action schema.

This module defines the action schema that the agent uses to determine
next steps in a conversation. It includes:

1. Action types: ToolAction, AskUserAction, FinalAction
2. RuleBasedPlanner: A deterministic planner for POC (replace with LLM)

For production, replace RuleBasedPlanner with a real LLM that outputs
the same Action schema using structured outputs / JSON mode.

Production LLM integration options:
- OpenAI: Use response_format={"type": "json_schema", ...}
- Anthropic: Use tool use with forced tool choice
- Google Vertex AI: Use responseSchema parameter
- Any LLM via Instructor library for structured outputs
"""
from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, Field


class ToolAction(BaseModel):
    """Action: call a tool."""

    type: Literal["tool"] = "tool"
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    why: str | None = None


class AskUserAction(BaseModel):
    """Action: ask user for clarification or confirmation."""

    type: Literal["ask_user"] = "ask_user"
    question: str


class FinalAction(BaseModel):
    """Action: provide final response to user."""

    type: Literal["final"] = "final"
    message: str


Action = Union[ToolAction, AskUserAction, FinalAction]


class RuleBasedPlanner:
    """
    Dev-only planner to keep this example runnable without a live LLM.
    Replace with a real LLM adapter that returns the same Action schema.
    
    Supported intents:
    - Greeting: "hello", "hi", "hey"
    - Order status: "status", "where is my order", "track"
    - Show order: "show order", "latest order", "my order"
    - Cancel order: "cancel", "cancel order"
    - Add order: "add order", "place order", "order", "buy"
    - Help: "help", "what can you do"
    - Confirmation: "yes", "confirm"
    """
    
    # Available products for ordering
    AVAILABLE_PRODUCTS = ["widget", "gadget", "gizmo", "doohickey", "thingamajig"]

    def _detect_intent(self, text: str) -> str:
        """Simple keyword-based intent detection."""
        lower = text.lower().strip()
        
        # Greeting
        if any(word in lower for word in ["hello", "hi", "hey", "good morning", "good afternoon"]):
            return "greeting"
        
        # Help
        if any(phrase in lower for phrase in ["help", "what can you do", "what do you do", "capabilities"]):
            return "help"
        
        # Cancel intent (must be before add_order to avoid "cancel" matching "add order")
        if "cancel" in lower and "order" not in lower.replace("cancel", ""):
            return "cancel"
        if lower.startswith("cancel"):
            return "cancel"
        
        # Add order intent - check for product names or ordering phrases
        order_phrases = ["add order", "place order", "create order", "new order", "buy", "order a", "want to order", "i want", "get me"]
        if any(phrase in lower for phrase in order_phrases):
            return "add_order"
        # Check if they mention a product name (handle plurals too)
        product_mentioned = any(
            product in lower or f"{product}s" in lower 
            for product in self.AVAILABLE_PRODUCTS
        )
        if product_mentioned:
            if any(word in lower for word in ["order", "buy", "want", "get", "add"]):
                return "add_order"
        # "Order X widgets" pattern
        if lower.startswith("order ") and product_mentioned:
            return "add_order"
        
        # Cancel intent (catch remaining cases)
        if "cancel" in lower:
            return "cancel"
        
        # Status intent
        if any(phrase in lower for phrase in ["status", "where is", "track", "tracking", "when will"]):
            return "status"
        
        # Show order intent
        if any(phrase in lower for phrase in ["show", "latest order", "my order", "order details", "what order"]):
            return "show_order"
        
        # Confirmation
        if lower in {"yes", "yes, cancel it", "yes cancel it", "confirm", "confirm cancel", "ok", "sure", "do it", "yes please", "proceed"}:
            return "confirm"
        
        # Decline
        if lower in {"no", "no thanks", "never mind", "cancel that", "don't", "stop"}:
            return "decline"
        
        # Default - try to understand
        return "unknown"
    
    def _extract_order_items(self, text: str) -> list[dict]:
        """Extract product names and quantities from text."""
        import re
        lower = text.lower()
        items = []
        
        for product in self.AVAILABLE_PRODUCTS:
            if product in lower:
                # Try to find quantity (e.g., "2 widgets", "3x gadget")
                quantity = 1
                # Pattern: number followed by product name
                pattern = rf"(\d+)\s*x?\s*{product}s?"
                match = re.search(pattern, lower)
                if match:
                    quantity = int(match.group(1))
                else:
                    # Pattern: product name followed by number
                    pattern = rf"{product}s?\s*x?\s*(\d+)"
                    match = re.search(pattern, lower)
                    if match:
                        quantity = int(match.group(1))
                
                items.append({"product_name": product, "quantity": min(quantity, 100)})
        
        return items

    def next_action(self, user_text: str, tool_results: list[dict]) -> Action:
        """Determine the next action based on user input and tool results."""
        intent = self._detect_intent(user_text)
        last_result = tool_results[-1] if tool_results else {}
        
        # Only show success messages if there's no new user intent requiring action
        # This prevents showing "Order placed successfully!" when user wants to cancel/check status
        if not user_text or intent in ("greeting", "help", "unknown"):
            # First, check if the last result is a successful action (order created, cancelled, etc.)
            # This prevents re-asking for confirmation after success
            if isinstance(last_result, dict) and last_result.get("ok"):
                # Check for successful order creation
                if last_result.get("order") and last_result["order"].get("status") == "PROCESSING":
                    order = last_result["order"]
                    items = order.get("items", [])
                    items_str = ", ".join(f"{i['name']} x{i['qty']}" for i in items)
                    return FinalAction(
                        message=f"Order placed successfully!\n\n"
                                f"- Order ID: {order.get('orderId')}\n"
                                f"- Items: {items_str}\n"
                                f"- Total: ${order.get('total', 0):.2f}\n"
                                f"- Status: {order.get('status')}"
                    )
                # Check for successful cancellation
                if last_result.get("result"):
                    result = last_result["result"]
                    if isinstance(result, dict):
                        status = result.get("status")
                        if status == "CANCELLED":
                            return FinalAction(message="Your order has been cancelled successfully.")
                        if status == "ALREADY_CANCELLED":
                            return FinalAction(message="This order was already cancelled.")
        
        # Check if user is responding to a confirmation request
        # This must happen BEFORE the CONFIRMATION_REQUIRED check to allow confirmations
        if intent in ("confirm", "decline") and tool_results:
            # User is responding - let the intent handling below take care of it
            pass
        else:
            # Handle CONFIRMATION_REQUIRED from tool (only if not confirming/declining)
            for r in tool_results[-2:]:
                err = (r or {}).get("error") if isinstance(r, dict) else None
                if err and err.get("code") == "CONFIRMATION_REQUIRED":
                    details = err.get("details", {})
                    # Check if this is an order creation confirmation
                    if "items" in details:
                        items = details.get("items", [])
                        items_summary = ", ".join(f"{i['quantity']}x {i['product_name']}" for i in items)
                        return AskUserAction(
                            question=f"Ready to place order for: {items_summary}. Reply 'Yes' to confirm or 'No' to cancel."
                        )
                    # Default to cancellation confirmation
                    return AskUserAction(
                        question='I need your confirmation to proceed. Reply "Yes" to confirm or "No" to cancel.'
                    )

        # === Handle different intents ===
        
        # Greeting
        if intent == "greeting":
            return FinalAction(
                message="Hello! I'm your order assistant. I can help you:\n"
                        "- Check your order status\n"
                        "- Show your latest order details\n"
                        "- Cancel delayed orders\n"
                        "- Place a new order\n\n"
                        "What would you like to do?"
            )
        
        # Help
        if intent == "help":
            products = ", ".join(self.AVAILABLE_PRODUCTS)
            return FinalAction(
                message="I can help you with:\n\n"
                        "**Check order status** - Ask \"What's my order status?\"\n"
                        "**View order details** - Ask \"Show my latest order\"\n"
                        "**Cancel orders** - Ask \"Cancel my order\" (only delayed orders can be cancelled)\n"
                        f"**Place an order** - Ask \"Order 2 widgets\" (available: {products})\n\n"
                        "Just type your question!"
            )
        
        # Decline (user says no to cancellation or order)
        if intent == "decline":
            return FinalAction(
                message="No problem! Let me know if you need anything else."
            )
        
        # Add order intent
        if intent == "add_order":
            items = self._extract_order_items(user_text)
            if not items:
                products = ", ".join(self.AVAILABLE_PRODUCTS)
                return AskUserAction(
                    question=f"What would you like to order? Available products: {products}. "
                             "You can say something like 'Order 2 widgets and 1 gadget'."
                )
            
            # Store pending order in tool_results for confirmation flow
            items_summary = ", ".join(f"{i['quantity']}x {i['product_name']}" for i in items)
            return ToolAction(
                tool="create_order",
                args={"items": items, "confirmed": False},
                why=f"Creating order for: {items_summary}",
            )
        
        # Confirmation - user wants to proceed with pending action
        if intent == "confirm":
            # Check if we have a pending order creation
            for r in reversed(tool_results):
                if isinstance(r, dict):
                    err = r.get("error")
                    if err and err.get("code") == "CONFIRMATION_REQUIRED":
                        details = err.get("details", {})
                        # Order creation confirmation
                        if "items" in details:
                            items = details.get("items", [])
                            return ToolAction(
                                tool="create_order",
                                args={"items": items, "confirmed": True},
                                why="User confirmed order placement.",
                            )
            
            # Check for cancellation flow
            order_id = None
            for r in reversed(tool_results):
                if isinstance(r, dict) and r.get("order"):
                    order_id = r["order"].get("orderId") or r["order"].get("order_id")
                    break
                if isinstance(r, dict) and r.get("status"):
                    order_id = r["status"].get("orderId")
                    break
            
            if not order_id:
                return ToolAction(
                    tool="get_latest_order",
                    args={},
                    why="Need to find the order before cancelling.",
                )
            return ToolAction(
                tool="request_order_cancellation",
                args={"order_id": order_id, "confirmed": True},
                why="User confirmed cancellation.",
            )
        
        # Show order - just get the latest order
        if intent == "show_order":
            if isinstance(last_result, dict) and last_result.get("order"):
                order = last_result["order"]
                items = order.get("items", [])
                items_str = ", ".join(f"{i['name']} x{i['qty']}" for i in items) if items else "N/A"
                return FinalAction(
                    message=f"**Your Latest Order**\n\n"
                            f"- Order ID: {order.get('orderId')}\n"
                            f"- Status: {order.get('status')}\n"
                            f"- Items: {items_str}\n"
                            f"- Total: ${order.get('total', 0):.2f}"
                )
            return ToolAction(
                tool="get_latest_order",
                args={},
                why="User wants to see their order.",
            )
        
        # Status check
        if intent == "status":
            # If we already have status, show it
            if isinstance(last_result, dict) and last_result.get("status"):
                status_info = last_result["status"]
                status = status_info.get("status", "Unknown")
                order_id = status_info.get("orderId", "N/A")
                
                msg = f"**Order Status**\n\nOrder {order_id} is currently: {status}"
                
                if status == "DELAYED":
                    msg += "\n\nWould you like me to cancel this order? Reply \"Yes\" to cancel."
                
                return FinalAction(message=msg)
            
            # If we have order but no status, get status
            if isinstance(last_result, dict) and last_result.get("order"):
                order_id = last_result["order"].get("orderId") or last_result["order"].get("order_id")
                return ToolAction(
                    tool="get_order_status",
                    args={"order_id": order_id},
                    why="Getting order status.",
                )
            
            # No data yet, get order first
            return ToolAction(
                tool="get_latest_order",
                args={},
                why="Need to get order before checking status.",
            )
        
        # Cancel intent
        if intent == "cancel":
            # If we have status showing DELAYED, ask for confirmation
            if isinstance(last_result, dict) and last_result.get("status"):
                status = last_result["status"].get("status")
                if status == "DELAYED":
                    return AskUserAction(
                        question='Your order is delayed. Would you like me to cancel it? Reply "Yes" to confirm.'
                    )
                elif status == "CANCELLED":
                    return FinalAction(message="This order has already been cancelled.")
                else:
                    return FinalAction(
                        message=f"Your order status is {status}. Only delayed orders can be cancelled. "
                                "Would you like me to check if there's an issue with your order?"
                    )
            
            # If we have order info, check if it's cancellable
            if isinstance(last_result, dict) and last_result.get("order"):
                order = last_result["order"]
                if order.get("cancelled"):
                    return FinalAction(message="This order has already been cancelled.")
                order_id = order.get("orderId") or order.get("order_id")
                return ToolAction(
                    tool="get_order_status",
                    args={"order_id": order_id},
                    why="Checking order status before cancellation.",
                )
            
            # No data, get order first
            return ToolAction(
                tool="get_latest_order",
                args={},
                why="Need to find order to cancel.",
            )
        
        # === Handle tool results (for ongoing flows) ===
        
        # After getting order, check status
        if isinstance(last_result, dict) and last_result.get("order"):
            order_id = last_result["order"].get("orderId") or last_result["order"].get("order_id")
            return ToolAction(
                tool="get_order_status",
                args={"order_id": order_id},
                why="Checking order status.",
            )
        
        # After getting status, respond appropriately
        if isinstance(last_result, dict) and last_result.get("status"):
            status_info = last_result["status"]
            status = status_info.get("status")
            
            if status == "DELAYED":
                return AskUserAction(
                    question=f'Your latest order is DELAYED. Would you like me to cancel it? Reply "Yes" to cancel or "No" to keep it.'
                )
            
            return FinalAction(
                message=f"Your order status is: {status}. Let me know if you need anything else!"
            )
        
        # Handle cancellation result
        if isinstance(last_result, dict) and last_result.get("result"):
            cancel_result = last_result["result"]
            if isinstance(cancel_result, dict):
                cancel_status = cancel_result.get("status")
                if cancel_status == "CANCELLED":
                    return FinalAction(message="Your order has been cancelled successfully.")
                if cancel_status == "ALREADY_CANCELLED":
                    return FinalAction(message="This order was already cancelled.")
        
        # Handle successful order creation
        if isinstance(last_result, dict) and last_result.get("ok") and last_result.get("order"):
            order = last_result["order"]
            # Check if this is a new order (PROCESSING status)
            if order.get("status") == "PROCESSING":
                items = order.get("items", [])
                items_str = ", ".join(f"{i['name']} x{i['qty']}" for i in items)
                return FinalAction(
                    message=f"Order placed successfully!\n\n"
                            f"- Order ID: {order.get('orderId')}\n"
                            f"- Items: {items_str}\n"
                            f"- Total: ${order.get('total', 0):.2f}\n"
                            f"- Status: {order.get('status')}"
                )
        
        # Unknown intent with no context - start fresh
        if not tool_results:
            return ToolAction(
                tool="get_latest_order",
                args={},
                why="Starting fresh - getting latest order.",
            )
        
        # Default fallback
        products = ", ".join(self.AVAILABLE_PRODUCTS)
        return FinalAction(
            message="I'm not sure what you'd like to do. I can help you:\n"
                    "- Check your order status\n"
                    "- Show your order details\n"
                    "- Cancel a delayed order\n"
                    f"- Place a new order (available: {products})\n\n"
                    "What would you like?"
        )
