const BASE_URL = "http://127.0.0.1:8000";

function setLog(message) {
  const node = document.getElementById("log");
  if (!node) return;
  const now = new Date().toLocaleTimeString("zh-CN", { hour12: false });
  node.textContent = `[${now}] ${message}`;
}

async function apiRequest(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const finalOptions = {
    headers: { "Content-Type": "application/json" },
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
    const detail = data && data.detail ? data.detail : `HTTP ${resp.status}`;
    throw new Error(detail);
  }

  return data;
}

export { BASE_URL, apiRequest, setLog };
