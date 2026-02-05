let medicamentos = [];
let tomas = [];
let lastAlertKey = null;
let currentAlertMed = null;
let editingId = null;
let currentMonth = new Date();
let filterStart = null;
let filterEnd = null;

function logout() {
  fetch("/auth/logout", { method: "POST" })
    .then(() => window.location.replace("/login"))
    .catch(() => window.location.replace("/login"));
}

function setFormMsg(text) {
  const el = document.getElementById("formMsg");
  if (el) el.innerText = text || "";
}

function renderList() {
  const list = document.getElementById("medList");
  const empty = document.getElementById("emptyState");
  const nextEl = document.getElementById("nextMed");
  if (!list || !empty) return;

  const todayStr = new Date().toISOString().slice(0, 10);
  list.innerHTML = "";
  if (!medicamentos.length) {
    empty.style.display = "block";
    if (nextEl) nextEl.querySelector(".next-value").innerText = "—";
    return;
  }

  empty.style.display = "none";
  const sorted = [...medicamentos].sort((a, b) => (a.hora || "").localeCompare(b.hora || ""));
  sorted.forEach(med => {
    const item = document.createElement("div");
    item.className = "med-item";

    if (String(editingId) === String(med.id)) {
      item.innerHTML = `
        <div>
          <div class="field">
            <label>Nome</label>
            <input id="editNome" value="${med.nome}">
          </div>
          <div class="field">
            <label>Dose</label>
            <input id="editDose" value="${med.dose}">
          </div>
          <div class="field">
            <label>Hora</label>
            <input id="editHora" type="time" value="${med.hora}">
          </div>
          <div class="field">
            <label>Data</label>
            <input id="editData" type="date" value="${med.data || ''}" min="${todayStr}">
          </div>
        </div>
        <div class="actions">
          <button class="edit-btn" data-id="${med.id}" data-action="save">Guardar</button>
          <button class="ghost-btn small-btn" data-id="${med.id}" data-action="cancel">Cancelar</button>
        </div>
      `;
    } else {
      item.innerHTML = `
        <div>
          <div class="med-title">${med.nome}</div>
          <div class="med-meta">${med.dose} • ${med.hora}${med.data ? ' • ' + med.data : ''}</div>
        </div>
        <div class="actions">
          <button class="take-btn" data-id="${med.id}">Tomei agora</button>
          <button class="edit-btn" data-id="${med.id}" data-action="edit">Editar</button>
          <button class="delete-btn" data-id="${med.id}">Apagar</button>
        </div>
      `;
    }

    list.appendChild(item);
  });

  list.querySelectorAll(".delete-btn").forEach(btn => {
    btn.addEventListener("click", () => apagarMedicamento(btn.dataset.id));
  });
  list.querySelectorAll(".edit-btn").forEach(btn => {
    const action = btn.dataset.action || "edit";
    if (action === "edit") btn.addEventListener("click", () => iniciarEdicao(btn.dataset.id));
    if (action === "save") btn.addEventListener("click", () => atualizarMedicamento(btn.dataset.id));
  });
  list.querySelectorAll(".ghost-btn").forEach(btn => {
    if (btn.dataset.action === "cancel") btn.addEventListener("click", cancelarEdicao);
  });
  list.querySelectorAll(".take-btn").forEach(btn => {
    btn.addEventListener("click", () => tomarAgora(btn.dataset.id));
  });

  if (nextEl) {
    const next = getNextMed(sorted);
    nextEl.querySelector(".next-value").innerText = next ? next : "—";
  }
}

function guardar() {
  setFormMsg("");
  if (!nome.value.trim() || !dose.value.trim() || !hora.value || !data.value) {
    setFormMsg("Preenche nome, dose, hora e data.");
    return;
  }
  if (!isDateTodayOrFuture(data.value)) {
    setFormMsg("A data tem de ser hoje ou no futuro.");
    return;
  }

  fetch("/api/medicamentos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      nome: nome.value.trim(),
      dose: dose.value.trim(),
      hora: hora.value,
      data: data.value
    })
  })
    .then(r => r.json().then(data => ({ ok: r.ok, data })))
    .then(({ ok, data }) => {
      if (ok && data.ok) {
        medicamentos.push({
          id: data.id,
          nome: nome.value.trim(),
          dose: dose.value.trim(),
          hora: hora.value,
          data: data.value
        });
        nome.value = "";
        dose.value = "";
        hora.value = "";
        data.value = "";
        renderList();
      } else {
        setFormMsg(data.message || "Erro ao guardar");
      }
    })
    .catch(() => setFormMsg("Erro de ligação ao servidor"));
}

function iniciarEdicao(id) {
  editingId = id;
  renderList();
}

function cancelarEdicao() {
  editingId = null;
  renderList();
}

function atualizarMedicamento(id) {
  const nomeEl = document.getElementById("editNome");
  const doseEl = document.getElementById("editDose");
  const horaEl = document.getElementById("editHora");
  const dataEl = document.getElementById("editData");
  if (!nomeEl || !doseEl || !horaEl || !dataEl) return;

  const nomeVal = nomeEl.value.trim();
  const doseVal = doseEl.value.trim();
  const horaVal = horaEl.value;
  const dataVal = dataEl.value;
  if (!nomeVal || !doseVal || !horaVal || !dataVal) {
    setFormMsg("Preenche nome, dose, hora e data.");
    return;
  }
  if (!isDateTodayOrFuture(dataVal)) {
    setFormMsg("A data tem de ser hoje ou no futuro.");
    return;
  }

  fetch(`/api/medicamentos/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      nome: nomeVal,
      dose: doseVal,
      hora: horaVal,
      data: dataVal
    })
  })
    .then(r => r.json().then(data => ({ ok: r.ok, data })))
    .then(({ ok, data }) => {
      if (ok && data.ok) {
        const idx = medicamentos.findIndex(m => String(m.id) === String(id));
        if (idx >= 0) {
          medicamentos[idx].nome = nomeVal;
          medicamentos[idx].dose = doseVal;
          medicamentos[idx].hora = horaVal;
          medicamentos[idx].data = dataVal;
        }
        editingId = null;
        renderList();
      } else {
        setFormMsg(data.message || "Erro ao atualizar");
      }
    })
    .catch(() => setFormMsg("Erro de ligação ao servidor"));
}

function apagarMedicamento(id) {
  fetch(`/api/medicamentos/${id}`, { method: "DELETE" })
    .then(r => r.json().then(data => ({ ok: r.ok, data })))
    .then(({ ok, data }) => {
      if (ok && data.ok) {
        medicamentos = medicamentos.filter(m => String(m.id) !== String(id));
        renderList();
      }
    })
    .catch(() => {});
}

function carregarMedicamentos() {
  fetch("/api/medicamentos")
    .then(r => {
      if (r.status === 401 || r.status === 302) {
        window.location.replace("/login");
        return null;
      }
      return r.json();
    })
    .then(data => {
      if (Array.isArray(data)) medicamentos = data;
      renderList();
    })
    .catch(() => {});
}

function ativarNotificacoes() {
  if (!("Notification" in window)) {
    setFormMsg("Este navegador não suporta notificações.");
    return;
  }
  if (Notification.permission === "granted") {
    setFormMsg("Notificações já estão ativas.");
    return;
  }
  Notification.requestPermission().then(p => {
    updateNotifBtn();
    if (p === "granted") {
      setFormMsg("Notificações ativadas.");
    } else {
      setFormMsg("Permissão recusada.");
    }
  });
}

function updateNotifBtn() {
  const btn = document.getElementById("notifBtn");
  if (!btn || !("Notification" in window)) return;
  if (Notification.permission === "granted") btn.innerText = "Notificações ativas";
  else if (Notification.permission === "denied") btn.innerText = "Notificações bloqueadas";
  else btn.innerText = "Ativar notificações";
}

function notifyNow(med) {
  if (!("Notification" in window)) return;
  if (Notification.permission !== "granted") return;
  navigator.serviceWorker?.ready
    .then(reg => {
      reg.showNotification("Hora do medicamento", {
        body: `${med.nome} • ${med.dose}`
      });
    })
    .catch(() => {
      new Notification("Hora do medicamento", { body: `${med.nome} • ${med.dose}` });
    });
}

function tomarAgora(id) {
  const med = medicamentos.find(m => String(m.id) === String(id));
  if (!med) return;
  const nota = pedirNota();
  fetch(`/api/medicamentos/${id}/take`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nota })
  })
    .then(r => r.json().then(data => ({ ok: r.ok, data })))
    .then(({ ok, data }) => {
      if (ok && data.ok) {
        medicamentos = medicamentos.filter(m => String(m.id) !== String(id));
        renderList();
        carregarTomas();
        setFormMsg(`Registado e removido: ${med.nome}`);
      }
    })
    .catch(() => {});
}

function carregarTomas() {
  const month = currentMonth.toISOString().slice(0, 7);
  const params = new URLSearchParams();
  if (filterStart) params.set("start", filterStart);
  if (filterEnd) params.set("end", filterEnd);
  if (!filterStart && !filterEnd) params.set("month", month);
  fetch(`/api/tomas?${params.toString()}`)
    .then(r => r.json())
    .then(data => {
      if (Array.isArray(data)) tomas = data;
      renderCalendar();
      renderTomasList();
    })
    .catch(() => {});
}

function renderTomasList() {
  const list = document.getElementById("tomasList");
  const empty = document.getElementById("tomasEmpty");
  if (!list || !empty) return;
  list.innerHTML = "";
  if (!tomas.length) {
    empty.style.display = "block";
    return;
  }
  empty.style.display = "none";
  tomas.forEach(t => {
    const item = document.createElement("div");
    item.className = "toma-item";
    item.innerHTML = `
      <div>
        <div class="med-title">${t.nome}</div>
        <div class="med-meta">${t.dose}${t.nota ? ' • ' + t.nota : ''}</div>
      </div>
      <div class="toma-time">${t.data} • ${t.hora}</div>
    `;
    list.appendChild(item);
  });
}

function renderCalendar() {
  const grid = document.getElementById("calGrid");
  const title = document.getElementById("calTitle");
  if (!grid || !title) return;

  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();
  const first = new Date(year, month, 1);
  const startDay = first.getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const prevDays = new Date(year, month, 0).getDate();

  title.innerText = currentMonth.toLocaleString("pt-PT", { month: "long", year: "numeric" });
  grid.innerHTML = "";

  const weekdays = ["D", "S", "T", "Q", "Q", "S", "S"];
  weekdays.forEach(w => {
    const head = document.createElement("div");
    head.className = "cal-day cal-head";
    head.innerText = w;
    grid.appendChild(head);
  });

  const days = [];
  for (let i = startDay - 1; i >= 0; i--) {
    days.push({ num: prevDays - i, muted: true, date: new Date(year, month - 1, prevDays - i) });
  }
  for (let d = 1; d <= daysInMonth; d++) {
    days.push({ num: d, muted: false, date: new Date(year, month, d) });
  }
  while (days.length % 7 !== 0) {
    const n = days.length - (startDay + daysInMonth) + 1;
    days.push({ num: n, muted: true, date: new Date(year, month + 1, n) });
  }

  const daysWithTomas = new Set(tomas.map(t => t.data));

  days.forEach(d => {
    const cell = document.createElement("div");
    cell.className = `cal-day${d.muted ? " muted" : ""}`;
    const iso = d.date.toISOString().slice(0, 10);
    cell.innerHTML = `
      <div class="cal-num">${d.num}</div>
      ${daysWithTomas.has(iso) ? '<div class="cal-dot"></div>' : ''}
    `;
    grid.appendChild(cell);
  });
}

function prevMonth() {
  currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1);
  carregarTomas();
}

function nextMonth() {
  currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1);
  carregarTomas();
}

function pedirNota() {
  const nota = prompt("Observação (opcional):") || "";
  return nota.trim();
}

function aplicarFiltro() {
  const s = document.getElementById("fStart");
  const e = document.getElementById("fEnd");
  filterStart = s && s.value ? s.value : null;
  filterEnd = e && e.value ? e.value : null;
  carregarTomas();
}

function limparFiltro() {
  const s = document.getElementById("fStart");
  const e = document.getElementById("fEnd");
  if (s) s.value = "";
  if (e) e.value = "";
  filterStart = null;
  filterEnd = null;
  carregarTomas();
}

function exportarHistorico() {
  const params = new URLSearchParams();
  if (filterStart) params.set("start", filterStart);
  if (filterEnd) params.set("end", filterEnd);
  if (!filterStart && !filterEnd) {
    const month = currentMonth.toISOString().slice(0, 7);
    params.set("month", month);
  }
  window.location.href = `/api/tomas/export?${params.toString()}`;
}

function getNextMed(list) {
  if (!list.length) return null;
  const now = new Date();
  const nowMinutes = now.getHours() * 60 + now.getMinutes();
  let candidate = null;
  let candidateMinutes = null;
  let day = "hoje";

  list.forEach(med => {
    if (!med.hora) return;
    const [hh, mm] = med.hora.split(":");
    const mins = (+hh) * 60 + (+mm);
    if (mins >= nowMinutes && (candidateMinutes === null || mins < candidateMinutes)) {
      candidate = med;
      candidateMinutes = mins;
      day = "hoje";
    }
  });

  if (!candidate) {
    list.forEach(med => {
      if (!med.hora) return;
      const [hh, mm] = med.hora.split(":");
      const mins = (+hh) * 60 + (+mm);
      if (candidateMinutes === null || mins < candidateMinutes) {
        candidate = med;
        candidateMinutes = mins;
        day = "amanhã";
      }
    });
  }

  return candidate ? `${candidate.nome} • ${candidate.dose} • às ${candidate.hora} (${day})` : null;
}

setInterval(() => {
  const agora = new Date();
  const h = agora.getHours();
  const m = agora.getMinutes();
  const minuteKey = `${h}:${m}`;

  medicamentos.forEach(med => {
    if (!med.hora) return;
    const [hh, mm] = med.hora.split(":");
    if (+hh === h && +mm === m) {
      const key = `${med.id}-${minuteKey}`;
      if (lastAlertKey === key) return;
      lastAlertKey = key;
      alertaTexto.innerText =
        `Está na hora de tomar ${med.nome} (${med.dose})`;
      alerta.style.display = "flex";
      som.play();
      notifyNow(med);
      currentAlertMed = med;
    }
  });
}, 60000);

carregarMedicamentos();
carregarTomas();
updateNotifBtn();
setDefaultDate();
setMinDateInputs();

function setDefaultDate() {
  if (typeof data === "undefined" || !data) return;
  if (!data.value) {
    const today = new Date().toISOString().slice(0, 10);
    data.value = today;
  }
}

function setMinDateInputs() {
  const today = new Date().toISOString().slice(0, 10);
  const dataInput = document.getElementById("data");
  if (dataInput) dataInput.min = today;
}

function isDateTodayOrFuture(value) {
  if (!value) return false;
  const today = new Date().toISOString().slice(0, 10);
  return value >= today;
}

function fecharAlerta() {
  alerta.style.display = "none";
  som.pause();
  som.currentTime = 0;
  if (currentAlertMed) {
    // No alerta, mantém o medicamento e só regista toma
    const med = currentAlertMed;
    const nota = pedirNota();
    fetch("/api/tomas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        med_id: med.id,
        nome: med.nome,
        dose: med.dose,
        nota
      })
    }).then(() => carregarTomas());
    currentAlertMed = null;
  }
}
