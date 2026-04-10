import asyncio
import random


async def cancel_order(order_id: str) -> dict[str, str | bool]:
    await asyncio.sleep(0.2)
    if random.random() < 0.2:
        return {
            "success": False,
            "order_id": order_id,
            "reason": "Cancellation service temporary error",
        }
    return {"success": True, "order_id": order_id}


async def send_email(email: str, message: str) -> dict[str, str | bool]:
    await asyncio.sleep(1)
    return {"success": True, "email": email, "message": message}
