import re

from app.models.schemas import PlanTask, StepTrace
from app.services.llm_service import OllamaService
from app.services.tools import cancel_order, send_email


ORDER_PATTERN = re.compile(r"(?:order\s*#?|#)(\d+)", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CANCEL_INTENTS = ("cancel", "cancellation", "stop order")
EMAIL_INTENTS = ("email", "mail", "confirmation")
BLOCK_EMAIL_INTENTS = ("don't send", "do not send", "dont send", "no email")
THINKING_LINES = (
    "Parsed the request and looked for actionable tool signals.",
    "Built a minimal execution plan from extracted order/email entities.",
    "Will run dependent steps in order and stop downstream tasks on failure.",
)


def _build_thinking_trace() -> str:
    return "\n".join(f"- {line}" for line in THINKING_LINES)


def _task(task_id: str, action: str, params: dict[str, str], depends_on: list[str] | None = None) -> PlanTask:
    return PlanTask(
        id=task_id,
        action=action,
        params=params,
        depends_on=depends_on or [],
    )


def _extract_intents(message: str) -> tuple[bool, bool, bool]:
    lower = message.lower()
    wants_cancel = any(token in lower for token in CANCEL_INTENTS)
    wants_email = any(token in lower for token in EMAIL_INTENTS)
    blocks_email = any(token in lower for token in BLOCK_EMAIL_INTENTS)
    return wants_cancel, wants_email, blocks_email


def build_plan(message: str) -> tuple[str, list[PlanTask]]:
    order_match = ORDER_PATTERN.search(message)
    email_match = EMAIL_PATTERN.search(message)
    wants_cancel, wants_email, blocks_email = _extract_intents(message)

    tasks: list[PlanTask] = []

    if wants_cancel and order_match:
        order_id = order_match.group(1)
        tasks.append(_task("1", "cancel_order", {"order_id": order_id}))

        if wants_email and email_match and not blocks_email:
            tasks.append(
                _task(
                    "2",
                    "send_email",
                    {
                        "email": email_match.group(0),
                        "message": f"Your order #{order_id} has been cancelled.",
                    },
                    depends_on=["1"],
                )
            )

    return _build_thinking_trace(), tasks


def _success_step(task: PlanTask, detail: str) -> StepTrace:
    return StepTrace(task_id=task.id, action=task.action, status="success", detail=detail)


def _failure_step(task: PlanTask, detail: str) -> StepTrace:
    return StepTrace(task_id=task.id, action=task.action, status="failed", detail=detail)


def _skipped_step(task: PlanTask, detail: str) -> StepTrace:
    return StepTrace(task_id=task.id, action=task.action, status="skipped", detail=detail)


async def _run_cancel_order(task: PlanTask) -> tuple[bool, StepTrace, str]:
    order_id = str(task.params.get("order_id", "")).strip()
    result = await cancel_order(order_id)
    if result.get("success"):
        return True, _success_step(task, f"Order #{order_id} cancelled."), ""

    reason = str(result.get("reason", "Cancellation failed"))
    return False, _failure_step(task, reason), f"Cancellation failed: {reason}"


async def _run_send_email(task: PlanTask) -> tuple[bool, StepTrace, str]:
    email = str(task.params.get("email", "")).strip()
    content = str(task.params.get("message", "Order update"))
    result = await send_email(email, content)
    if result.get("success"):
        return True, _success_step(task, f"Email sent to {email}."), ""

    return False, _failure_step(task, "Email send failed."), "Email send failed"


async def run_plan(tasks: list[PlanTask]) -> tuple[str, list[StepTrace], str]:
    completed: set[str] = set()
    steps: list[StepTrace] = []

    for task in tasks:
        if any(dep not in completed for dep in task.depends_on):
            steps.append(_skipped_step(task, "Skipped because a dependency failed."))
            continue

        if task.action == "cancel_order":
            success, step, summary = await _run_cancel_order(task)
            steps.append(step)
            if not success:
                return "failed", steps, summary
            completed.add(task.id)

        elif task.action == "send_email":
            success, step, summary = await _run_send_email(task)
            steps.append(step)
            if not success:
                return "failed", steps, summary
            completed.add(task.id)

    return "success", steps, "Workflow executed successfully."


async def run_agent_request(
    message: str,
    llm_service: OllamaService,
    system_prompt: str | None = None,
) -> tuple[str, list[PlanTask], list[StepTrace], str, str]:
    thinking, plan = build_plan(message)

    if not plan:
        # Fallback: pure chat reply when no tool-oriented action is detected.
        reply = await llm_service.chat(message, system_prompt)
        return "success", [], [], thinking, reply

    status, steps, summary = await run_plan(plan)
    return status, plan, steps, thinking, summary
