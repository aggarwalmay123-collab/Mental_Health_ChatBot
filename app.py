# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, ChatMessage, ScreeningResult
import joblib
import json
db_created = False


# load env
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

# Basic FAQ and resources (can move to CSV/DB)
FAQ = {
    "how to reduce anxiety": (
        "🌿 Ways to reduce anxiety:\n"
        "- 🧘 Deep breathing exercises (4-4-4 breathing)\n"
        "- 🚶 Short walks & regular exercise\n"
        "- 📝 Journaling to clarify thoughts\n"
        "- 💤 Good sleep routine\n"
        "- 👥 Talk to a friend/counselor if persistent"
    ),
    "how to manage exam stress": "Make a revision schedule, break tasks into small parts, practice relaxation, and sleep well.",
    "what are signs of depression": "Persistent sadness, loss of interest, fatigue, changes in sleep/appetite, difficulty concentrating.",
    "how to improve sleep": "Keep fixed sleep/wake times, avoid screens before bed, and relax with a calming routine."
}

# Load model if present
MODEL_PATH = "chatbot_model.joblib"
model = None
label_encoder = None
try:
    model = joblib.load(MODEL_PATH)
    # if you saved a label encoder separately, load it too
    # label_encoder = joblib.load("label_encoder.joblib")
except Exception:
    model = None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_request
def create_tables_once():
    global db_created
    if not db_created:
        db.create_all()
        db_created = True

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("chat"))
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        if not username or not password:
            flash("Please provide username and password")
            return redirect(url_for("register"))
        if User.query.filter_by(username=username).first():
            flash("Username exists")
            return redirect(url_for("register"))
        user = User(username=username, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash("Account created. Please login")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("chat"))
        flash("Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/chat")
@login_required
def chat():
    return render_template("chat.html", username=current_user.username)

# API: send user message → predict intent / screening suggestion / crisis handling
@app.route("/api/message", methods=["POST"])
@login_required
def api_message():
    data = request.json or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "empty"}), 400

    # Save user msg
    cm_user = ChatMessage(user_id=current_user.id, sender="user", text=text)
    db.session.add(cm_user)
    db.session.commit()

    lower = text.lower()

    # immediate crisis detection (keyword-based safety net)
    crisis_keywords = ["i want to die", "i don't want to live", "i want to kill myself", "kill myself", "suicide"]
    if any(k in lower for k in crisis_keywords):
        bot_text = (
            "🚨 If you are in immediate danger call your local emergency number now. "
            "Helpline: 9152987821. "
            "You can also book a confidential urgent session here: https://yourbookinglink.com"
        )
        cm_bot = ChatMessage(user_id=current_user.id, sender="bot", text=bot_text)
        db.session.add(cm_bot); db.session.commit()
        return jsonify({"type":"crisis", "reply": bot_text})

    # FAQ detection (simple substring)
    for q, a in FAQ.items():
        if q in lower:
            cm_bot = ChatMessage(user_id=current_user.id, sender="bot", text=a)
            db.session.add(cm_bot); db.session.commit()
            return jsonify({"type":"faq", "reply": a})

    # If model available, predict intent
    if model:
        try:
            probs = model.predict_proba([text])[0]
            idx = int(probs.argmax())
            # if label_encoder used: intent = label_encoder.inverse_transform([idx])[0]
            intent = str(idx)  # fallback; you should map index->intent stored in train step
            confidence = float(probs[idx])
            # You should map intent->response; for now we return generic reply
            reply = "I understand. Would you like to take a quick screening test? (yes/no)"
            cm_bot = ChatMessage(user_id=current_user.id, sender="bot", text=reply)
            db.session.add(cm_bot); db.session.commit()
            return jsonify({"type":"model","reply":reply,"confidence":confidence})
        except Exception:
            pass

    # default
    reply = "I can help — would you like to take a quick screening test? (yes/no)"
    cm_bot = ChatMessage(user_id=current_user.id, sender="bot", text=reply)
    db.session.add(cm_bot); db.session.commit()
    return jsonify({"type":"default", "reply": reply})

# API: screening start (we'll use short 3-question PHQ-like for demo)
SCREEN_QS = [
    "Over the last 2 weeks, felt little interest or pleasure in doing things? (0-3)",
    "Over the last 2 weeks, felt down, depressed, or hopeless? (0-3)",
    "Over the last 2 weeks, had trouble sleeping or concentrating? (0-3)",
]

@app.route("/api/screening/questions", methods=["GET"])
@login_required
def screening_questions():
    return jsonify({"questions": SCREEN_QS})

@app.route("/api/screening/submit", methods=["POST"])
@login_required
def screening_submit():
    data = request.json or {}
    answers = data.get("answers", [])
    if not isinstance(answers, list) or not answers:
        return jsonify({"error": "answers required"}), 400
    score = sum(int(a) for a in answers)
    if score <= 3:
        severity = "mild"
    elif 4 <= score <= 7:
        severity = "moderate"
    else:
        severity = "severe"
    # save
    sr = ScreeningResult(user_id=current_user.id, score=score, severity=severity)
    db.session.add(sr)
    db.session.commit()

    # responses per case
    if severity == "mild":
        reply = {
            "case":"non-severe",
            "message":"You appear to have mild symptoms. Here are resources.",
            "resources": [
                {"type":"audio","title":"5-min breathing","url":"https://www.youtube.com/watch?v=SEfs5TJZ6Nk"},
                {"type":"video","title":"Grounding exercise","url":"https://www.youtube.com/watch?v=1Z3kV8e0J9M"}
            ]
        }
    elif severity == "moderate":
        reply = {
            "case":"moderate",
            "message":"Your responses suggest moderate symptoms. We recommend booking a confidential session.",
            "booking":"https://yourbookinglink.com",
            "resources":[
                {"type":"video","title":"Coping strategies","url":"https://www.youtube.com/watch?v=hnpQrMqDoqE"}
            ]
        }
    else:
        reply = {
            "case":"severe",
            "message":"Severe distress detected. Please contact emergency services or the helpline.",
            "helpline":"9152987821",
            "booking":"https://yourbookinglink.com"
        }

    return jsonify(reply)

# API to fetch last N chat messages for UI polling
@app.route("/api/messages", methods=["GET"])
@login_required
def api_messages():
    last = int(request.args.get("last", 0))
    q = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.created_at.asc()).all()
    out = [{"id":m.id, "sender":m.sender, "text":m.text, "time":m.created_at.isoformat()} for m in q]
    return jsonify({"messages": out})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
