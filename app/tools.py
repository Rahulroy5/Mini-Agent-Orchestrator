import asyncio
import random


async def cancel_order(order_id: str) -> dict:
    # Simulate a real async call such as HTTP/DB request latency.
    await asyncio.sleep(0.2)

    if random.random() < 0.2:
        return {
            "success": False,
            "order_id": order_id,
            "reason": "Cancellation service temporary error",
        }

    return {"success": True, "order_id": order_id}


async def send_email(email: str, message: str) -> dict:
    # Requirement: simulate a 1 second async email sending operation.
    await asyncio.sleep(1)
    return {"success": True, "email": email, "message": message}
