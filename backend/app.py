from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta
from sqlalchemy import func
from sklearn.linear_model import LinearRegression
import numpy as np
import calendar

from email_service import send_reminder_email

# =======================
# APP SETUP
# =======================

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =======================
# DATABASE MODELS
# =======================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, default=date.today)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, unique=True)
    monthly_budget = db.Column(db.Float, nullable=False)
    alert_sent = db.Column(db.Boolean, default=False)

class Streak(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, unique=True)
    current_streak = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.Date)

with app.app_context():
    db.create_all()

# =======================
# ROOT
# =======================

@app.route("/")
def home():
    return jsonify({"status": "Finance Tracker backend running"})

# =======================
# AUTH
# =======================

@app.route("/register", methods=["POST"])
def register():
    data = request.json or {}

    if not all(k in data for k in ("name", "email", "password")):
        return jsonify({"error": "Missing fields"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "User already exists"}), 400

    user = User(
        name=data["name"],
        email=data["email"],
        password=generate_password_hash(data["password"])
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Registered successfully"})

@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    user = User.query.filter_by(email=data.get("email")).first()

    if not user or not check_password_hash(user.password, data.get("password", "")):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"user_id": user.id, "name": user.name})

# =======================
# ADD EXPENSE + STREAK + EMAIL
# =======================

@app.route("/add-expense", methods=["POST"])
def add_expense():
    data = request.json

    user_id = int(data["user_id"])
    amount = float(data["amount"])
    category = data["category"]

    db.session.add(Transaction(
        user_id=user_id,
        amount=amount,
        category=category
    ))

    today = date.today()

    # ---------- STREAK ----------
    streak = Streak.query.filter_by(user_id=user_id).first()
    if not streak:
        streak = Streak(user_id=user_id, current_streak=1, last_updated=today)
    elif streak.last_updated == today - timedelta(days=1):
        streak.current_streak += 1
        streak.last_updated = today
    else:
        streak.current_streak = 1
        streak.last_updated = today

    db.session.add(streak)

    # ---------- BUDGET EMAIL ----------
    budget = Budget.query.filter_by(user_id=user_id).first()
    user = User.query.get(user_id)

    if budget and not budget.alert_sent:
        month_start = today.replace(day=1)
        spent = db.session.query(func.sum(Transaction.amount))\
            .filter(
                Transaction.user_id == user_id,
                Transaction.date >= month_start
            ).scalar() or 0

        if spent > budget.monthly_budget:
            send_reminder_email(
                to_email=user.email,
                user_name=user.name,
                spent=round(spent, 2),
                budget=budget.monthly_budget
            )
            budget.alert_sent = True
            db.session.add(budget)

    db.session.commit()
    return jsonify({"current_streak": streak.current_streak})

# =======================
# SUMMARY (FIXED)
# =======================

@app.route("/summary/<int:user_id>")
def summary(user_id):
    today = date.today()
    week_start = today - timedelta(days=6)
    month_start = today.replace(day=1)

    weekly = db.session.query(func.sum(Transaction.amount))\
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= week_start,
            Transaction.date <= today
        ).scalar() or 0

    monthly = db.session.query(func.sum(Transaction.amount))\
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= month_start,
            Transaction.date <= today
        ).scalar() or 0

    streak = Streak.query.filter_by(user_id=user_id).first()

    return jsonify({
        "weekly_total": float(weekly),
        "monthly_total": float(monthly),
        "current_streak": streak.current_streak if streak else 0
    })

# =======================
# CATEGORY PIE
# =======================

@app.route("/category-summary/<int:user_id>")
def category_summary(user_id):
    rows = db.session.query(
        Transaction.category,
        func.sum(Transaction.amount)
    ).filter(Transaction.user_id == user_id)\
     .group_by(Transaction.category).all()

    return jsonify({
        "categories": [r[0] for r in rows],
        "amounts": [float(r[1]) for r in rows]
    })

# =======================
# HISTORY (FIXED)
# =======================

@app.route("/expenses/<int:user_id>")
def expenses(user_id):
    records = Transaction.query.filter_by(user_id=user_id)\
        .order_by(Transaction.date.desc()).all()

    return jsonify({
        "expenses": [
            {
                "date": r.date.strftime("%Y-%m-%d"),
                "category": r.category,
                "amount": float(r.amount)
            }
            for r in records
        ]
    })

# =======================
# BUDGET
# =======================

@app.route("/set-budget", methods=["POST"])
def set_budget():
    data = request.json
    user_id = int(data["user_id"])
    amount = float(data["budget"])

    budget = Budget.query.filter_by(user_id=user_id).first()
    if not budget:
        budget = Budget(
            user_id=user_id,
            monthly_budget=amount,
            alert_sent=False
        )
    else:
        budget.monthly_budget = amount
        budget.alert_sent = False

    db.session.add(budget)
    db.session.commit()
    return jsonify({"message": "Budget saved"})

@app.route("/budget-status/<int:user_id>")
def budget_status(user_id):
    spent = db.session.query(func.sum(Transaction.amount))\
        .filter(Transaction.user_id == user_id).scalar() or 0

    budget = Budget.query.filter_by(user_id=user_id).first()
    if not budget:
        return jsonify({"status": "not_set"})

    percent = round((spent / budget.monthly_budget) * 100, 2)

    status = "safe"
    if percent >= 80 and percent < 100:
        status = "warning"
    elif percent >= 100:
        status = "exceeded"

    return jsonify({
        "budget": float(budget.monthly_budget),
        "spent": float(spent),
        "percent": percent,
        "status": status
    })

# =======================
# ML TREND
# =======================

@app.route("/ml-trend/<int:user_id>")
def ml_trend(user_id):
    txs = Transaction.query.filter_by(user_id=user_id)\
        .order_by(Transaction.date.asc()).all()

    if len(txs) < 5:
        return jsonify({"status": "not_enough_data"})

    # ---- group by date ----
    daily = {}
    for t in txs:
        key = t.date.strftime("%Y-%m-%d")
        daily[key] = daily.get(key, 0) + t.amount

    dates = sorted(daily.keys())
    y = np.array([daily[d] for d in dates], dtype=float)

    # ---- ML regression ----
    X = np.arange(len(y)).reshape(-1, 1)
    model = LinearRegression()
    model.fit(X, y)
    predicted = model.predict(X)

    # ---- TRUE average daily change ----
    if len(y) > 1:
        daily_changes = np.diff(y)
        avg_daily_change = round(float(np.mean(daily_changes)), 2)
    else:
        avg_daily_change = 0.0

    # ---- trend direction ----
    if avg_daily_change > 0:
        trend = "increasing"
    elif avg_daily_change < 0:
        trend = "decreasing"
    else:
        trend = "stable"

    return jsonify({
        "trend": trend,
        "daily_change": avg_daily_change,
        "actual": y.round(2).tolist(),
        "predicted": predicted.round(2).tolist(),
        "labels": dates
    })

# =======================
# CATEGORY ML
# =======================

@app.route("/ml-category-predict/<int:user_id>")
def ml_category_predict(user_id):
    today = date.today()
    month_start = today.replace(day=1)

    txs = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.date >= month_start
    ).all()

    if len(txs) < 5:
        return jsonify({"status": "not_enough_data"})

    grouped = {}
    for t in txs:
        grouped.setdefault(t.category, []).append(t.amount)

    days = calendar.monthrange(today.year, today.month)[1]
    predictions = []

    for cat, values in grouped.items():
        if len(values) < 3:
            continue
        avg = sum(values) / len(values)
        predictions.append({
            "category": cat,
            "predicted_month_total": round(avg * days, 2),
            "trend": "stable"
        })

    return jsonify({"status": "ok", "predictions": predictions})
@app.route("/predict-month/<int:user_id>")
def predict_month(user_id):
    today = date.today()
    month_start = today.replace(day=1)

    # Total spent so far this month
    spent = db.session.query(func.sum(Transaction.amount))\
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= month_start,
            Transaction.date <= today
        ).scalar() or 0

    days_passed = today.day
    days_in_month = calendar.monthrange(today.year, today.month)[1]

    if days_passed == 0:
        daily_avg = 0
    else:
        daily_avg = spent / days_passed

    predicted_total = round(daily_avg * days_in_month, 2)

    return jsonify({
        "daily_average": round(daily_avg, 2),
        "predicted_month_total": predicted_total
    })


# =======================
# RUN
# =======================

if __name__ == "__main__":
    app.run(debug=True)
