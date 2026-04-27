function updateTaskFormForMode(form) {
  const mode = form.querySelector("[name=mode]").value;
  const hint = form.querySelector("#task-mode-hint");
  const emailField = form.querySelector("#task-email-field");
  const passwordField = form.querySelector("#task-password-field");
  const accountCountInput = form.querySelector("[name=account_count]");
  const emailInput = form.querySelector("[name=email]");
  const passwordInput = form.querySelector("[name=password]");
  const trialCheckbox = form.querySelector("[name=generate_trial_link]");

  const configs = {
    full: {
      hint: "Leave email and password blank in full mode to auto-generate them.",
      showEmail: true,
      showPassword: true,
      showAccountCount: true,
      showTrial: true,
      emailPlaceholder: "Optional in full mode",
      passwordPlaceholder: "Optional in full mode",
    },
    trial: {
      hint: "Trial mode needs an existing account email plus password, unless you use a saved session token outside the UI.",
      showEmail: true,
      showPassword: true,
      showAccountCount: false,
      showTrial: false,
      emailPlaceholder: "Required in trial mode",
      passwordPlaceholder: "Required in trial mode",
    },
    "trial-browser": {
      hint: "Trial-browser mode signs into an existing account. Fill email and password for that account.",
      showEmail: true,
      showPassword: true,
      showAccountCount: false,
      showTrial: false,
      emailPlaceholder: "Required in trial-browser mode",
      passwordPlaceholder: "Required in trial-browser mode",
    },
    upload: {
      hint: "Upload mode does not use email or password from this form.",
      showEmail: false,
      showPassword: false,
      showAccountCount: false,
      showTrial: false,
      emailPlaceholder: "",
      passwordPlaceholder: "",
    },
  };
  const config = configs[mode] || configs.full;

  hint.textContent = config.hint;
  emailField.hidden = !config.showEmail;
  passwordField.hidden = !config.showPassword;
  accountCountInput.closest("label").hidden = !config.showAccountCount;
  trialCheckbox.closest("label").hidden = !config.showTrial;
  emailInput.placeholder = config.emailPlaceholder;
  passwordInput.placeholder = config.passwordPlaceholder;
}

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
    updateTaskFormForMode(form);
    form.querySelector("[name=mode]").addEventListener("change", () => updateTaskFormForMode(form));
    form.addEventListener("submit", submitTaskForm);
  }
});
