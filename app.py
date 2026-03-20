import streamlit as st
import os
import threading
import urllib.parse
from langchain_groq import ChatGroq

# =========================
# LLM SETUP (Using Secrets)
# =========================
# This pulls the key from the Streamlit "Advanced Settings" box
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    st.error("GROQ_API_KEY missing! Add it to Streamlit Secrets.")
    st.stop()

@st.cache_resource
def load_llm():
    return ChatGroq(
        model_name="llama-3.1-8b-instant",
        groq_api_key=GROQ_API_KEY
    )

# =========================
# TTS (Text-to-Speech)
# =========================
# NOTE: pyttsx3 may not produce sound on Streamlit Cloud Linux servers
def speak_text(text):
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 150)
        threading.Thread(
            target=lambda: (engine.say(text), engine.runAndWait()),
            daemon=True
        ).start()
    except:
        pass # Fails silently if sound drivers are missing on the server

# =========================
# SESSION INIT
# =========================
def init_session():
    defaults = {
        "logged_in": False,
        "users": {},
        "current_user": None,
        "page": "login",
        "mode": "Tutor",
        "messages": [],
        "tts": True,
        "font_size": 18,
        "theme": "Light",
        "progress": {},
        "quiz": None,
        "quiz_answer": None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# =========================
# LOGIN & REGISTER
# =========================
def login_page():
    st.title("Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u in st.session_state.users and st.session_state.users[u] == p:
            st.session_state.logged_in = True
            st.session_state.current_user = u
            if u not in st.session_state.progress:
                st.session_state.progress[u] = {"questions": 0, "quizzes": 0, "correct": 0}
            st.rerun()
        else:
            st.error("Invalid login")
    if st.button("Go to Register"):
        st.session_state.page = "register"
        st.rerun()

def register_page():
    st.title("Register")
    u = st.text_input("Choose Username")
    p = st.text_input("Choose Password", type="password")
    if st.button("Create Account"):
        if u in st.session_state.users:
            st.error("User exists")
        else:
            st.session_state.users[u] = p
            st.success("Registered! Now Login.")
            st.session_state.page = "login"
            st.rerun()

# =========================
# QUIZ GENERATOR
# =========================
def generate_quiz(topic):
    llm = load_llm()
    prompt = f"Create ONE multiple choice question for {topic}. Provide 4 options A, B, C, D and the ANSWER."
    response = llm.invoke(prompt).content.strip()
    # Simplified logic for example; normally you'd parse more strictly
    return response, ["A", "B", "C", "D"], "A"

# =========================
# TUTOR PAGE
# =========================
def tutor_page():
    llm = load_llm()
    user = st.session_state.current_user
    stats = st.session_state.progress[user]

    st.title("CONCEPT MASTER")

    with st.sidebar:
        st.header("⚙️ Settings")
        st.session_state.mode = st.radio("Mode", ["Tutor", "Quiz"])
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    if st.session_state.mode == "Tutor":
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input("Ask a question...")
        if user_input:
            stats["questions"] += 1
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("assistant"):
                response = llm.invoke(user_input).content
                st.markdown(response)
                if st.session_state.tts:
                    speak_text(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

# =========================
# MAIN
# =========================
def main():
    init_session()
    if not st.session_state.logged_in:
        if st.session_state.page == "login":
            login_page()
        else:
            register_page()
    else:
        tutor_page()

if __name__ == "__main__":
    main()