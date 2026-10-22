const state = { selected: new Set(["板烧鸡腿堡", "薯条"]) };

const menuEl = document.querySelector("#menu");
const pickedEl = document.querySelector("#picked");
const resultEl = document.querySelector("#result");
const errorEl = document.querySelector("#error");
const sourceEl = document.querySelector("#source");
const cityEl = document.querySelector("#city");
const keywordEl = document.querySelector("#keyword");
const minutesEl = document.querySelector("#minutes");
const wageEl = document.querySelector("#wage");
const maxEl = document.querySelector("#maxMinutes");
const drivingEl = document.querySelector("#driving");
const couponEl = document.querySelector("#coupon");

function money(value) {
  return `¥${Number(value).toFixed(2)}`;
}

function showError(message) {
  errorEl.hidden = !message;
  errorEl.textContent = message || "";
}

function esc(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function renderPicked() {
  pickedEl.textContent = state.selected.size
    ? `已选 ${[...state.selected].join("、")}`
    : "还没点";
}

function renderMenu(groups) {
  menuEl.innerHTML = "";
  groups.forEach((group) => {
    const section = document.createElement("section");
    section.className = "group";
    const title = document.createElement("h2");
    title.textContent = group.label;
    const chips = document.createElement("div");
    chips.className = "chips";
    group.items.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `chip${state.selected.has(item.name) ? " on" : ""}`;
      button.dataset.name = item.name;
      const name = document.createElement("span");
      name.textContent = item.name;
      const price = document.createElement("small");
      price.textContent = money(item.price_yuan) + (item.price_note ? ` ${item.price_note}` : "");
      button.append(name, price);
      button.addEventListener("click", () => {
        if (state.selected.has(item.name)) state.selected.delete(item.name);
        else state.selected.add(item.name);
        button.classList.toggle("on", state.selected.has(item.name));
        renderPicked();
      });
      chips.append(button);
    });
    section.append(title, chips);
    menuEl.append(section);
  });
  renderPicked();
}

function renderResult(data) {
  const wage = data.critical_wage_yuan_per_hour;
  const wageText = wage == null
    ? "这几条路里没有「更便宜但更花时间」的对照。"
    : `临界时薪约 ¥${wage}/小时。低于它更值得出门，高于它更值得外送。`;
  const rows = data.rows.map((row) => `
    <tr class="${row.recommended ? "pick" : ""}">
      <td>
        ${esc(row.label)}${row.recommended ? " · 建议" : ""}${row.in_decision ? "" : " · 对照"}
        <p class="note">${esc(row.store_name)}</p>
        <p class="note">${esc(row.product_name)}</p>
        <p class="note">${esc(row.note)}</p>
      </td>
      <td class="price">${row.price_yuan == null ? "—" : money(row.price_yuan)}</td>
      <td class="mins">${row.minutes} 分钟</td>
    </tr>
  `).join("");
  resultEl.hidden = false;
  sourceEl.textContent = data.scenario.source;
  resultEl.innerHTML = `
    <p class="kicker">${esc(data.scenario.place)} · ${esc(data.scenario.title)}</p>
    <h2>裁决：${esc(data.headline)}</h2>
    <p class="reason">${esc(data.reason)}</p>
    <table>
      <thead><tr><th>通道</th><th class="price">到手价</th><th class="mins">时间</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <p class="wage">${wageText}</p>
    <p class="note">${esc(data.scenario.source)}（${esc(data.scenario.captured_at)}，上海时间）</p>
    <button class="again" type="button" data-wage="50">时薪按 50 再比</button>
    <button class="again" type="button" data-wage="80">时薪按 80 再比</button>
    <button class="again" type="button" data-minutes="0">人已经在站口</button>
  `;
  resultEl.querySelectorAll(".again").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.wage) wageEl.value = button.dataset.wage;
      if (button.dataset.minutes != null) minutesEl.value = button.dataset.minutes;
      ask();
    });
  });
}

async function ask() {
  showError("");
  if (!state.selected.size) {
    showError("先点选汉堡、小食或饮料。");
    return;
  }
  const button = document.querySelector("#go");
  button.disabled = true;
  try {
    const response = await fetch("/api/verdict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        names: [...state.selected],
        city: cityEl.value,
        keyword: keywordEl.value,
        use_coupon: couponEl.checked,
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
document.querySelector("#here").addEventListener("click", () => {
  if (!navigator.geolocation) {
    showError("这个浏览器给不了当前位置，请自己填城市和地点。");
    return;
  }
  navigator.geolocation.getCurrentPosition(async (position) => {
    try {
      const response = await fetch("/api/locate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        showError(data.error || "当前位置没有解析出来");
        return;
      }
      cityEl.value = data.city || "";
      keywordEl.value = data.keyword || "";
      ask();
    } catch (error) {
      showError("当前位置没有解析出来，请自己填。");
    }
  }, () => {
    showError("浏览器没有给出当前位置，请自己填城市和地点。");
  }, { enableHighAccuracy: true, timeout: 8000 });
});
document.querySelector("#clear").addEventListener("click", () => {
  state.selected.clear();
  menuEl.querySelectorAll(".chip").forEach((chip) => chip.classList.remove("on"));
  renderPicked();
});
drivingEl.addEventListener("change", ask);
couponEl.addEventListener("change", ask);

fetch("/api/menu")
  .then((response) => response.json())
  .then((data) => {
    renderMenu(data.groups);
    sourceEl.textContent = "小白楼店当前菜单，采集于 " + data.captured_at;
    ask();
  })
  .catch(() => showError("页面没连上本机服务"));
