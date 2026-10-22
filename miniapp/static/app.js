const state = {
  scenarios: [],
  scenario: "banshao",
};

const scenariosEl = document.querySelector("#scenarios");
const resultEl = document.querySelector("#result");
const errorEl = document.querySelector("#error");
const sourceEl = document.querySelector("#source");
const minutesEl = document.querySelector("#minutes");
const wageEl = document.querySelector("#wage");
const maxEl = document.querySelector("#maxMinutes");
const drivingEl = document.querySelector("#driving");

function money(value) {
  return `¥${Number(value).toFixed(2)}`;
}

function showError(message) {
  errorEl.hidden = !message;
  errorEl.textContent = message || "";
}

function selectedScenario() {
  return state.scenarios.find((item) => item.id === state.scenario);
}

function renderScenarios() {
  scenariosEl.innerHTML = "";
  state.scenarios.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `choice${item.id === state.scenario ? " selected" : ""}`;
    button.innerHTML = `<strong>${item.title}</strong><span>${item.place} · ${item.blurb}</span>`;
    button.addEventListener("click", () => {
      state.scenario = item.id;
      minutesEl.value = item.default_minutes_to_spot;
      sourceEl.textContent = item.source;
      renderScenarios();
      ask();
    });
    scenariosEl.appendChild(button);
  });
}

function renderResult(data) {
  const wage = data.critical_wage_yuan_per_hour;
  const wageText = wage == null
    ? "这几条路里没有「更便宜但更花时间」的对照。"
    : `临界时薪约 ¥${wage}/小时。低于它更值得出门，高于它更值得外送。`;
  const rows = data.rows.map((row) => `
    <tr class="${row.recommended ? "pick" : ""}">
      <td>
        ${row.label}${row.recommended ? " · 建议" : ""}${row.in_decision ? "" : " · 对照"}
        <p class="note">${row.store_name}</p>
        <p class="note">${row.product_name}</p>
        <p class="note">${row.note}</p>
      </td>
      <td class="price">${money(row.price_yuan)}</td>
      <td class="mins">${row.minutes} 分钟</td>
    </tr>
  `).join("");
  resultEl.hidden = false;
  sourceEl.textContent = data.scenario.source;
  resultEl.innerHTML = `
    <p class="kicker">${data.scenario.place} · ${data.scenario.title}</p>
    <h2>裁决：${data.headline}</h2>
    <p class="reason">${data.reason}</p>
    <table>
      <thead><tr><th>通道</th><th class="price">到手价</th><th class="mins">时间</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <p class="wage">${wageText}</p>
    <p class="note">${data.scenario.source}（${data.scenario.captured_at}，上海时间）</p>
    <button class="again" type="button" data-scenario="mala">换成麦辣券再比</button>
    <button class="again" type="button" data-wage="50">时薪按 50 再比</button>
    <button class="again" type="button" data-wage="80">时薪按 80 再比</button>
    <button class="again" type="button" data-minutes="0">人已经在站口</button>
  `;
  resultEl.querySelectorAll(".again").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.scenario) {
        state.scenario = button.dataset.scenario;
        const item = selectedScenario();
        if (item) minutesEl.value = item.default_minutes_to_spot;
        renderScenarios();
      }
      if (button.dataset.wage) wageEl.value = button.dataset.wage;
      if (button.dataset.minutes != null) minutesEl.value = button.dataset.minutes;
      ask();
    });
  });
}

async function ask() {
  showError("");
  const button = document.querySelector("#go");
  button.disabled = true;
  try {
    const response = await fetch("/api/verdict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scenario: state.scenario,
        minutes_to_spot: minutesEl.value,
        wage: wageEl.value,
        driving: drivingEl.checked,
        max_minutes: maxEl.value,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      showError(data.error || "裁决失败");
      return;
    }
    renderResult(data);
  } catch (error) {
    showError("页面没连上本机服务");
  } finally {
    button.disabled = false;
  }
}

document.querySelector("#go").addEventListener("click", ask);
drivingEl.addEventListener("change", ask);

fetch("/api/scenarios")
  .then((response) => response.json())
  .then((data) => {
    state.scenarios = data.scenarios;
    const first = selectedScenario();
    minutesEl.value = first.default_minutes_to_spot;
    sourceEl.textContent = first.source;
    renderScenarios();
    ask();
  })
  .catch(() => showError("页面没连上本机服务"));
