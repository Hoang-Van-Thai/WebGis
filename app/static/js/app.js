

let currentModel = "lst";
let trendChart = null;

// ===================== DATE HELPERS =====================
function _startOfToday() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}
function _addDays(date, days) {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}
function _fmtDateVI(d) {
  return d.toLocaleDateString("vi-VN");
}
function _fmtWeekdayVI(d) {
  return d.toLocaleDateString("vi-VN", { weekday: "short" });
}
function _fmtISODate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}
// =============================================================

// ===================== TAB =====================
function switchTab(tab) {
  currentModel = tab;

  ["lst", "ndvi", "tvdi"].forEach(t => {
    const btn = document.getElementById(`tab-${t}`);
    if (btn) btn.classList.remove("active");
  });
  const activeBtn = document.getElementById(`tab-${tab}`);
  if (activeBtn) activeBtn.classList.add("active");

  const title = { lst: "Dự báo LST", ndvi: "Dự báo NDVI", tvdi: "Dự báo TVDI" }[tab];
  const titleEl = document.getElementById("titlePage");
  if (titleEl) titleEl.innerText = title || "Dự báo";

  updateMapPanelsVisibility();
  autoRun();

  setTimeout(() => {
    try {
      if (tab === "lst" && window.lstMapInstance) window.lstMapInstance.invalidateSize();
      if (tab === "ndvi" && window.ndviMapInstance) window.ndviMapInstance.invalidateSize();
      if (tab === "tvdi" && window.tvdiMapInstance) window.tvdiMapInstance.invalidateSize();
    } catch (e) {}
  }, 250);
}

function updateMapPanelsVisibility() {
  const lstPanel = document.getElementById("lstMapPanel");
  const ndviPanel = document.getElementById("ndviMapPanel");
  const tvdiPanel = document.getElementById("tvdiMapPanel");

  if (lstPanel) lstPanel.style.display = (currentModel === "lst") ? "block" : "none";
  if (ndviPanel) ndviPanel.style.display = (currentModel === "ndvi") ? "block" : "none";
  if (tvdiPanel) tvdiPanel.style.display = (currentModel === "tvdi") ? "block" : "none";
}

// ===================== INIT =====================
window.onload = function () {
  loadXaList().then(() => {
    const sel = document.getElementById("xaSelectGlobal");
    if (sel) sel.value = "An Hội Tây";
    updateMapPanelsVisibility();
    autoRun();
  });
};

document.addEventListener("DOMContentLoaded", () => {
  initLstMapUI();
  initNdviMapUI();
  initTvdiMapUI();

  const xaSel = document.getElementById("xaSelectGlobal");
  if (xaSel) {
    xaSel.addEventListener("change", function () {
      autoRun();
    });
  }
});

// ===================== LOADING OVERLAY =====================
let loadingCount = 0;

function showLoading(text = "Đang xử lý...") {
  loadingCount++;
  const t = document.getElementById("loadingText");
  const o = document.getElementById("loadingOverlay");
  if (t) t.innerText = text;
  if (o) o.classList.remove("hidden");
}

function hideLoading() {
  loadingCount = Math.max(0, loadingCount - 1);
  if (loadingCount === 0) {
    const o = document.getElementById("loadingOverlay");
    if (o) o.classList.add("hidden");
  }
}

// ===================== AUTO RUN (forecast + chart) =====================
async function autoRun() {
  const xa = document.getElementById("xaSelectGlobal")?.value;
  if (!xa) return;

  showLoading("Đang tải mô hình & dự báo...");
  try {
    await Promise.all([runModel(xa), loadChart(xa)]);
  } catch (e) {
    console.error(e);
  } finally {
    hideLoading();
  }
}

async function runModel(xa) {
  let url = "";
  if (currentModel === "lst") url = `/api/lst/auto_predict7?xa=${encodeURIComponent(xa)}`;
  else if (currentModel === "ndvi") url = `/api/ndvi/predict?xa=${encodeURIComponent(xa)}`;
  else if (currentModel === "tvdi") url = `/api/tvdi/auto_predict?xa=${encodeURIComponent(xa)}`;

  const res = await fetch(url);
  const data = await res.json();
  renderForecastGrid(data);
  return data;
}

async function loadChart(xa) {
  let url = "";
  if (currentModel === "lst") url = `/api/lst/chart?xa=${encodeURIComponent(xa)}`;
  else if (currentModel === "ndvi") url = `/api/ndvi/chart?xa=${encodeURIComponent(xa)}`;
  else if (currentModel === "tvdi") url = `/api/tvdi/chart?xa=${encodeURIComponent(xa)}`;

  const res = await fetch(url);
  const data = await res.json();
  renderChart(data);
}

// ===================== LEVELS =====================
function getLSTLevel(C) {
  if (C < 25) return "Mát lạnh";
  if (C < 30) return "Dễ chịu";
  if (C < 35) return "Nóng";
  if (C < 40) return "Rất nóng";
  return "Nguy hiểm";
}
function getNDVILevel(v) {
  if (v < 0.1) return "Rất kém";
  if (v < 0.2) return "Kém";
  if (v < 0.3) return "Trung bình";
  if (v < 0.5) return "Tốt";
  return "Rất tốt";
}
function getTVDILevel(v) {
  if (v < 0.2) return "Đất ướt";
  if (v < 0.4) return "Ẩm";
  if (v < 0.6) return "Bình thường";
  if (v < 0.8) return "Khô hạn nhẹ";
  return "Hạn nghiêm trọng";
}

// ===================== FORECAST GRID =====================
// ✅ HIỂN THỊ NGÀY = hôm nay (i=0), +1, +2... cho tất cả model
function renderForecastGrid(data) {
  const grid = document.getElementById("forecastGrid");
  if (!grid) return;
  grid.innerHTML = "";

  const baseToday = _startOfToday();

  // -------- LST --------
  if (data && data.pred_LST_K) {
    data.pred_LST_K.forEach((K, i) => {
      const C = K - 273.15;

      // ✅ bắt đầu từ hôm nay
      const date = _addDays(baseToday, i);

      const weekday = _fmtWeekdayVI(date);
      const dateStr = _fmtDateVI(date);

      let color = "#1e88e5";
      if (C >= 25 && C <= 30) color = "#fbc02d";
      if (C > 30) color = "#e53935";

      grid.innerHTML += `
        <div class="dayCard" style="border-top:5px solid ${color}">
          <div class="day">${weekday}</div>
          <div class="date">${dateStr}</div>
          <div class="valueMain" style="color:${color}">${C.toFixed(1)}°C</div>
          <div class="valueSub">${getLSTLevel(C)}</div>
        </div>`;
    });
  }

  // -------- NDVI (robust schema) --------
  const ndviArr =
    (Array.isArray(data?.data) ? data.data : null) ||
    (Array.isArray(data?.forecast) ? data.forecast : null) ||
    (Array.isArray(data?.predictions) ? data.predictions : null) ||
    (Array.isArray(data?.items) ? data.items : null) ||
    [];

  const _getNdviVal = (item) => {
    if (item == null) return undefined;
    if (typeof item === "number") return item;
    if (item.predicted_ndvi !== undefined) return item.predicted_ndvi;
    if (item.ndvi !== undefined) return item.ndvi;
    if (item.value !== undefined) return item.value;
    if (item.yhat !== undefined) return item.yhat;
    if (item.pred !== undefined) return item.pred;
    return undefined;
  };

  if (ndviArr.length && _getNdviVal(ndviArr[0]) !== undefined) {
    ndviArr.forEach((item, i) => {
      const ndvi = Number(_getNdviVal(item));
      if (!Number.isFinite(ndvi)) return;

      // ✅ bắt đầu từ hôm nay
      const dateObj = _addDays(baseToday, i);

      const dateStr = _fmtDateVI(dateObj);
      const weekday = _fmtWeekdayVI(dateObj);

      let color = "#b81414";
      if (ndvi >= 0.2 && ndvi <= 0.4) color = "#f57f17";
      if (ndvi > 0.4) color = "#0b8f38";

      grid.innerHTML += `
        <div class="dayCard" style="border-top:5px solid ${color}">
          <div class="day">${weekday}</div>
          <div class="date">${dateStr}</div>
          <div class="valueMain" style="color:${color}">${ndvi.toFixed(3)}</div>
          <div class="valueSub">${getNDVILevel(ndvi)}</div>
        </div>`;
    });
  }

  // -------- TVDI --------
  if (data && data.prediction_real) {
    data.prediction_real.forEach((v, i) => {
      // ✅ bắt đầu từ hôm nay
      const dateObj = _addDays(baseToday, i);

      const weekday = _fmtWeekdayVI(dateObj);
      const dateStr = _fmtDateVI(dateObj);

      let color = "#1565c0";
      if (v >= 0.4 && v <= 0.6) color = "#f57f17";
      if (v > 0.6) color = "#c62828";

      grid.innerHTML += `
        <div class="dayCard" style="border-top:5px solid ${color}">
          <div style="font-weight:bold;font-size:18px;" class="monthLabel">${weekday}</div>
          <div class="day">${dateStr}</div>
          <div class="valueMain" style="color:${color}">${Number(v).toFixed(3)}</div>
          <div class="valueSub">${getTVDILevel(Number(v))}</div>
        </div>`;
    });
  }
}

// ===================== CHART =====================
// ✅ DỰ BÁO trên chart cũng hiển thị ngày = hôm nay (i=0), +1, +2...
function renderChart(data) {
  const canvas = document.getElementById("chartCanvas");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");

  const history = data?.history || [];
  const forecast = data?.forecast || [];

  const historyLabels = history.map(x => x.date);
  const historyData = history.map(x => x.value);
  const forecastData = forecast.map(x => x.value);

  const baseToday = _startOfToday();

  const forecastLabels = forecast.map((_, i) => {
    // ✅ bắt đầu từ hôm nay
    const d = _addDays(baseToday, i);
    return _fmtISODate(d);
  });

  const labels = historyLabels.concat(forecastLabels);

  if (trendChart) trendChart.destroy();

  trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Lịch sử",
          data: historyData.concat(Array(forecastData.length).fill(null)),
          borderColor: "#1976d2",
          backgroundColor: "#1976d233",
          tension: 0.3,
          pointRadius: 3
        },
        {
          label: "Dự báo",
          data: Array(historyData.length).fill(null).concat(forecastData),
          borderColor: "red",
          backgroundColor: "#ff000033",
          borderDash: [6, 6],
          tension: 0.3,
          pointRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { x: { display: true }, y: { display: true } }
    }
  });
}

// ===================== LOAD XA LIST =====================
async function loadXaList() {
  const res = await fetch("/api/xa/list");
  const list = await res.json();

  const select = document.getElementById("xaSelectGlobal");
  if (!select) return;

  select.innerHTML = `<option value="">Tìm phường/xã...</option>`;
  list.forEach(xa => {
    select.innerHTML += `<option value="${xa}">${xa}</option>`;
  });
}

/* =========================================================
   LST MAP
========================================================= */
(function () {
  const V_MIN = 1.0;
  const V_MAX = 45.0;
  const PALETTE = ["#0000FF", "#0066FF", "#00FFFF", "#00FF00", "#FFFF00", "#FFCC00","#FF6600", "#FF0000"];

  function clamp01(x){ return Math.max(0, Math.min(1, x)); }
  function colorOf(v){
    if (v === null || v === undefined || Number.isNaN(v)) return "#D3D3D3";
    const t = clamp01((v - V_MIN) / (V_MAX - V_MIN));
    const i = Math.min(PALETTE.length - 1, Math.floor(t * (PALETTE.length - 1)));
    return PALETTE[i];
  }

  let map = null;
  let layer = null;

  function initMapOnce(){
    if (map) return;
    map = L.map("lstLeafletMap", { zoomControl:true, attributionControl:false }).setView([10.78, 106.68], 10);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19 }).addTo(map);
    window.lstMapInstance = map;
    renderLegend();
  }

  function renderLegend(){
    const el = document.getElementById("lstMapLegend");
    if (!el) return;

    const step = (V_MAX - V_MIN) / PALETTE.length;
    let html = `<div style="display:flex;gap:10px;flex-wrap:wrap;">`;
    PALETTE.forEach((c, i) => {
      const a = (V_MIN + i*step).toFixed(1);
      const b = (V_MIN + (i+1)*step).toFixed(1);
      html += `
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="width:14px;height:14px;background:${c};display:inline-block;"></span>
          <span>${a}–${b}°C</span>
        </div>`;
    });
    html += `
      <div style="display:flex;align-items:center;gap:6px;">
        <span style="width:14px;height:14px;background:#D3D3D3;display:inline-block;"></span>
        <span>No data</span>
      </div>`;
    html += `</div>`;
    el.innerHTML = html;
  }

  async function loadGeojson(date){
    const r = await fetch(`/api/lst/geojson?date=${encodeURIComponent(date)}`);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async function draw(date){
    initMapOnce();
    const gj = await loadGeojson(date);
    if (layer) layer.remove();

    layer = L.geoJSON(gj, {
      style: f => ({
        color: "white",
        weight: 0.4,
        fillOpacity: 0.85,
        fillColor: colorOf(f.properties.lst_c)
      }),
      onEachFeature: (f, l) => {
        const v = f.properties.lst_c;
        l.bindTooltip(`<b>${f.properties._key}</b><br>LST: ${v == null ? "No data" : v.toFixed(2) + " °C"}`, { sticky: true });
      }
    }).addTo(map);

    try { map.fitBounds(layer.getBounds(), { padding:[10,10] }); } catch(e){}
    setTimeout(() => map.invalidateSize(), 200);
  }

  async function loadAvailableDates(){
    const r = await fetch("/api/lst/available_dates");
    if (!r.ok) throw new Error(await r.text());
    const data = await r.json();
    return data.dates || [];
  }

  function fillDateSelect(selectEl, dates){
    selectEl.innerHTML = "";
    for (const d of dates){
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d.split("-").reverse().join("/");
      selectEl.appendChild(opt);
    }
  }

  window.initLstMapUI = async function initLstMapUI() {
    const btn = document.getElementById("btnLoadLstMap");
    const dateSelect = document.getElementById("lstMapDate");
    if (!btn || !dateSelect) return;

    try {
      showLoading("Đang tải danh sách ngày LST...");
      const dates = await loadAvailableDates();
      if (dates.length === 0){
        btn.disabled = true; dateSelect.innerHTML = "";
        return;
      }

      fillDateSelect(dateSelect, dates);
      dateSelect.value = dates[dates.length - 1];

      btn.addEventListener("click", async () => {
        showLoading("Đang tải bản đồ LST...");
        try { await draw(dateSelect.value); }
        catch (e) { alert("Lỗi bản đồ LST: " + (e.message || e)); }
        finally { hideLoading(); }
      });

//      if (currentModel === "lst") btn.click();
    } catch(e){
      console.error(e);
    } finally {
      hideLoading();
    }
  };
})();

/* =========================================================
   NDVI MAP
========================================================= */
(function () {
  const V_MIN = -0.1;
  const V_MAX = 1.0;
  const PALETTE = ['#FF0000', '#FF7F00', '#FFFF00', '#ADFF2F', '#00FF00', '#00FFFF', '#007FFF','#0000FF'];

  function clamp01(x){ return Math.max(0, Math.min(1, x)); }
  function colorOf(v){
    if (v === null || v === undefined || Number.isNaN(v)) return "#D3D3D3";
    const t = clamp01((v - V_MIN) / (V_MAX - V_MIN));
    const i = Math.min(PALETTE.length - 1, Math.floor(t * (PALETTE.length - 1)));
    return PALETTE[i];
  }

  let map = null;
  let layer = null;

  function initMapOnce(){
    if (map) return;
    map = L.map("ndviLeafletMap", { zoomControl:true, attributionControl:false }).setView([10.78, 106.68], 10);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19 }).addTo(map);
    window.ndviMapInstance = map;
    renderLegend();
  }

  function renderLegend(){
    const el = document.getElementById("ndviMapLegend");
    if (!el) return;

    const step = (V_MAX - V_MIN) / PALETTE.length;
    let html = `<div style="display:flex;gap:10px;flex-wrap:wrap;">`;
    PALETTE.forEach((c, i) => {
      const a = (V_MIN + i*step).toFixed(2);
      const b = (V_MIN + (i+1)*step).toFixed(2);
      html += `
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="width:14px;height:14px;background:${c};display:inline-block;"></span>
          <span>${a}–${b}</span>
        </div>`;
    });
    html += `
      <div style="display:flex;align-items:center;gap:6px;">
        <span style="width:14px;height:14px;background:#D3D3D3;display:inline-block;"></span>
        <span>No data</span>
      </div>`;
    html += `</div>`;
    el.innerHTML = html;
  }

  async function loadGeojson(date){
    const r = await fetch(`/api/ndvi/geojson?date=${encodeURIComponent(date)}`);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async function draw(date){
    initMapOnce();
    const gj = await loadGeojson(date);
    if (layer) layer.remove();

    layer = L.geoJSON(gj, {
      style: f => ({
        color: "white",
        weight: 0.4,
        fillOpacity: 0.85,
        fillColor: colorOf(f.properties.ndvi)
      }),
      onEachFeature: (f, l) => {
        const v = f.properties.ndvi;
        l.bindTooltip(`<b>${f.properties._key}</b><br>NDVI: ${v == null ? "No data" : Number(v).toFixed(4)}`, { sticky: true });
      }
    }).addTo(map);

    try { map.fitBounds(layer.getBounds(), { padding:[10,10] }); } catch(e){}
    setTimeout(() => map.invalidateSize(), 200);
  }

  async function loadAvailableDates(){
    const r = await fetch("/api/ndvi/available_dates");
    if (!r.ok) throw new Error(await r.text());
    const data = await r.json();
    return data.dates || [];
  }

  function fillDateSelect(selectEl, dates){
    selectEl.innerHTML = "";
    for (const d of dates){
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d.split("-").reverse().join("/");
      selectEl.appendChild(opt);
    }
  }

  window.initNdviMapUI = async function initNdviMapUI() {
    const btn = document.getElementById("btnLoadNdviMap");
    const dateSelect = document.getElementById("ndviMapDate");
    if (!btn || !dateSelect) return;

    try {
      showLoading("Đang tải danh sách ngày NDVI...");
      const dates = await loadAvailableDates();
      if (dates.length === 0){
        btn.disabled = true; dateSelect.innerHTML = "";
        return;
      }

      fillDateSelect(dateSelect, dates);
      dateSelect.value = dates[dates.length - 1];

      btn.addEventListener("click", async () => {
        showLoading("Đang tải bản đồ NDVI...");
        try { await draw(dateSelect.value); }
        catch (e) { alert("Lỗi bản đồ NDVI: " + (e.message || e)); }
        finally { hideLoading(); }
      });

      if (currentModel === "ndvi") btn.click();
    } catch(e){
      console.error(e);
    } finally {
      hideLoading();
    }
  };
})();

/* =========================================================
   TVDI MAP
========================================================= */
(function () {
  const V_MIN = 0.0;
  const V_MAX = 1.0;
  const PALETTE = ['#066b00', '#0bc400', '#0ce100', '#00ff00', '#ffff00', '#ffcc00', '#ff6600', '#ff0000'];

  function clamp01(x){ return Math.max(0, Math.min(1, x)); }
  function colorOf(v){
    if (v === null || v === undefined || Number.isNaN(v)) return "#D3D3D3";
    const t = clamp01((v - V_MIN) / (V_MAX - V_MIN));
    const i = Math.min(PALETTE.length - 1, Math.floor(t * (PALETTE.length - 1)));
    return PALETTE[i];
  }

  let map = null;
  let layer = null;

  function initMapOnce(){
    if (map) return;
    map = L.map("tvdiLeafletMap", { zoomControl:true, attributionControl:false }).setView([10.78, 106.68], 10);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19 }).addTo(map);
    window.tvdiMapInstance = map;
    renderLegend();
  }

  function renderLegend(){
    const el = document.getElementById("tvdiMapLegend");
    if (!el) return;

    const step = (V_MAX - V_MIN) / PALETTE.length;
    let html = `<div style="display:flex;gap:10px;flex-wrap:wrap;">`;
    PALETTE.forEach((c, i) => {
      const a = (V_MIN + i*step).toFixed(2);
      const b = (V_MIN + (i+1)*step).toFixed(2);
      html += `
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="width:14px;height:14px;background:${c};display:inline-block;"></span>
          <span>${a}–${b}</span>
        </div>`;
    });
    html += `
      <div style="display:flex;align-items:center;gap:6px;">
        <span style="width:14px;height:14px;background:#D3D3D3;display:inline-block;"></span>
        <span>No data</span>
      </div>`;
    html += `</div>`;
    el.innerHTML = html;
  }

  async function loadGeojson(month){
    const r = await fetch(`/api/tvdi/geojson?date=${encodeURIComponent(month)}`);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async function draw(month){
    initMapOnce();
    const gj = await loadGeojson(month);
    if (layer) layer.remove();

    layer = L.geoJSON(gj, {
      style: f => ({
        color: "white",
        weight: 0.4,
        fillOpacity: 0.85,
        fillColor: colorOf(f.properties.tvdi)
      }),
      onEachFeature: (f, l) => {
        const v = f.properties.tvdi;
        l.bindTooltip(`<b>${f.properties._key}</b><br>TVDI: ${v == null ? "No data" : Number(v).toFixed(4)}<br>${v == null ? "" : getTVDILevel(Number(v))}`, { sticky: true });
      }
    }).addTo(map);

    try { map.fitBounds(layer.getBounds(), { padding:[10,10] }); } catch(e){}
    setTimeout(() => map.invalidateSize(), 200);
  }

  async function loadAvailableMonths(){
    const r = await fetch("/api/tvdi/available_dates");
    if (!r.ok) throw new Error(await r.text());
    const data = await r.json();
    return data.dates || [];
  }

  function fillMonthSelect(selectEl, months){
    selectEl.innerHTML = "";
    for (const m of months){
      const opt = document.createElement("option");
      opt.value = m;
      const parts = m.split("-");
      opt.textContent = `${parts[1]}/${parts[0]}`;
      selectEl.appendChild(opt);
    }
  }

  window.initTvdiMapUI = async function initTvdiMapUI() {
    const btn = document.getElementById("btnLoadTvdiMap");
    const monthSelect = document.getElementById("tvdiMapDate");
    if (!btn || !monthSelect) return;

    try {
      showLoading("Đang tải danh sách tháng TVDI...");
      const months = await loadAvailableMonths();

      if (months.length === 0){
        btn.disabled = true;
        monthSelect.innerHTML = "";
        return;
      }

      fillMonthSelect(monthSelect, months);
      monthSelect.value = months[months.length - 1];

      btn.addEventListener("click", async () => {
        showLoading("Đang tải bản đồ TVDI...");
        try { await draw(monthSelect.value); }
        catch (e) { alert("Lỗi bản đồ TVDI: " + (e.message || e)); }
        finally { hideLoading(); }
      });

      if (currentModel === "tvdi") btn.click();
    } catch(e){
      console.error(e);
    } finally {
      hideLoading();
    }
  };
})();
