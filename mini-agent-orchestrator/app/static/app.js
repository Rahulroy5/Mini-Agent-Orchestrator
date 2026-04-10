const feed = document.getElementById("feed");
const form = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const llmPill = document.getElementById("llm-pill");
const cardTemplate = document.getElementById("card-template");

function shortId() {
  return Math.random().toString(16).slice(2, 10);
}

function setPending(isPending) {
  sendButton.disabled = isPending;
  sendButton.textContent = isPending ? "..." : "→";
}

function renderCard(inputText, payload, isError = false) {
  const fragment = cardTemplate.content.cloneNode(true);

  fragment.querySelector(".entry-id").textContent = shortId();
  fragment.querySelector(".entry-user").textContent = inputText;

  const thinking = payload?.thinking || "No explicit reasoning summary provided.";
  fragment.querySelector(".entry-thinking").textContent = thinking;

  const planList = fragment.querySelector(".entry-plan");
  const stepsList = fragment.querySelector(".entry-steps");

  const plan = Array.isArray(payload?.plan) ? payload.plan : [];
  const steps = Array.isArray(payload?.steps) ? payload.steps : [];

  if (plan.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No tool plan generated.";
    planList.appendChild(li);
  } else {
    for (const task of plan) {
      const li = document.createElement("li");
      const deps = task.depends_on?.length ? ` (depends on: ${task.depends_on.join(", ")})` : "";
      li.textContent = `${task.id}. ${task.action} ${JSON.stringify(task.params)}${deps}`;
      planList.appendChild(li);
    }
  }

  if (steps.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No execution steps were run.";
    stepsList.appendChild(li);
  } else {
    for (const step of steps) {
      const li = document.createElement("li");
      li.textContent = `[${step.status.toUpperCase()}] ${step.action}: ${step.detail}`;
      stepsList.appendChild(li);
    }
  }

  fragment.querySelector(".entry-agent").textContent = payload?.reply || "No response received.";

  const stateNode = fragment.querySelector(".entry-state");
  const workflowStatus = payload?.workflow_status || (isError ? "failed" : "success");
  stateNode.textContent = workflowStatus === "failed" ? "FAILED" : "COMPLETED";

  const card = fragment.querySelector(".entry-card");
  if (isError || workflowStatus === "failed") {
    card.classList.add("error");
  }

  feed.prepend(fragment);
}

async function refreshLLMStatus() {
  try {
    const response = await fetch("/llm-status");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    const online = data.status === "ok";

    llmPill.classList.toggle("online", online);
    llmPill.classList.toggle("offline", !online);
    llmPill.textContent = online
      ? `LLM Online ${data.model}`
      : `LLM Offline ${data.model}`;
  } catch {
    llmPill.classList.remove("online");
    llmPill.classList.add("offline");
    llmPill.textContent = "LLM Offline";
  }
}

async function submitPrompt(message) {
  setPending(true);

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message }),
    });

    const data = await response.json();

    if (!response.ok) {
      const detail = data?.detail || "Unexpected server error";
      renderCard(
        message,
        {
          workflow_status: "failed",
          thinking: "- Request failed before workflow execution.",
          plan: [],
          steps: [],
          reply: String(detail),
        },
        true,
      );
      return;
    }

    renderCard(message, data);
  } catch (error) {
    renderCard(
      message,
      {
        workflow_status: "failed",
        thinking: "- Network failure while contacting backend.",
        plan: [],
        steps: [],
        reply: `Network error: ${error}`,
      },
      true,
    );
  } finally {
    setPending(false);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = messageInput.value.trim();
  if (!message) {
    return;
  }

  messageInput.value = "";
  await submitPrompt(message);
});

for (const chip of document.querySelectorAll(".chip")) {
  chip.addEventListener("click", () => {
    const value = chip.getAttribute("data-suggestion") || "";
    messageInput.value = value;
    messageInput.focus();
  });
}

refreshLLMStatus();
setInterval(refreshLLMStatus, 10000);
