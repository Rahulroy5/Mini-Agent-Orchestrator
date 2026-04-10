from collections import deque

from app.schemas import AgentEvent, AgentResponse, Plan, TaskResult
from app.tools import cancel_order, send_email


class Orchestrator:
    async def run(self, plan: Plan) -> AgentResponse:
        events: list[AgentEvent] = [
            AgentEvent(type="workflow_started", detail={"task_count": len(plan.tasks)})
        ]
        results: list[TaskResult] = []
        successful_tasks: set[str] = set()
        task_map = {task.id: task for task in plan.tasks}
        queue = deque(plan.tasks)

        while queue:
            task = queue.popleft()

            if any(dep not in successful_tasks for dep in task.depends_on):
                queue.append(task)

                # No progress possible: dependency chain failed or cyclic dependency.
                if all(any(dep not in successful_tasks for dep in t.depends_on) for t in queue):
                    failure_message = "Workflow halted because required prior task failed"
                    events.append(AgentEvent(type="workflow_failed", detail={"reason": failure_message}))
                    return AgentResponse(
                        status="failed",
                        message=failure_message,
                        plan=plan,
                        steps=results,
                        events=events,
                    )

                continue

            events.append(
                AgentEvent(
                    type="task_started",
                    detail={"task_id": task.id, "action": task.action},
                )
            )

            result = await self._execute_task(task.action, task.params)
            task_result = TaskResult(
                task_id=task.id,
                action=task.action,
                success=result.get("success", False),
                result=result,
                error=None if result.get("success", False) else result.get("reason", "Task failed"),
            )
            results.append(task_result)

            if task_result.success:
                successful_tasks.add(task.id)
                events.append(
                    AgentEvent(
                        type="task_succeeded",
                        detail={"task_id": task.id, "action": task.action},
                    )
                )
            else:
                events.append(
                    AgentEvent(
                        type="task_failed",
                        detail={"task_id": task.id, "action": task.action, "error": task_result.error},
                    )
                )

                blocked = [t.id for t in task_map.values() if task.id in t.depends_on]
                if blocked:
                    events.append(
                        AgentEvent(
                            type="downstream_tasks_skipped",
                            detail={"blocked_by": task.id, "skipped_task_ids": blocked},
                        )
                    )

                return AgentResponse(
                    status="failed",
                    message=f"Task {task.action} failed: {task_result.error}",
                    plan=plan,
                    steps=results,
                    events=events,
                )

        events.append(AgentEvent(type="workflow_succeeded", detail={"completed_tasks": len(results)}))
        return AgentResponse(
            status="success",
            message="Order request processed successfully",
            plan=plan,
            steps=results,
            events=events,
        )

    async def _execute_task(self, action: str, params: dict) -> dict:
        if action == "cancel_order":
            order_id = str(params.get("order_id", "")).strip()
            if not order_id:
                return {"success": False, "reason": "Missing order_id"}
            return await cancel_order(order_id)

        if action == "send_email":
            email = str(params.get("email", "")).strip()
            message = str(params.get("message", "Your order has been updated.")).strip()
            if not email:
                return {"success": False, "reason": "Missing email"}
            return await send_email(email, message)

        return {"success": False, "reason": f"Unknown action: {action}"}
