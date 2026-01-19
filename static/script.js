console.log("script.js loaded");

/* =========================
   API BASE
========================= */
const API = "http://127.0.0.1:5000";

/* =========================
   AUTH
========================= */
function register() {
    fetch(`${API}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name: regName.value,
            email: regEmail.value,
            password: regPassword.value
        })
    })
    .then(r => r.json())
    .then(d => registerMsg.textContent = d.message || d.error);
}

function login() {
    fetch(`${API}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            email: email.value,
            password: password.value
        })
    })
    .then(r => r.json())
    .then(d => {
        if (d.error) errorMsg.textContent = d.error;
        else {
            localStorage.setItem("user_id", d.user_id);
            localStorage.setItem("user_name", d.name);
            location.href = "dashboard.html";
        }
    });
}

function logout() {
    localStorage.clear();
    location.href = "login.html";
}

/* =========================
   PAGE LOAD
========================= */
document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("userName")) {
        userName.textContent = localStorage.getItem("user_name");

        loadSummary();
        loadBudgetStatus();
        loadPrediction();
        loadMLTrend();
        loadCategoryMLPrediction();
    }

    document.getElementById("addExpenseBtn")?.addEventListener("click", addExpense);
    document.getElementById("saveBudgetBtn")?.addEventListener("click", setBudget);

    if (document.getElementById("expenseTable")) {
        loadExpenses();
    }
});

/* =========================
   ADD EXPENSE
========================= */
function addExpense() {
    const amount = document.getElementById("amount").value;
    const category = document.getElementById("category").value;
    const msg = document.getElementById("successMsg");

    if (!amount || !category) {
        msg.textContent = "Enter amount and category";
        msg.style.color = "red";
        return;
    }

    fetch(`${API}/add-expense`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_id: localStorage.getItem("user_id"),
            amount,
            category
        })
    })
    .then(r => r.json())
    .then(() => {
        msg.textContent = "Expense added successfully";
        msg.style.color = "green";

        // 🔥 FORCE REFRESH ALL DEPENDENT DATA
        loadSummary();
        loadBudgetStatus();
        loadPrediction();
        loadMLTrend();
        loadCategoryChart();
        loadCategoryMLPrediction();
    });
}


/* =========================
   SUMMARY + CHARTS
========================= */
let expenseChart = null;
let categoryChart = null;

function loadSummary() {
    fetch(`${API}/summary/${localStorage.getItem("user_id")}`)
    .then(r => r.json())
    .then(d => {
        weeklyTotal.textContent = d.weekly_total;
        monthlyTotal.textContent = d.monthly_total;
        streakCount.textContent = d.current_streak + " Days";

        renderExpenseChart(d.weekly_total, d.monthly_total);
        loadCategoryChart();
    });
}

function renderExpenseChart(weekly, monthly) {
    const canvas = document.getElementById("expenseChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (expenseChart) expenseChart.destroy();

    expenseChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Weekly", "Monthly"],
            datasets: [{
                label: "Expenses (₹)",
                data: [weekly, monthly],
                backgroundColor: ["#667eea", "#764ba2"]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

function loadCategoryChart() {
    fetch(`${API}/category-summary/${localStorage.getItem("user_id")}`)
    .then(r => r.json())
    .then(d => {
        if (!d.categories.length) return;

        const canvas = document.getElementById("categoryChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        if (categoryChart) categoryChart.destroy();

        categoryChart = new Chart(ctx, {
            type: "pie",
            data: {
                labels: d.categories,
                datasets: [{
                    data: d.amounts,
                    backgroundColor: [
                        "#ff6384",
                        "#36a2eb",
                        "#ffce56",
                        "#4bc0c0",
                        "#9966ff",
                        "#ff9f40"
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    });
}

/* =========================
   BUDGET
========================= */
function setBudget() {
    fetch(`${API}/set-budget`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_id: localStorage.getItem("user_id"),
            budget: budgetInput.value
        })
    }).then(loadBudgetStatus);
}

function loadBudgetStatus() {
    fetch(`${API}/budget-status/${localStorage.getItem("user_id")}`)
    .then(r => r.json())
    .then(d => {
        if (d.status === "not_set") {
            budgetStatus.textContent = "No budget set";
            budgetStatus.style.color = "gray";
        } else {
            budgetStatus.textContent =
                `Spent ₹${d.spent} / ₹${d.budget} (${d.percent}%)`;
            budgetStatus.style.color =
                d.status === "safe" ? "green" :
                d.status === "warning" ? "orange" : "red";
        }
    });
}

/* =========================
   MONTH PREDICTION
========================= */
function loadPrediction() {
    fetch(`${API}/predict-month/${localStorage.getItem("user_id")}`)
        .then(r => r.json())
        .then(d => {
            const amountEl = document.getElementById("predictedAmount");
            const noteEl = document.getElementById("predictionNote");

            if (!amountEl || !noteEl) return;

            amountEl.textContent = d.predicted_month_total;
            noteEl.textContent = `Avg daily spend: ₹${d.daily_average}`;
        })
        .catch(() => {
            document.getElementById("predictedAmount").textContent = "0";
            document.getElementById("predictionNote").textContent = "Prediction unavailable";
        });
}


/* =========================
   ML TREND
========================= */
let mlChart = null;

function loadMLTrend() {
    fetch(`${API}/ml-trend/${localStorage.getItem("user_id")}`)
        .then(r => r.json())
        .then(d => {
            const trendEl = document.getElementById("mlTrend");
            const insightEl = document.getElementById("mlInsight");

            if (!trendEl || !insightEl) return;

            if (d.status === "not_enough_data") {
                trendEl.textContent = "Not enough data";
                insightEl.textContent = "Add at least 5 days of expenses";
                return;
            }

            trendEl.textContent = d.trend.toUpperCase();
            insightEl.textContent = `Avg daily change: ₹${d.daily_change}`;

            renderMLChart(d.labels, d.actual, d.predicted);
        })
        .catch(() => {
            console.error("ML trend failed");
        });
}

function renderMLChart(labels, actual, predicted) {
    const canvas = document.getElementById("mlChart");
    if (!canvas) return;

    if (mlChart) mlChart.destroy();

    mlChart = new Chart(canvas.getContext("2d"), {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Actual Spend",
                    data: actual,
                    borderWidth: 2,
                    tension: 0.3
                },
                {
                    label: "ML Trend",
                    data: predicted,
                    borderDash: [6, 6],
                    borderWidth: 2,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}



function renderMLChart(actual, predicted) {
    const canvas = document.getElementById("mlChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (mlChart) mlChart.destroy();

    mlChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: actual.map((_, i) => `Day ${i + 1}`),
            datasets: [
                { label: "Actual", data: actual },
                { label: "ML Trend", data: predicted, borderDash: [5, 5] }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

/* =========================
   CATEGORY ML
========================= */
function loadCategoryMLPrediction() {
    fetch(`${API}/ml-category-predict/${localStorage.getItem("user_id")}`)
    .then(r => r.json())
    .then(d => {
        mlCategoryTable.innerHTML = "";

        if (d.status === "not_enough_data") {
            mlCategoryTable.innerHTML =
                "<tr><td colspan='3'>Not enough data for ML</td></tr>";
            return;
        }

        d.predictions.forEach(p => {
            mlCategoryTable.innerHTML += `
                <tr>
                    <td>${p.category}</td>
                    <td>₹ ${p.predicted_month_total}</td>
                    <td>${p.trend.toUpperCase()}</td>
                </tr>`;
        });
    });
}



document.addEventListener("DOMContentLoaded", () => {
    const table = document.getElementById("expenseTable");
    if (!table) return; // not history page

    const userId = localStorage.getItem("user_id");
    if (!userId) {
        alert("Please login again");
        window.location.href = "login.html";
        return;
    }

    fetch(`http://127.0.0.1:5000/expenses/${userId}`)
        .then(res => {
            if (!res.ok) throw new Error("API error");
            return res.json();
        })
        .then(data => {
            table.innerHTML = "";
            let total = 0;

            if (data.expenses.length === 0) {
                table.innerHTML = `
                    <tr>
                        <td colspan="3" style="text-align:center;">
                            No expenses found
                        </td>
                    </tr>`;
                return;
            }

            data.expenses.forEach(e => {
                total += e.amount;
                table.innerHTML += `
                    <tr>
                        <td>${e.date}</td>
                        <td>${e.category}</td>
                        <td style="text-align:right;">₹ ${e.amount}</td>
                    </tr>`;
            });

            document.getElementById("totalAmount").textContent = total;
        })
        .catch(err => {
            console.error("History load failed:", err);
            table.innerHTML = `
                <tr>
                    <td colspan="3" style="text-align:center;color:red;">
                        Failed to load expenses
                    </td>
                </tr>`;
        });
});


function goBack() {
    location.href = "dashboard.html";
}
