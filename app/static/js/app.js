let currentModel = "lst";

// =======================================
// 1) Khi đổi tab → đổi model và load lại
// =======================================
function switchTab(tab) {
    currentModel = tab;

    document.getElementById("tab-lst").classList.remove("active");
    document.getElementById("tab-ndvi").classList.remove("active");
    document.getElementById("tab-tvdi").classList.remove("active");

    document.getElementById(`tab-${tab}`).classList.add("active");

    const title = {
        lst: "Dự báo LST",
        ndvi: "Dự báo NDVI",
        tvdi: "Dự báo TVDI",
    }[tab];

    document.getElementById("titlePage").innerText = title;

    autoRun();
}


// =======================================
// 2) Auto-run khi đổi xã
// =======================================
document.getElementById("xaSelectGlobal").addEventListener("change", function () {
    autoRun();
});


// =======================================
// 3) Hàm tự chạy
// =======================================
function autoRun() {
    const xa = document.getElementById("xaSelectGlobal").value;
    if (!xa) return;
    runModel(xa);
    loadChart(xa);
}
async function loadChart(xa) {
    let url = "";

    if (currentModel === "lst") {
        url = `/api/lst/chart?xa=${encodeURIComponent(xa)}`;
    }
    else if (currentModel === "ndvi") {
        url = `/api/ndvi/chart?xa=${encodeURIComponent(xa)}`;
    }
    else if (currentModel === "tvdi") {
        url = `/api/tvdi/chart?xa=${encodeURIComponent(xa)}`;
    }

    const res = await fetch(url);
    const data = await res.json();

    renderChart(data);
}


// =======================================
// 4) Gọi API theo tab
// =======================================
function runModel(xa) {
    let url = "";

    if (currentModel === "lst") {
        url = `/api/lst/auto_predict7?xa=${encodeURIComponent(xa)}`;
    }
    else if (currentModel === "ndvi") {
        url = `/api/ndvi/predict?xa=${encodeURIComponent(xa)}`;
    }
    else if (currentModel === "tvdi") {
        url = `/api/tvdi/auto_predict?xa=${encodeURIComponent(xa)}`;
    }

    fetch(url)
        .then(res => res.json())
        .then(data => renderResult(data))
        .catch(err => console.error(err));
}


// =======================================
// 5) Nút vẫn hoạt động
// =======================================
//document.getElementById("btnRunModel").addEventListener("click", function () {
//    autoRun();
//});


// =======================================
// 6) Render kết quả text
// =======================================
function renderResult(data) {

    renderForecastGrid(data);

    const box = document.getElementById("resultBox");
    box.innerHTML = "";

    if (data.error) {
        box.innerHTML = `<p style="color:red;">${data.error}</p>`;
        return;
    }

    let html = `<b>Xã:</b> ${data.xa || data.ten_xa}<br><br><ul>`;

    // LST
    if (data.pred_LST_K) {
        const lastDate = new Date(data.last_date);
        data.pred_LST_K.forEach((K, i) => {
            const C = K - 273.15;
            const d = new Date(lastDate);
            d.setDate(d.getDate() + (i + 1) * 7);
            html += `<li>Tuần ${i + 1} (${d.toISOString().split("T")[0]}): <b>${C.toFixed(2)}°C</b></li>`;
        });
    }

    // NDVI
    if (data.data && data.data[0]?.predicted_ndvi !== undefined) {
        data.data.forEach(item => {
            const d = new Date(item.date).toISOString().split("T")[0];
            html += `<li>Bước ${item.step} — ${d}: <b>${item.predicted_ndvi.toFixed(4)}</b></li>`;
        });
    }

    // TVDI
    if (data.prediction_real) {
        let [year, month] =
            data.history_months[data.history_months.length - 1].split("-").map(Number);

        data.prediction_real.forEach(val => {
            month++;
            if (month > 12) { month = 1; year++; }
            html += `<li>Tháng ${year}-${String(month).padStart(2, "0")}: <b>${val.toFixed(4)}</b></li>`;
        });
    }

    html += `</ul>`;
    box.innerHTML = html;
}


// =======================================
// 7) Auto load mặc định
// =======================================
//window.onload = function () {
//    document.getElementById("xaSelectGlobal").value = "An Hội Tây";
//    autoRun();
//};
window.onload = function () {
    loadXaList().then(() => {
        document.getElementById("xaSelectGlobal").value = "An Hội Tây";
        autoRun();
    });
};

// ===================== NGƯỠNG LST =====================
function getLSTLevel(C) {
    if(C < 25) return "Mát lạnh";
    if(C < 30) return "Dễ chịu";
    if(C < 35) return "Nóng";
    if(C < 40) return "Rất nóng";
    return "Nguy hiểm";
}

// ===================== NGƯỠNG NDVI =====================
function getNDVILevel(v) {
    if(v < 0.1) return "Rất kém";
    if(v < 0.2) return "Kém";
    if(v < 0.3) return "Trung bình";
    if(v < 0.5) return "Tốt";
    return "Rất tốt";
}

// ===================== NGƯỠNG TVDI =====================
function getTVDILevel(v) {
    if(v < 0.2) return "Đất ướt";
    if(v < 0.4) return "Ẩm";
    if(v < 0.6) return "Bình thường";
    if(v < 0.8) return "Khô hạn nhẹ";
    return "Hạn nghiêm trọng";
}

// =======================================
// 8) Render Forecast Grid + NGƯỠNG + KHÔNG ICON
// =======================================
function renderForecastGrid(data) {
    const grid = document.getElementById("forecastGrid");
    grid.innerHTML = "";

    // =======================
    // L S T
    // =======================
    if (data.pred_LST_K) {
        const lastDate = new Date(data.last_date);

        data.pred_LST_K.forEach((K, i) => {
            const C = K - 273.15;
            const date = new Date(lastDate);
            date.setDate(date.getDate() + (i + 1) * 7);

            const weekday = date.toLocaleDateString("vi-VN", { weekday: "short" });
            const dateStr = date.toLocaleDateString("vi-VN");

            // NGƯỠNG màu
            let color = "#1e88e5"; // mát
            if (C >= 25 && C <= 30) color = "#fbc02d"; // ấm
            if (C > 30) color = "#e53935"; // nóng

            grid.innerHTML += `
            <div class="dayCard" style="border-top:5px solid ${color}">
                <div class="day">${weekday}</div>
                <div class="date">${dateStr}</div>
                <div class="valueMain" style="color:${color}">${C.toFixed(1)}°C</div>
                <div class="valueSub">${getLSTLevel(C)}</div>

            </div>`;
        });
    }

    // =======================
    // N D V I
    // =======================
    if (data.data && data.data[0]?.predicted_ndvi !== undefined) {

        data.data.forEach(item => {
            const ndvi = item.predicted_ndvi;
            const dateStr = new Date(item.date).toLocaleDateString("vi-VN");
            const weekday = new Date(item.date).toLocaleDateString("vi-VN", { weekday: "short" });

            let color = "#b81414"; // xấu
            if (ndvi >= 0.2 && ndvi <= 0.4) color = "#f57f17"; // trung bình
            if (ndvi > 0.4) color = "#0b8f38"; // tốt

            grid.innerHTML += `
            <div class="dayCard" style="border-top:5px solid ${color}">
                <div class="day">${weekday}</div>
                <div class="date">${dateStr}</div>
                <div class="valueMain" style="color:${color}">${ndvi.toFixed(3)}</div>
                <div class="valueSub">${getNDVILevel(item.predicted_ndvi)}</div>

            </div>`;
        });
    }

    // =======================
    // T V D I
    // =======================
    if (data.prediction_real) {
        let months = data.history_months;
        let [year, month] = months[months.length - 1].split("-").map(Number);

        data.prediction_real.forEach(v => {
            month++;
            if (month > 12) { month = 1; year++; }

            let color = "#1565c0"; // ướt
            if (v >= 0.4 && v <= 0.6) color = "#f57f17"; // trung bình
            if (v > 0.6) color = "#c62828"; // khô hạn

            grid.innerHTML += `
            <div class="dayCard" style="border-top:5px solid ${color}">
                 <div style="font-weight: bold; font-size: 18px;" class="monthLabel">Tháng ${month}</div>

                <div class="day">${year}-${String(month).padStart(2,"0")}</div>
                <div class="valueMain" style="color:${color}">${v.toFixed(3)}</div>
                <div class="valueSub">${getTVDILevel(v)}</div>

            </div>`;
        });
    }
}
async function loadXaList() {
    const res = await fetch("/api/xa/list");
    const list = await res.json();

    const select = document.getElementById("xaSelectGlobal");
    select.innerHTML = `<option value="">Tìm xã...</option>`;

    list.forEach(xa => {
        select.innerHTML += `<option value="${xa}">${xa}</option>`;
    });
}
let chart; // chart instance global

async function loadChartLST(xa) {
    const res = await fetch(`/api/lst/chart?xa=${encodeURIComponent(xa)}`);
    const data = await res.json();

    if (data.error) return;

    // Gộp lịch sử + dự báo
    const labels = [
        ...data.history.map(x => x.date),
        ...data.forecast.map(x => x.date)
    ];

    const values = [
        ...data.history.map(x => x.value - 273.15),
        ...data.forecast.map(x => x.value - 273.15)
    ];

    // Nếu chart đã tồn tại → destroy để vẽ lại
    const ctx = document.getElementById("chartCanvas").getContext("2d");
    if (chart) chart.destroy();

    chart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Lịch sử",
                    data: data.history.map(x => x.value - 273.15),
                    borderColor: "#1d92d0",
                    tension: 0.3,
                },
                {
                    label: "Dự báo",
                    data: [
                        ...new Array(data.history.length).fill(null),
                        ...data.forecast.map(x => x.value - 273.15)
                    ],
                    borderColor: "#e53935",
                    borderDash: [6, 6],
                    tension: 0.3,
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: "top" }
            },
            scales: {
                y: {
                    title: {
                        display: true,
                        text: "Nhiệt độ (°C)"
                    }
                }
            }
        }
    });
}
let trendChart = null;

function renderChart(data) {
    const ctx = document.getElementById("chartCanvas").getContext("2d");

    const labels = [...data.history.map(x => x.date),
                    ...data.forecast.map(x => x.date)];

    const historyData = data.history.map(x => x.value);
    const forecastData = data.forecast.map(x => x.value);

    if (trendChart) trendChart.destroy();

    trendChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
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
            scales: {
                x: { display: true },
                y: { display: true }
            }
        }
    });
}
