function updateTaskFormForMode(form) {
  const lang = document.documentElement.lang === "zh" ? "zh" : "en";
  const mode = form.querySelector("[name=mode]").value;
  const hint = form.querySelector("#task-mode-hint");
  const emailField = form.querySelector("#task-email-field");
  const passwordField = form.querySelector("#task-password-field");
  const accountCountInput = form.querySelector("[name=account_count]");
  const emailInput = form.querySelector("[name=email]");
  const passwordInput = form.querySelector("[name=password]");
  const trialCheckbox = form.querySelector("[name=generate_trial_link]");

  const text = {
    en: {
      fullHint: "Leave email and password blank in full mode to auto-generate them.",
      fullEmail: "Optional in full mode",
      fullPassword: "Optional in full mode",
      trialHint: "Trial mode needs an existing account email plus password, unless you use a saved session token outside the UI.",
      trialEmail: "Required in trial mode",
      trialPassword: "Required in trial mode",
      browserHint: "Trial-browser mode signs into an existing account. Fill email and password for that account.",
      browserEmail: "Required in trial-browser mode",
      browserPassword: "Required in trial-browser mode",
      uploadHint: "Upload mode does not use email or password from this form.",
    },
    zh: {
      fullHint: "full 模式下邮箱和密码可以留空，系统会自动生成。",
      fullEmail: "full 模式可留空",
      fullPassword: "full 模式可留空",
      trialHint: "trial 模式需要已有账号邮箱和密码，除非在 UI 外提供 session token。",
      trialEmail: "trial 模式必填",
      trialPassword: "trial 模式必填",
      browserHint: "trial-browser 会登录已有账号，请填写该账号邮箱和密码。",
      browserEmail: "trial-browser 模式必填",
      browserPassword: "trial-browser 模式必填",
      uploadHint: "upload 模式不会使用此表单里的邮箱或密码。",
    },
  }[lang];

  const configs = {
    full: {
      hint: text.fullHint,
      showEmail: true,
      showPassword: true,
      showAccountCount: true,
      showTrial: true,
      emailPlaceholder: text.fullEmail,
      passwordPlaceholder: text.fullPassword,
    },
    trial: {
      hint: text.trialHint,
      showEmail: true,
      showPassword: true,
      showAccountCount: false,
      showTrial: false,
      emailPlaceholder: text.trialEmail,
      passwordPlaceholder: text.trialPassword,
    },
    "trial-browser": {
      hint: text.browserHint,
      showEmail: true,
      showPassword: true,
      showAccountCount: false,
      showTrial: false,
      emailPlaceholder: text.browserEmail,
      passwordPlaceholder: text.browserPassword,
    },
    upload: {
      hint: text.uploadHint,
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

async function copyText(button) {
  const originalLabel = button.textContent;
  const value = button.dataset.copyText || "";
  if (!value) {
    return;
  }

  try {
    await navigator.clipboard.writeText(value);
    button.textContent = "Copied";
  } catch {
    button.textContent = "Copy failed";
  }

  window.setTimeout(() => {
    button.textContent = originalLabel;
  }, 1200);
}

function currentLang() {
  return document.documentElement.lang === "zh" ? "zh" : "en";
}

function accountMessages() {
  return {
    en: {
      updating: "Updating...",
      trialing: "Generating...",
      pushing: "Pushing...",
      updateFailed: "Failed to update account",
      trialFailed: "Failed to generate Trial link",
      pushFailed: "Failed to push account",
      deleteFailed: "Failed to delete account",
      deleteConfirm: "Delete this local account record? This will not delete the remote Pool account.",
    },
    zh: {
      updating: "保存中...",
      trialing: "生成中...",
      pushing: "推送中...",
      updateFailed: "账号更新失败",
      trialFailed: "Trial 链接生成失败",
      pushFailed: "推送账号失败",
      deleteFailed: "删除账号失败",
      deleteConfirm: "删除这条本地账号记录？这不会删除远端 Pool 账号。",
    },
  }[currentLang()];
}

async function readJsonError(response, fallbackMessage) {
  const payload = await response.json().catch(() => ({}));
  return payload.detail || fallbackMessage;
}

async function withBusyButton(button, busyLabel, action) {
  const originalLabel = button.textContent;
  button.disabled = true;
  button.textContent = busyLabel;
  try {
    await action();
  } finally {
    button.disabled = false;
    button.textContent = originalLabel;
  }
}

function modalElements() {
  return {
    modal: document.getElementById("account-modal"),
    accountId: document.getElementById("modal-account-id"),
    email: document.getElementById("modal-email"),
    poolStatus: document.getElementById("modal-pool-status"),
    sessionToken: document.getElementById("modal-session-token"),
    trialUrl: document.getElementById("modal-trial-url"),
    ott: document.getElementById("modal-ott"),
  };
}

function openAccountModal(button) {
  const account = JSON.parse(button.dataset.accountJson || "{}");
  const fields = modalElements();
  fields.accountId.value = account.id || "";
  fields.email.value = account.email || "";
  fields.poolStatus.value = account.pool_status || "";
  fields.sessionToken.value = account.session_token || "";
  fields.trialUrl.value = account.trial_checkout_url || "";
  fields.ott.value = account.ott && !account.ott.includes("...") ? account.ott : "";
  fields.modal.showModal();
}

async function saveAccountFromModal() {
  const fields = modalElements();
  const accountId = fields.accountId.value;
  const text = accountMessages();
  const data = {
    email: fields.email.value,
    pool_status: fields.poolStatus.value,
    session_token: fields.sessionToken.value,
    trial_checkout_url: fields.trialUrl.value,
    ott: fields.ott.value,
  };
  const saveButton = document.querySelector("[data-modal-save]");
  await withBusyButton(saveButton, text.updating, async () => {
    const response = await fetch(`/api/accounts/${accountId}`, {
      method: "PATCH",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      alert(await readJsonError(response, text.updateFailed));
      return;
    }
    window.location.reload();
  });
}

async function triggerTrial(button) {
  const text = accountMessages();
  const accountId = button.dataset.accountTrialButton;
  await withBusyButton(button, text.trialing, async () => {
    const response = await fetch(`/api/accounts/${accountId}/trial`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      alert(await readJsonError(response, text.trialFailed));
      return;
    }
    window.location.reload();
  });
}

async function pushAccount(button) {
  const text = accountMessages();
  const accountId = button.dataset.accountPushButton;
  await withBusyButton(button, text.pushing, async () => {
    const response = await fetch(`/api/accounts/${accountId}/push`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      alert(await readJsonError(response, text.pushFailed));
      return;
    }
    window.location.reload();
  });
}

async function deleteAccount(button) {
  const accountId = button.dataset.accountDeleteButton;
  const text = accountMessages();
  if (!window.confirm(text.deleteConfirm)) {
    return;
  }
  const response = await fetch(`/api/accounts/${accountId}`, {method: "DELETE"});
  if (!response.ok) {
    alert(await readJsonError(response, text.deleteFailed));
    return;
  }
  window.location.reload();
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("task-form");
  if (form) {
    updateTaskFormForMode(form);
    form.querySelector("[name=mode]").addEventListener("change", () => updateTaskFormForMode(form));
    form.addEventListener("submit", submitTaskForm);
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-copy-text]");
    if (!button) {
      return;
    }
    copyText(button);
  });

  document.querySelectorAll("[data-account-edit-button]").forEach((button) => {
    button.addEventListener("click", () => openAccountModal(button));
  });

  document.querySelectorAll("[data-account-trial-button]").forEach((button) => {
    button.addEventListener("click", () => triggerTrial(button));
  });

  document.querySelectorAll("[data-account-push-button]").forEach((button) => {
    button.addEventListener("click", () => pushAccount(button));
  });

  document.querySelectorAll("[data-account-delete-button]").forEach((button) => {
    button.addEventListener("click", () => deleteAccount(button));
  });

  const modal = document.getElementById("account-modal");
  if (modal) {
    modal.querySelector("[data-modal-save]").addEventListener("click", saveAccountFromModal);
  }
});
