const API_BASE_URL = "http://localhost:8000";

const CATEGORY_LABELS = {
  laptop: "Laptop",
  desktop: "Komputer stacjonarny",
  monitor: "Monitor",
  printer: "Drukarka",
  peripheral: "Urządzenie peryferyjne",
  network: "Sieć",
  other: "Inne",
};

const PRIORITY_LABELS = {
  low: "Niski",
  medium: "Średni",
  high: "Wysoki",
  critical: "Krytyczny",
};

const STATUS_LABELS = {
  open: "Otwarte",
  in_progress: "W realizacji",
  resolved: "Rozwiązane",
  closed: "Zamknięte",
};

const ROLE_LABELS = {
  employee: "pracownik",
  agent: "agent Helpdesk",
};

let currentUser = null;
let selectedTicketId = null;

const messageBox = document.getElementById("message");
const authView = document.getElementById("auth-view");
const appView = document.getElementById("app-view");
const userBar = document.getElementById("user-bar");
const userInfo = document.getElementById("user-info");
const ticketList = document.getElementById("ticket-list");
const ticketDetail = document.getElementById("ticket-detail");
const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const ticketForm = document.getElementById("ticket-form");
const filterForm = document.getElementById("filter-form");
const logoutButton = document.getElementById("logout-button");

async function api(path, options = {}) {
  const response = await fetch(API_BASE_URL + path, {
    method: options.method || "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  let body = null;
  try {
    body = await response.json();
  } catch (error) {
    body = null;
  }

  if (!response.ok) {
    if (body && typeof body.detail === "string") {
      throw new Error(body.detail);
    }
    throw new Error(JSON.stringify(body));
  }
  return body;
}

function showMessage(text, isError) {
  messageBox.textContent = text;
  messageBox.className = text ? (isError ? "error" : "success") : "";
}

function formatDate(value) {
  return new Date(value).toLocaleString("pl-PL");
}

function statusBadge(status) {
  return `<span class="status status-${status}">${STATUS_LABELS[status] || status}</span>`;
}

function showAuthView() {
  currentUser = null;
  selectedTicketId = null;
  authView.hidden = false;
  appView.hidden = true;
  userBar.hidden = true;
  ticketDetail.hidden = true;
  ticketDetail.innerHTML = "";
  ticketList.innerHTML = "";
}

async function showAppView() {
  authView.hidden = true;
  appView.hidden = false;
  userBar.hidden = false;
  userInfo.innerHTML = `Zalogowano: ${currentUser.full_name} (${ROLE_LABELS[currentUser.role] || currentUser.role})`;
  await loadTickets();
}

function renderTickets(tickets) {
  if (tickets.length === 0) {
    ticketList.innerHTML = `<tr><td colspan="8">Brak zgłoszeń.</td></tr>`;
    return;
  }

  ticketList.innerHTML = tickets
    .map(
      (ticket) => `
      <tr data-id="${ticket.id}">
        <td>${ticket.id}</td>
        <td>${ticket.title}</td>
        <td>${CATEGORY_LABELS[ticket.category] || ticket.category}</td>
        <td>${PRIORITY_LABELS[ticket.priority] || ticket.priority}</td>
        <td>${statusBadge(ticket.status)}</td>
        <td>${ticket.reporter_name}</td>
        <td>${ticket.assignee_name || "—"}</td>
        <td>${formatDate(ticket.created_at)}</td>
      </tr>`
    )
    .join("");

  ticketList.querySelectorAll("tr[data-id]").forEach((row) => {
    row.addEventListener("click", () => {
      openTicket(Number(row.dataset.id)).catch((error) => showMessage(error.message, true));
    });
  });
}

function currentFilterQuery() {
  const data = new FormData(filterForm);
  const params = new URLSearchParams();
  for (const [key, value] of data.entries()) {
    if (value !== "") {
      params.set(key, value);
    }
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

async function loadTickets() {
  const tickets = await api(`/api/tickets${currentFilterQuery()}`);
  renderTickets(tickets);
}

function renderAgentActions(ticket) {
  if (currentUser.role !== "agent") {
    return "";
  }
  const options = Object.entries(STATUS_LABELS)
    .map(
      ([value, label]) =>
        `<option value="${value}"${value === ticket.status ? " selected" : ""}>${label}</option>`
    )
    .join("");
  return `
    <div class="agent-actions">
      <select id="status-select">${options}</select>
      <button type="button" id="status-button">Zmień status</button>
      <button type="button" id="assign-button">Przypisz do mnie</button>
    </div>`;
}

async function openTicket(id) {
  const ticket = await api(`/api/tickets/${id}`);
  selectedTicketId = ticket.id;

  const comments = ticket.comments
    .map(
      (comment) => `
      <li>
        <strong>${comment.author_name}</strong>
        <span class="meta">${formatDate(comment.created_at)}</span>
        <div>${comment.body}</div>
      </li>`
    )
    .join("");

  ticketDetail.innerHTML = `
    <h2>#${ticket.id} ${ticket.title}</h2>
    <p class="meta">
      ${statusBadge(ticket.status)}
      Kategoria: ${CATEGORY_LABELS[ticket.category] || ticket.category} ·
      Priorytet: ${PRIORITY_LABELS[ticket.priority] || ticket.priority} ·
      Nr inwentarzowy: ${ticket.asset_tag || "—"} ·
      Lokalizacja: ${ticket.location || "—"}
    </p>
    <p class="meta">
      Zgłaszający: ${ticket.reporter_name} ·
      Przypisany: ${ticket.assignee_name || "—"} ·
      Utworzono: ${formatDate(ticket.created_at)} ·
      Zaktualizowano: ${formatDate(ticket.updated_at)}
    </p>
    <p class="description">${ticket.description}</p>
    ${renderAgentActions(ticket)}
    <h3>Komentarze</h3>
    <ul class="comments">${comments || "<li>Brak komentarzy.</li>"}</ul>
    <form id="comment-form">
      <label>Nowy komentarz
        <textarea name="body" rows="3" required></textarea>
      </label>
      <button type="submit">Dodaj komentarz</button>
    </form>`;
  ticketDetail.hidden = false;

  document.getElementById("comment-form").addEventListener("submit", onCommentSubmit);

  const statusButton = document.getElementById("status-button");
  if (statusButton) {
    statusButton.addEventListener("click", onStatusChange);
  }
  const assignButton = document.getElementById("assign-button");
  if (assignButton) {
    assignButton.addEventListener("click", onAssignToMe);
  }
}

async function refreshAfterChange() {
  await openTicket(selectedTicketId);
  await loadTickets();
}

async function onCommentSubmit(event) {
  event.preventDefault();
  const form = event.target;
  try {
    await api(`/api/tickets/${selectedTicketId}/comments`, {
      method: "POST",
      body: { body: new FormData(form).get("body") },
    });
    showMessage("Komentarz dodany", false);
    await refreshAfterChange();
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function onStatusChange() {
  const status = document.getElementById("status-select").value;
  try {
    await api(`/api/tickets/${selectedTicketId}`, { method: "PATCH", body: { status } });
    showMessage("Status zmieniony", false);
    await refreshAfterChange();
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function onAssignToMe() {
  try {
    await api(`/api/tickets/${selectedTicketId}`, {
      method: "PATCH",
      body: { assignee_id: currentUser.id },
    });
    showMessage("Zgłoszenie przypisane do Ciebie", false);
    await refreshAfterChange();
  } catch (error) {
    showMessage(error.message, true);
  }
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(loginForm);
  try {
    const result = await api("/api/auth/login", {
      method: "POST",
      body: { username: data.get("username"), password: data.get("password") },
    });
    currentUser = result.user;
    loginForm.reset();
    showMessage("", false);
    await showAppView();
  } catch (error) {
    showMessage(error.message, true);
  }
});

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(registerForm);
  try {
    await api("/api/auth/register", {
      method: "POST",
      body: {
        username: data.get("username"),
        password: data.get("password"),
        full_name: data.get("full_name"),
        department: data.get("department"),
      },
    });
    registerForm.reset();
    showMessage("Konto utworzone — możesz się zalogować", false);
  } catch (error) {
    showMessage(error.message, true);
  }
});

logoutButton.addEventListener("click", async () => {
  try {
    await api("/api/auth/logout", { method: "POST" });
  } catch (error) {
    showMessage(error.message, true);
  }
  showAuthView();
});

ticketForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(ticketForm);
  try {
    await api("/api/tickets", {
      method: "POST",
      body: {
        title: data.get("title"),
        description: data.get("description"),
        category: data.get("category"),
        priority: data.get("priority"),
        asset_tag: data.get("asset_tag") || null,
        location: data.get("location") || null,
      },
    });
    ticketForm.reset();
    showMessage("Zgłoszenie wysłane", false);
    await loadTickets();
  } catch (error) {
    showMessage(error.message, true);
  }
});

filterForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await loadTickets();
  } catch (error) {
    showMessage(error.message, true);
  }
});

async function init() {
  try {
    currentUser = await api("/api/auth/me");
  } catch (error) {
    currentUser = null;
  }

  if (currentUser) {
    try {
      await showAppView();
    } catch (error) {
      showMessage(error.message, true);
    }
  } else {
    showAuthView();
  }
}

init();
