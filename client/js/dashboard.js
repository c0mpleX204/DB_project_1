import { BASE_URL, apiRequest, logout, requireLogin, setLog } from "./api.js";

const apiStatusNode = document.getElementById("api-status");
const invCountNode = document.getElementById("inv-count");
const orderCountNode = document.getElementById("order-count");
const currentPassengerNode = document.getElementById("current-passenger");
const passengerId = requireLogin();

currentPassengerNode.textContent = String(passengerId);
document.getElementById("btn-logout").addEventListener("click", logout);

async function loadDashboard() {
  try {
    const root = await apiRequest("/");
    apiStatusNode.textContent = root.message ? "ONLINE" : "UNKNOWN";
    setLog(`API: ${BASE_URL} 可访问`);
  } catch (err) {
    apiStatusNode.textContent = "OFFLINE";
    setLog(`API 健康检查失败: ${err.message}`);
  }

  try {
    const inv = await apiRequest("/api/v1/tickets?limit=200&offset=0");
    invCountNode.textContent = String(Array.isArray(inv) ? inv.length : 0);
  } catch (err) {
    invCountNode.textContent = "ERR";
    setLog(`读取库存失败: ${err.message}`);
  }
}

async function loadOrderCount() {
  try {
    const rows = await apiRequest(`/api/v1/orders/${passengerId}?limit=200&offset=0`);
    orderCountNode.textContent = String(Array.isArray(rows) ? rows.length : 0);
    setLog(`乘客 ${passengerId} 的订单数已更新`);
  } catch (err) {
    orderCountNode.textContent = "ERR";
    setLog(`读取订单数失败: ${err.message}`);
  }
}

loadDashboard();
loadOrderCount();
