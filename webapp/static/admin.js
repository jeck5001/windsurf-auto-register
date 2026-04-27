async function submitTaskForm(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form).entries());
  data.account_count = Number(data.account_count || "1");
  data.generate_trial_link = form.querySelector("[name=generate_trial_link]").checked;

  const response = await fetch("/api/tasks", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    alert("Failed to create task");
    return;
  }
  window.location.reload();
}

function attachTaskEventStream(taskId, target) {
  const source = new EventSource(`/api/tasks/${taskId}/events`);
  source.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    const item = document.createElement("li");
    item.textContent = `${payload.level}: ${payload.message}`;
    target.prepend(item);
  };
  return source;
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("task-form");
  if (form) {
    form.addEventListener("submit", submitTaskForm);
  }
});
