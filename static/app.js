/* ── Death Clock — Frontend Logic ─────────────────────────────────── */

const COUNTRIES = [
  ["AT","Austria"], ["AU","Australia"], ["BE","Belgium"], ["BR","Brazil"],
  ["BG","Bulgaria"], ["CA","Canada"], ["CH","Switzerland"], ["CY","Cyprus"],
  ["CZ","Czechia"], ["DE","Germany"], ["DK","Denmark"], ["EE","Estonia"],
  ["ES","Spain"], ["FI","Finland"], ["FR","France"], ["GB","United Kingdom"],
  ["GR","Greece"], ["HR","Croatia"], ["HU","Hungary"], ["IE","Ireland"],
  ["IS","Iceland"], ["IT","Italy"], ["JP","Japan"], ["KR","South Korea"],
  ["LT","Lithuania"], ["LU","Luxembourg"], ["LV","Latvia"], ["MT","Malta"],
  ["NL","Netherlands"], ["NO","Norway"], ["NZ","New Zealand"], ["PL","Poland"],
  ["PT","Portugal"], ["RO","Romania"], ["SE","Sweden"], ["SI","Slovenia"],
  ["SK","Slovakia"], ["TR","Türkiye"], ["US","United States"], ["ZA","South Africa"],
];

// Populate country dropdown
const countrySelect = document.getElementById("country");
COUNTRIES.forEach(([code, name]) => {
  const opt = document.createElement("option");
  opt.value = code;
  opt.textContent = name;
  countrySelect.appendChild(opt);
});

// ── Show/hide "years since quit" field ──────────────────────────────
const smokingSelect = document.getElementById("smoking");
const yearsQuitRow  = document.getElementById("years-since-quit-row");

smokingSelect.addEventListener("change", () => {
  const show = ["former_light", "former_heavy"].includes(smokingSelect.value);
  yearsQuitRow.style.display = show ? "block" : "none";
});

// ── View switching ──────────────────────────────────────────────────
function showView(id) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}

// ── State ──────────────────────────────────────────────────────────
let deathTimestamp = null;
let tickInterval = null;

// ── Activate clock view from API response ──────────────────────────
function activateClock(data) {
  deathTimestamp = Date.now() + data.remaining_seconds * 1000;
  showStats(data);
  showView("clock-view");
  startTicking();
}

// ── Form submission ─────────────────────────────────────────────────
document.getElementById("survey-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const formData = new FormData(e.target);
  const payload = {};
  formData.forEach((v, k) => { payload[k] = v; });
  // convert numeric fields
  ["height_cm","weight_kg","sleep_hours","hrv_ms","resting_hr","years_since_quit"].forEach(f => {
    if (payload[f] !== undefined) payload[f] = parseFloat(payload[f]);
  });

  try {
    const resp = await fetch("/api/survey", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      alert("Error: " + (err.detail || resp.statusText));
      return;
    }
    const data = await resp.json();
    activateClock(data);
  } catch (err) {
    alert("Network error: " + err.message);
  }
});

// ── Stats panel ─────────────────────────────────────────────────────
function showStats(data) {
  document.getElementById("stat-name").textContent = data.name;
  document.getElementById("stat-baseline").textContent = data.baseline_life_expectancy;
  document.getElementById("stat-adjustment").textContent = (data.total_adjustment > 0 ? "+" : "") + data.total_adjustment;
  document.getElementById("stat-adjusted").textContent = data.adjusted_life_expectancy;
  document.getElementById("stat-death").textContent = new Date(data.estimated_death).toLocaleDateString("en-GB", {
    year: "numeric", month: "long", day: "numeric",
  });

  // Render factor breakdown
  const ul = document.getElementById("stat-factors");
  ul.innerHTML = "";
  data.factors.forEach(f => {
    const cls = f.years > 0 ? "positive" : f.years < 0 ? "negative" : "neutral";
    const sign = f.years > 0 ? "+" : "";
    const li = document.createElement("li");
    li.className = "factor-item";
    li.innerHTML = `
      <div class="factor-head">
        <span class="factor-label">${f.label}</span>
        <span class="factor-years ${cls}">${sign}${f.years}</span>
      </div>
      <div class="factor-detail">${f.detail}</div>`;
    ul.appendChild(li);
  });
}

// ── Seven-segment rendering ─────────────────────────────────────────
const segDisplay = document.getElementById("seven-segment");

function renderCountdown() {
  const now = Date.now();
  let remainingMs = Math.max(deathTimestamp - now, 0);
  const totalSec = Math.floor(remainingMs / 1000);

  const str = totalSec.toLocaleString("en-US");
  segDisplay.innerHTML = str.split("").map(ch => {
    if (ch === ",") return `<span class="seg-sep">,</span>`;
    return `<span class="seg-digit">${ch}</span>`;
  }).join("");
}

function tick() { renderCountdown(); }

function startTicking() {
  if (tickInterval) clearInterval(tickInterval);
  tick();
  tickInterval = setInterval(tick, 1000);
}

// ── Buttons ────────────────────────────────────────────────────────
document.getElementById("btn-reset").addEventListener("click", async () => {
  try {
    await fetch("/api/profile", { method: "DELETE" });
  } catch { /* ignore */ }
  if (tickInterval) clearInterval(tickInterval);
  deathTimestamp = null;
  document.getElementById("stats-panel").classList.add("hidden");
  document.getElementById("survey-form").reset();
  yearsQuitRow.style.display = "none";
  showView("survey-view");
});

document.getElementById("btn-stats").addEventListener("click", () => {
  document.getElementById("stats-panel").classList.toggle("hidden");
});

// ── On page load: check if a profile already exists on the server ───
(async () => {
  try {
    const resp = await fetch("/api/profile");
    if (resp.ok) {
      const data = await resp.json();
      activateClock(data);
    }
  } catch { /* stay on survey */ }
})();