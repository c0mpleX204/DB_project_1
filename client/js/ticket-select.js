import { apiRequest, setLog } from "./api.js";

const form = document.getElementById("filter-form");
const tbody = document.getElementById("result-body");
const dateTabs = document.getElementById("date-tabs");

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function fillRouteFromQuery() {
  const q = new URLSearchParams(window.location.search);
  const dep = q.get("departure_city") || "";
  const arr = q.get("arrival_city") || "";
  document.getElementById("dep").value = dep;
  document.getElementById("arr").value = arr;
}

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

function buildDateTabs() {
  const today = new Date();
  const buttons = [];
  for (let i = 0; i < 7; i += 1) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    const iso = d.toISOString().slice(0, 10);
    const label = i === 0 ? "今天" : i === 1 ? "明天" : `${d.getMonth() + 1}/${d.getDate()}`;
    buttons.push(`<button type="button" class="date-tab" data-date="${iso}">${label}</button>`);
  }
  dateTabs.innerHTML = buttons.join("");

  dateTabs.querySelectorAll(".date-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      dateTabs.querySelectorAll(".date-tab").forEach((x) => x.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("date").value = btn.dataset.date;
      if (document.getElementById("dep").value.trim() && document.getElementById("arr").value.trim()) {
        form.requestSubmit();
      }
    });
  });

  const first = dateTabs.querySelector(".date-tab");
  if (first) {
    first.classList.add("active");
    document.getElementById("date").value = first.dataset.date;
  }
}

async function bookTicket(ticketId, cabinClass) {
  const passengerId = Number(document.getElementById("passenger-id").value || 1);
  try {
    const data = await apiRequest("/api/v1/orders/book", {
      method: "POST",
      body: {
        passenger_id: passengerId,
        ticket_id: ticketId,
        cabin_class: cabinClass,
      },
    });
    setLog(`下单成功: order_id=${data.order_id}, ticket_id=${ticketId}, cabin=${cabinClass}`);
  } catch (err) {
    setLog(`下单失败: ${err.message}`);
  }
}

function renderRows(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:gray;">没有符合条件的机票</td></tr>';
    return;
  }

  const sortedRows = [...rows].sort((a, b) => String(a.departure_time_local).localeCompare(String(b.departure_time_local)));

  tbody.innerHTML = sortedRows
    .map(
      (r) => `
      <tr>
        <td>${r.ticket_id}</td>
        <td>${escapeHtml(r.flight_number)}</td>
        <td>${escapeHtml(r.airline_code)} (${escapeHtml(r.airline_name)})</td>
        <td>${escapeHtml(r.source_city)}(${escapeHtml(r.source_iata)}) -> ${escapeHtml(r.destination_city)}(${escapeHtml(r.destination_iata)})</td>
        <td>${escapeHtml(r.departure_time_local)} - ${escapeHtml(r.arrival_time_local)} (+${r.arrival_day_offset})</td>
        <td>${r.economy_remain} / ${r.economy_price}</td>
        <td>${r.business_remain} / ${r.business_price}</td>
        <td>
          <button class="mini-btn" data-id="${r.ticket_id}" data-cabin="economy">经济舱</button>
          <button class="mini-btn" data-id="${r.ticket_id}" data-cabin="business">商务舱</button>
        </td>
      </tr>
    `,
    )
    .join("");

  tbody.querySelectorAll("button[data-id]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const ticketId = Number(btn.dataset.id);
      const cabin = btn.dataset.cabin;
      bookTicket(ticketId, cabin);
    });
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const dep = document.getElementById("dep").value.trim();
  const arr = document.getElementById("arr").value.trim();
  const date = document.getElementById("date").value;
  const depTime = document.getElementById("dep-time").value;
  const arrTime = document.getElementById("arr-time").value;
  const airline = document.getElementById("airline").value.trim();
  const srcIata = document.getElementById("src-iata").value.trim();
  const dstIata = document.getElementById("dst-iata").value.trim();

  const params = new URLSearchParams({
    departure_city: dep,
    arrival_city: arr,
    flight_date: date,
    limit: "200",
    offset: "0",
  });

  if (airline) params.set("airline", airline);
  if (depTime) params.set("departure_time", depTime);
  if (arrTime) params.set("arrival_time", arrTime);
  if (srcIata) params.set("source_iata", srcIata.toUpperCase());
  if (dstIata) params.set("destination_iata", dstIata.toUpperCase());

  try {
    const rows = await apiRequest(`/api/v1/tickets/search?${params.toString()}`);
    renderRows(rows);
    setLog(`筛选完成，返回 ${rows.length} 条机票`);
  } catch (err) {
    setLog(`筛选失败: ${err.message}`);
  }
});

fillRouteFromQuery();
bindCityAutocomplete("dep", "dep-city-list");
bindCityAutocomplete("arr", "arr-city-list");
buildDateTabs();
