import { apiRequest, logout, requireLogin } from "./api.js";

const currentPassengerId = requireLogin();
const currentPassengerNode = document.getElementById("current-passenger");
if (currentPassengerNode) {
  currentPassengerNode.textContent = String(currentPassengerId);
}
const logoutBtn = document.getElementById("btn-logout");
if (logoutBtn) {
  logoutBtn.addEventListener("click", logout);
}

const form = document.getElementById("search-form");

async function bindCityAutocomplete(inputId, listId) {
  const input = document.getElementById(inputId);
  const list = document.getElementById(listId);

  input.addEventListener("input", async () => {
    const keyword = input.value.trim();
    if (keyword.length < 1) {
      list.innerHTML = "";
      return;
    }
    try {
      const cities = await apiRequest(`/api/v1/tickets/cities?keyword=${encodeURIComponent(keyword)}&limit=12`);
      list.innerHTML = cities.map((c) => `<option value="${c}"></option>`).join("");
    } catch (_) {
      list.innerHTML = "";
    }
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const dep = document.getElementById("dep").value.trim();
  const arr = document.getElementById("arr").value.trim();

  const params = new URLSearchParams({
    departure_city: dep,
    arrival_city: arr,
  });
  window.location.href = `./ticket-select.html?${params.toString()}`;
});

bindCityAutocomplete("dep", "dep-city-list");
bindCityAutocomplete("arr", "arr-city-list");
