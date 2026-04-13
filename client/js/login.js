import { apiRequest, getCurrentPassengerId, setCurrentPassengerId, setLog } from "./api.js";

const form = document.getElementById("login-form");

const existing = getCurrentPassengerId();
if (existing) {
  window.location.href = "./index.html";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value.trim();

  if (!username || !password) {
    setLog("请输入手机号和密码");
    return;
  }

  try {
    const data = await apiRequest("/api/v1/auth/login", {
      method: "POST",
      body: {
        username,
        password,
      },
    });
    setCurrentPassengerId(data.passenger_id);
    setLog(`登录成功: passenger_id=${data.passenger_id}`);
    window.location.href = "./index.html";
  } catch (err) {
    setLog(`登录失败: ${err.message}`);
  }
});
