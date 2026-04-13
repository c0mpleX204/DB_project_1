const BASE_URL = "http://127.0.0.1:8000";
const AUTH_KEY = "current_passenger_id";

function setLog(message) {
  const node = document.getElementById("log");
  if (!node) return;
  const now = new Date().toLocaleTimeString("zh-CN", { hour12: false });
  node.textContent = `[${now}] ${message}`;
}

function getCurrentPassengerId() {
  const raw = localStorage.getItem(AUTH_KEY);
  const parsed = Number(raw);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    return null;
  }
  return parsed;
}

function setCurrentPassengerId(passengerId) {
  localStorage.setItem(AUTH_KEY, String(passengerId));
}

function clearCurrentPassengerId() {
  localStorage.removeItem(AUTH_KEY);
}

function requireLogin() {
  const passengerId = getCurrentPassengerId();
  if (!passengerId) {
    window.location.href = "./login.html";
    throw new Error("login required");
  }
  return passengerId;
}

function logout() {
  clearCurrentPassengerId();
  window.location.href = "./login.html";
}

async function apiRequest(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const passengerId = getCurrentPassengerId();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (passengerId) {
    headers["X-Passenger-Id"] = String(passengerId);
  }

  const finalOptions = {
    headers,
    ...options,
  };
  if (finalOptions.body && typeof finalOptions.body !== "string") {
    finalOptions.body = JSON.stringify(finalOptions.body);
  }

  const resp = await fetch(url, finalOptions);
  const text = await resp.text();
  let data = null;

  if (text) {
    try {
      data = JSON.parse(text);
    } catch (_) {
      data = text;
    }
  }

  if (!resp.ok) {
    if (resp.status === 401 && path !== "/api/v1/auth/login" && !window.location.pathname.endsWith("/login.html")) {
      clearCurrentPassengerId();
      window.location.href = "./login.html";
    }
    const detail = data && data.detail ? data.detail : `HTTP ${resp.status}`;
    throw new Error(detail);
  }

  return data;
}

export {
  BASE_URL,
  apiRequest,
  clearCurrentPassengerId,
  getCurrentPassengerId,
  logout,
  requireLogin,
  setCurrentPassengerId,
  setLog,
};
