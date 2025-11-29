import streamlit as st
import json, os, hashlib

# ---------------- Page Config ----------------
st.set_page_config(page_title="Mental Health Chatbot", page_icon="💬", layout="wide")
# Force Streamlit to use light mode and make all text black
st.markdown("""
<style>
/* Force light mode */
:root {
    color-scheme: light !important;
}

/* Force all text to black */
html, body, [class*="st-"], div, span, p, h1, h2, h3, h4, h5, h6, label {
    color: black !important;
}

/* Optional: light background for everything */
.stApp {
    background-color: #FFFFFF !important;
}
section[data-testid="stSidebar"] {
    background-color: #E6F9F2 !important;
}

/* Ensure chat input and sidebar buttons are readable */
textarea, input, button {
    color: black !important;
    background-color: white !important;
}
</style>
""", unsafe_allow_html=True)


# ---------------- Helper Functions ----------------
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    else:
        return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ---------------- Auth State ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

users = load_users()

# ---------------- Login / Signup ----------------
def login_screen():
    st.title("🔐 Welcome to the Mental Health Chatbot")
    st.markdown("Please log in or create an account to continue.")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    # ---- Login Tab ----
    with tab1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username in users and users[username] == hash_password(password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")

    # ---- Signup Tab ----
    with tab2:
        new_user = st.text_input("Create Username")
        new_pass = st.text_input("Create Password", type="password")
        if st.button("Sign Up"):
            if new_user in users:
                st.warning("⚠️ Username already exists.")
            elif len(new_user) < 3 or len(new_pass) < 3:
                st.warning("⚠️ Username and password must be at least 3 characters.")
            else:
                users[new_user] = hash_password(new_pass)
                save_users(users)
                st.success("🎉 Account created! You can log in now.")

# ---------------- Show Chatbot if Logged In ----------------
if not st.session_state.logged_in:
    login_screen()
    st.stop()

# ---------------- Custom CSS ----------------

st.markdown("""
    <style>
        /* Background */
        .stApp {
            background-color: #FFFFFF;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #E6F9F2 !important;
        }

        /* FAQ Buttons */
        div[data-testid="stSidebar"] button {
            background-color: #A8E6CF !important;
            color: black !important;
            border-radius: 10px !important;
            border: none !important;
            margin: 4px 0px !important;
        }
        div[data-testid="stSidebar"] button:hover {
            background-color: #7BDCB5 !important;
            color: black !important;
        }

        /* Chat bubbles container */
        .chat-container {
            padding: 10px;
        }

        /* User messages (mint green, right aligned) */
        .user-msg {
            text-align: right;
            background: #7BDCB5;
            color: black;
            padding: 10px 15px;
            border-radius: 18px 18px 0px 18px;
            margin: 8px 0;
            max-width: 70%;
            float: right;
            clear: both;
        }

        /* Bot messages (white, left aligned, light border) */
        .bot-msg {
            text-align: left;
            background: #E6F9F2;
            color: black;
            border: 1px solid #A8E6CF;
            padding: 10px 15px;
            border-radius: 18px 18px 18px 0px;
            margin: 8px 0;
            max-width: 70%;
            float: left;
            clear: both;
        }

                /* Chat input */
        div[data-baseweb="input"] > div {
            border: 2px solid #A8E6CF !important;
            border-radius: 12px !important;
        }

        /* Buttons */
        button {
            background-color: #A8E6CF !important;
            color: black !important;
            border-radius: 8px !important;
            border: none !important;
        }
        button:hover {
            background-color: #7BDCB5 !important;
            color: black !important;
        }
    </style>
""", unsafe_allow_html=True)

# ---------------- Sidebar ----------------
st.sidebar.title(f"👋 Welcome, {st.session_state.username}")
if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

st.sidebar.title("📌 Frequently Asked Questions")
faqs = {
    "🌿 How to reduce anxiety?": "🧘 Deep breathing, exercise, journaling, and good sleep.",
    "📖 How to manage exam stress?": "Plan your study, take breaks, eat well, and rest properly.",
    "😔 What are signs of depression?": "Persistent sadness, loss of interest, fatigue.",
    "🌙 How to improve sleep?": "Routine, no caffeine, relax before bed.",
    "🔒 Confidential booking for counseling": "Book a confidential session [here](https://example.com)"
}
for q in faqs:
    if st.sidebar.button(q):
        st.session_state.messages.append(("user", q))
        st.session_state.messages.append(("bot", faqs[q]))

# ---------------- Chat Session ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "screening_active" not in st.session_state:
    st.session_state.screening_active = False
if "screening_step" not in st.session_state:
    st.session_state.screening_step = 0
if "screening_score" not in st.session_state:
    st.session_state.screening_score = 0
if "show_resources" not in st.session_state:
    st.session_state.show_resources = False
if "show_booking" not in st.session_state:
    st.session_state.show_booking = False

# ---------------- Chat Interface ----------------
st.title("💬 Hi, How May I Help You?")
chat_container = st.container()

with chat_container:
    for role, msg in st.session_state.messages:
        if role == "user":
            st.markdown(f"<div class='user-msg'>{msg}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='bot-msg'>{msg}</div>", unsafe_allow_html=True)

# ---------------- Screening Logic ----------------
questions = [
    "Over the last 2 weeks, how often have you felt little interest or pleasure in doing things?",
    "Over the last 2 weeks, how often have you felt down, depressed, or hopeless?",
    "Over the last 2 weeks, how often have you had trouble sleeping or concentrating?",
]
options = {"Not at all": 0, "Several days": 1, "More than half the days": 2, "Nearly every day": 3}

if st.session_state.screening_active:
    st.subheader("📝 Quick Screening Test")
    step = st.session_state.screening_step
    if step < len(questions):
        choice = st.radio(questions[step], list(options.keys()), key=f"q{step}")
        if st.button("Next"):
            st.session_state.screening_score += options[choice]
            st.session_state.screening_step += 1
            st.rerun()
    else:
        score = st.session_state.screening_score
        if score <= 3:
            st.success("✅ Mild risk detected. Here are some helpful resources:")
            st.session_state.show_resources = True
        else:
            st.error("⚠️ High risk detected. Please consider confidential help:")
            st.session_state.show_booking = True
        st.session_state.screening_active = False

# ---------------- Chat Input ----------------
user_input = st.chat_input("Type your message here...")
if user_input:
    st.session_state.messages.append(("user", user_input))
    if "yes" in user_input.lower():
        st.session_state.messages.append(("bot", "📝 Okay! Let's start a quick screening test."))
        st.session_state.screening_active = True
        st.session_state.screening_step = 0
        st.session_state.screening_score = 0
    elif "not live" in user_input.lower() or "suicide" in user_input.lower():
        st.session_state.messages.append(("bot", "🚨 If you are feeling unsafe, please call immediately: ☎ 1800-599-0019"))
        st.session_state.messages.append(("bot", "🔒 [Confidential booking for counseling](https://example.com)"))
    else:
        st.session_state.messages.append(("bot", "🤖 I'm here to support you. Would you like to take a screening test? (yes/no)"))
    st.rerun()

# ---------------- Resources ----------------
if st.session_state.show_resources:
    st.subheader("🎧 Resource Hub")
    st.markdown("""
    <div style="display:flex; justify-content:center; gap:30px;">
        <div>
            <iframe width="360" height="202" src="https://www.youtube.com/embed/inpok4MKVLM" frameborder="0" allowfullscreen></iframe>
            <div style="text-align:center; font-size:15px;">Meditation</div>
        </div>
        <div>
            <iframe width="360" height="202" src="https://www.youtube.com/embed/ZToicYcHIOU" frameborder="0" allowfullscreen></iframe>
            <div style="text-align:center; font-size:15px;">Relaxation</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

if st.session_state.show_booking:
    st.subheader("🔒 Confidential Help")
    st.markdown("📞 Call: **1800-599-0019**")
    st.markdown("➡️ [Book a confidential counseling session](https://example.com)")
