import { apiRequest, logout, requireLogin, setLog } from "./api.js";

const tbody = document.getElementById("inv-body");
const currentPassengerId = requireLogin();
const currentPassengerNode = document.getElementById("current-passenger");
if (currentPassengerNode) {
  currentPassengerNode.textContent = String(currentPassengerId);
}
const logoutBtn = document.getElementById("btn-logout");
if (logoutBtn) {
  logoutBtn.addEventListener("click", logout);
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function refreshInventory() {
  try {
    const rows = await apiRequest("/api/v1/tickets?limit=200&offset=0");
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:gray;">暂无数据</td></tr>';
      return;
    }
    tbody.innerHTML = rows
      .map(
        (r) => `
      <tr>
        <td>${r.ticket_id}</td>
        <td>${r.flight_id}</td>
        <td>${escapeHtml(r.flight_date)}</td>
        <td>${r.economy_remain} / ${r.economy_price}</td>
        <td>${r.business_remain} / ${r.business_price}</td>
        <td><button class="mini-btn" data-del="${r.ticket_id}">删除</button></td>
      </tr>
    `,
      )
      .join("");

    tbody.querySelectorAll("button[data-del]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const ticketId = Number(btn.dataset.del);
        try {
          await apiRequest(`/api/v1/tickets/${ticketId}`, { method: "DELETE" });
          setLog(`删除成功: ticket_id=${ticketId}`);
          refreshInventory();
        } catch (err) {
          setLog(`删除失败: ${err.message}`);
        }
      });
    });
  } catch (err) {
    setLog(`加载库存失败: ${err.message}`);
  }
}

document.getElementById("btn-refresh").addEventListener("click", refreshInventory);

document.getElementById("generate-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const startDate = document.getElementById("start-date").value;
  const endDate = document.getElementById("end-date").value;
  try {
    const data = await apiRequest("/api/v1/tickets/generate", {
      method: "POST",
      body: { start_date: startDate, end_date: endDate },
    });
    setLog(`自动生成机票完成，新增 ${data.added} 条机票`);
    refreshInventory();
  } catch (err) {
    setLog(`自动生成机票失败: ${err.message}`);
  }
});

document.getElementById("create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    flight_id: Number(document.getElementById("c-flight-id").value),
    flight_date: document.getElementById("c-flight-date").value,
    business_price: Number(document.getElementById("c-b-price").value),
    business_remain: Number(document.getElementById("c-b-remain").value),
    economy_price: Number(document.getElementById("c-e-price").value),
    economy_remain: Number(document.getElementById("c-e-remain").value),
  };

  try {
    const data = await apiRequest("/api/v1/tickets", { method: "POST", body: payload });
    setLog(`新增成功: ticket_id=${data.ticket_id}`);
    event.target.reset();
    refreshInventory();
  } catch (err) {
    setLog(`新增失败: ${err.message}`);
  }
});

refreshInventory();
