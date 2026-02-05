function getEls() {
  return {
    emailEl: document.getElementById("email"),
    phoneEl: document.getElementById("phone"),
    passwordEl: document.getElementById("password"),
    msgEl: document.getElementById("msg")
  };
}

function login() {
  const { emailEl, phoneEl, passwordEl, msgEl } = getEls();
  if (!passwordEl || !msgEl) return;
  msgEl.innerText = "";
  fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: emailEl ? emailEl.value.trim() : "",
      phone: phoneEl ? phoneEl.value.trim() : "",
      password: passwordEl.value
    })
  })
    .then(r => r.json().then(data => ({ ok: r.ok, data })).catch(() => ({ ok: false, data: {} })))
    .then(({ ok, data }) => {
      if (ok && data.ok) {
        window.location.replace("/");
      } else {
        msgEl.innerText = data.message || "Erro ao entrar";
      }
    })
    .catch(() => msgEl.innerText = "Erro de ligação ao servidor");
}

function registar() {
  const { emailEl, phoneEl, passwordEl, msgEl } = getEls();
  if (!passwordEl || !msgEl) return;
  msgEl.innerText = "";
  fetch("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: emailEl ? emailEl.value.trim() : "",
      phone: phoneEl ? phoneEl.value.trim() : "",
      password: passwordEl.value
    })
  })
    .then(r => r.json().then(data => ({ ok: r.ok, data })))
    .then(({ ok, data }) => {
      if (ok && data.ok) {
        msgEl.innerText = data.message || "Conta criada com sucesso";
      } else {
        msgEl.innerText = data.message || "Erro ao criar conta";
      }
    })
    .catch(() => msgEl.innerText = "Erro de ligação ao servidor");
}

function loginGoogle() {
  window.location.href = "/auth/google";
}
