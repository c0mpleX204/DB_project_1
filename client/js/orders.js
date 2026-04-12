import { apiRequest, setLog } from "./api.js";

const form = document.getElementById("orders-form");
const tbody = document.getElementById("orders-body");
const passengerNode = document.getElementById("passenger-id");

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function loadOrders() {
  const passengerId = Number(passengerNode.value || 1);
  try {
    const rows = await apiRequest(`/api/v1/orders/${passengerId}?limit=200&offset=0`);

    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:gray;">暂无订单</td></tr>';
      setLog(`乘客 ${passengerId} 暂无订单`);
      return;
    }

    tbody.innerHTML = rows
      .map(
        (r) => `
      <tr>
        <td>${r.order_id}</td>
        <td>${escapeHtml(r.status)}</td>
        <td>${escapeHtml(r.cabin_class)}</td>
        <td>${r.unit_price}</td>
        <td>${escapeHtml(r.flight_number)}</td>
        <td>${escapeHtml(r.source_city)} -> ${escapeHtml(r.destination_city)}</td>
        <td>${escapeHtml(r.flight_date)}</td>
        <td>${escapeHtml(r.booked_at)}</td>
        <td>
          ${
            r.status === "booked"
              ? `<button class="mini-btn" data-cancel="${r.order_id}">取消</button>`
              : "-"
          }
        </td>
      </tr>
    `,
      )
      .join("");

    tbody.querySelectorAll("button[data-cancel]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const orderId = Number(btn.dataset.cancel);
        try {
          await apiRequest(`/api/v1/orders/${passengerId}/${orderId}/cancel`, { method: "POST" });
          setLog(`取消成功: order_id=${orderId}`);
          loadOrders();
        } catch (err) {
          setLog(`取消失败: ${err.message}`);
        }
      });
    });

    setLog(`加载完成: 乘客 ${passengerId} 共 ${rows.length} 条订单`);
  } catch (err) {
    setLog(`加载订单失败: ${err.message}`);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  loadOrders();
});

loadOrders();
