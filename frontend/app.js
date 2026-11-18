const API_BASE_URL = "http://patchpoint.localhost:8000";
const PAGE_SIZE = 50;
const SESSION_EXPIRED_MESSAGE = "Sesja wygasła lub została zakończona — zaloguj się ponownie.";

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
let currentOffset = 0;

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
const prevButton = document.getElementById("prev-page");
const nextButton = document.getElementById("next-page");
const pageInfo = document.getElementById("page-info");

function el(tag, className, ...children) {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  for (const child of children) {
    if (child !== null && child !== undefined) {
      element.append(child);
    }
  }
  return element;
}

function label(map, value) {
  return map[value] || value;
}

function fillSelect(select, labels, selectedValue) {
  for (const [value, text] of Object.entries(labels)) {
    const selected = value === selectedValue;
    select.append(new Option(text, value, selected, selected));
  }
}

fillSelect(ticketForm.querySelector('select[name="category"]'), CATEGORY_LABELS);
fillSelect(ticketForm.querySelector('select[name="priority"]'), PRIORITY_LABELS, "medium");
fillSelect(filterForm.querySelector('select[name="status"]'), STATUS_LABELS);

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
    if (response.status === 401 && currentUser !== null) {
      showAuthView();
      showMessage(SESSION_EXPIRED_MESSAGE, true);
      throw new Error(SESSION_EXPIRED_MESSAGE);
    }
    const detail = body ? body.detail : null;
    if (typeof detail === "string") {
      throw new Error(detail);
    }
    if (Array.isArray(detail)) {
      throw new Error(detail.map((item) => item.msg).join("; "));
    }
    throw new Error(`Błąd serwera (HTTP ${response.status})`);
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
  return el("span", "status status-" + status, label(STATUS_LABELS, status));
}

function showAuthView() {
  currentUser = null;
  selectedTicketId = null;
  currentOffset = 0;
  authView.hidden = false;
  appView.hidden = true;
  userBar.hidden = true;
  ticketDetail.hidden = true;
  ticketDetail.replaceChildren();
  ticketList.replaceChildren();
  userInfo.replaceChildren();
  ticketForm.reset();
  filterForm.reset();
  registerForm.reset();
  showMessage("", false);
}

async function showAppView() {
  authView.hidden = true;
  appView.hidden = false;
  userBar.hidden = false;
  userInfo.textContent = `Zalogowano: ${currentUser.full_name} (${label(ROLE_LABELS, currentUser.role)})`;
  await loadTickets();
}

function renderTickets(tickets) {
  if (tickets.length === 0) {
    const cell = el("td", null, "Brak zgłoszeń.");
    cell.colSpan = 8;
    ticketList.replaceChildren(el("tr", null, cell));
    return;
  }

  const rows = tickets.map((ticket) => {
    const row = el(
      "tr",
      null,
      el("td", null, String(ticket.id)),
      el("td", null, ticket.title),
      el("td", null, label(CATEGORY_LABELS, ticket.category)),
      el("td", null, label(PRIORITY_LABELS, ticket.priority)),
      el("td", null, statusBadge(ticket.status)),
      el("td", null, ticket.reporter_name),
      el("td", null, ticket.assignee_name || "—"),
      el("td", null, formatDate(ticket.created_at))
    );
    row.addEventListener("click", () => {
      openTicket(ticket.id).catch((error) => showMessage(error.message, true));
    });
    return row;
  });
  ticketList.replaceChildren(...rows);
}

function currentFilterParams() {
  const data = new FormData(filterForm);
  const params = new URLSearchParams();
  for (const [key, value] of data.entries()) {
    if (value !== "") {
      params.set(key, value);
    }
  }
  return params;
}

async function loadTickets() {
  const params = currentFilterParams();
  params.set("limit", String(PAGE_SIZE));
  params.set("offset", String(currentOffset));
  const tickets = await api(`/api/tickets?${params.toString()}`);
  renderTickets(tickets);
  prevButton.disabled = currentOffset === 0;
  nextButton.disabled = tickets.length < PAGE_SIZE;
  pageInfo.textContent = "Strona " + (currentOffset / PAGE_SIZE + 1);
}

function renderAgentActions(ticket) {
  if (currentUser.role !== "agent") {
    return null;
  }
  const select = el("select");
  select.id = "status-select";
  fillSelect(select, STATUS_LABELS, ticket.status);

  const statusButton = el("button", null, "Zmień status");
  statusButton.type = "button";
  statusButton.id = "status-button";
  statusButton.addEventListener("click", onStatusChange);

  const assignButton = el("button", null, "Przypisz do mnie");
  assignButton.type = "button";
  assignButton.id = "assign-button";
  assignButton.addEventListener("click", onAssignToMe);

  return el("div", "agent-actions", select, statusButton, assignButton);
}

function renderCommentForm() {
  const textarea = el("textarea");
  textarea.name = "body";
  textarea.rows = 3;
  textarea.required = true;
  textarea.maxLength = 2000;

  const submit = el("button", null, "Dodaj komentarz");
  submit.type = "submit";

  const form = el("form", null, el("label", null, "Nowy komentarz", textarea), submit);
  form.id = "comment-form";
  form.addEventListener("submit", onCommentSubmit);
  return form;
}

async function openTicket(id) {
  const ticket = await api(`/api/tickets/${id}`);
  selectedTicketId = ticket.id;

  const comments = ticket.comments.map((comment) =>
    el(
      "li",
      null,
      el("strong", null, comment.author_name),
      " ",
      el("span", "meta", formatDate(comment.created_at)),
      el("div", null, comment.body)
    )
  );
  if (comments.length === 0) {
    comments.push(el("li", null, "Brak komentarzy."));
  }

  const detailNodes = [
    el("h2", null, `#${ticket.id} ${ticket.title}`),
    el(
      "p",
      "meta",
      statusBadge(ticket.status),
      ` Kategoria: ${label(CATEGORY_LABELS, ticket.category)} · ` +
        `Priorytet: ${label(PRIORITY_LABELS, ticket.priority)} · ` +
        `Nr inwentarzowy: ${ticket.asset_tag || "—"} · ` +
        `Lokalizacja: ${ticket.location || "—"}`
    ),
    el(
      "p",
      "meta",
      `Zgłaszający: ${ticket.reporter_name} · ` +
        `Przypisany: ${ticket.assignee_name || "—"} · ` +
        `Utworzono: ${formatDate(ticket.created_at)} · ` +
        `Zaktualizowano: ${formatDate(ticket.updated_at)}`
    ),
    el("p", "description", ticket.description),
    renderAgentActions(ticket),
    el("h3", null, "Komentarze"),
    ticket.comment_count > ticket.comments.length
      ? el(
          "p",
          "meta",
          `Wyświetlono ostatnie ${ticket.comments.length} z ${ticket.comment_count} komentarzy.`
        )
      : null,
    el("ul", "comments", ...comments),
    renderCommentForm()
  ];
  ticketDetail.replaceChildren(...detailNodes.filter((node) => node !== null));
  ticketDetail.hidden = false;
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

async function changePage(delta) {
  currentOffset = Math.max(0, currentOffset + delta);
  try {
    await loadTickets();
  } catch (error) {
    showMessage(error.message, true);
  }
}

prevButton.addEventListener("click", () => changePage(-PAGE_SIZE));
nextButton.addEventListener("click", () => changePage(PAGE_SIZE));

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(loginForm);
  try {
    const result = await api("/api/auth/login", {
      method: "POST",
      body: { username: data.get("username"), password: data.get("password") },
    });
    currentUser = result.user;
    currentOffset = 0;
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
    if (currentUser !== null) {
      showMessage("Nie udało się wylogować: " + error.message, true);
    }
    return;
  }
  showAuthView();
  showMessage("Wylogowano", false);
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
    currentOffset = 0;
    await loadTickets();
  } catch (error) {
    showMessage(error.message, true);
  }
});

filterForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  currentOffset = 0;
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
