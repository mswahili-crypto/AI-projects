import streamlit as st
import os
from dotenv import load_dotenv
import pyttsx3
import threading
import urllib.parse
import random

from langchain_groq import ChatGroq

# =========================
# ENV SETUP
# =========================
load_dotenv()
if not os.getenv("GROQ_API_KEY"):
    st.error("GROQ_API_KEY missing in .env")
    st.stop()

# =========================
# TTS
# =========================
@st.cache_resource
def init_tts():
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 150)
        return engine
    except:
        return None

def speak_text(text):
    engine = init_tts()
    if engine:
        threading.Thread(
            target=lambda: (engine.say(text), engine.runAndWait()),
            daemon=True
        ).start()

# =========================
# LLM
# =========================
@st.cache_resource
def load_llm():
    return ChatGroq(
        model_name="llama-3.1-8b-instant",
        groq_api_key=os.getenv("GROQ_API_KEY")
    )

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
        "progress": {},   # username → stats
        "quiz": None,
        "quiz_answer": None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# =========================
# LOGIN
# =========================
def login_page():
    st.title(" Login")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u in st.session_state.users and st.session_state.users[u] == p:
            st.session_state.logged_in = True
            st.session_state.current_user = u
            if u not in st.session_state.progress:
                st.session_state.progress[u] = {
                    "questions": 0,
                    "quizzes": 0,
                    "correct": 0
                }
            st.rerun()
        else:
            st.error("Invalid login")

    if st.button("Register"):
        st.session_state.page = "register"
        st.rerun()

# =========================
# REGISTER
# =========================
def register_page():
    st.title(" Register")

    u = st.text_input("Choose Username")
    p = st.text_input("Choose Password", type="password")

    if st.button("Create Account"):
        if u in st.session_state.users:
            st.error("User exists")
        else:
            st.session_state.users[u] = p
            st.success("Registered successfully")
            st.session_state.page = "login"
            st.rerun()

# =========================
# QUIZ GENERATOR
# =========================
def generate_quiz(topic):
    llm = load_llm()

    prompt = f"""
Create ONE multiple choice quiz question for a university student.

Topic: {topic}

Rules:
- Provide exactly 4 options (A, B, C, D)
- Clearly indicate the correct answer

Format:
QUESTION: ...
A) ...
B) ...
C) ...
D) ...
ANSWER: A/B/C/D
"""

    response = llm.invoke(prompt).content.strip()
    lines = [l.strip() for l in response.splitlines() if l.strip()]

    question = ""
    options = []
    answer = ""

    for line in lines:
        if line.upper().startswith("QUESTION"):
            question = line.replace("QUESTION:", "").strip()
        elif line.startswith(("A)", "B)", "C)", "D)")):
            options.append(line)
        elif line.upper().startswith("ANSWER"):
            parts = line.split(":")
            if len(parts) > 1:
                answer = parts[1].strip().upper()

    # Safety fallback
    if not question or len(options) != 4 or answer not in ["A", "B", "C", "D"]:
        question = f"What is a key concept of {topic}?"
        options = [
            "A) Definition",
            "B) Example",
            "C) Application",
            "D) All of the above"
        ]
        answer = "D"

    return question, options, answer


# =========================
# TUTOR PAGE
# =========================
def tutor_page():
    llm = load_llm()
    user = st.session_state.current_user
    stats = st.session_state.progress[user]

    # THEME
    bg = "#ffffff" if st.session_state.theme == "Light" else "#0e1117"
    text = "#000000" if st.session_state.theme == "Light" else "#ffffff"

    st.markdown(
        f"""
        <style>
        body {{
            background-color: {bg};
            color: {text};
            font-size: {st.session_state.font_size}px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("CONCEPT MASTER")

    # SIDEBAR
    with st.sidebar:
        st.header("⚙️ Settings")

        st.session_state.mode = st.radio(
            "Mode", ["Tutor", "Quiz"]
        )

        st.session_state.font_size = st.slider(
            "Font Size", 14, 28, st.session_state.font_size
        )

        st.session_state.theme = st.radio(
            "Theme", ["Light", "Dark"],
            index=0 if st.session_state.theme == "Light" else 1
        )

        st.session_state.tts = st.checkbox(
            "Text-to-Speech", value=st.session_state.tts
        )

        st.markdown("---")
        st.subheader(" Progress")
        st.write(f"Questions Asked: {stats['questions']}")
        st.write(f"Quizzes Taken: {stats['quizzes']}")
        st.write(f"Correct Answers: {stats['correct']}")

        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.messages = []
            st.rerun()

    # =====================
    # TUTOR MODE
    # =====================
    if st.session_state.mode == "Tutor":
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input("Ask a question...")

        if user_input:
            stats["questions"] += 1
            st.session_state.messages.append(
                {"role": "user", "content": user_input}
            )

            query = urllib.parse.quote_plus(user_input + " explained")
            video = f"https://www.youtube.com/results?search_query={query}"

            prompt = f"""
Explain clearly for a university student.
Use examples.

Question:
{user_input}
"""

            with st.chat_message("assistant"):
                response = llm.invoke(prompt).content
                response += f"\n\n🎥 Related Video:\n{video}"
                response += "\n\n👉 Want a quiz on this topic?"

                st.markdown(response)

                if st.session_state.tts:
                    speak_text(response)

                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )

    # =====================
    # QUIZ MODE
    # =====================
    else:
        st.header("📝 Quiz Mode")

        topic = st.text_input("Enter quiz topic")

        if st.button("Generate Quiz") and topic:
            q, opts, ans = generate_quiz(topic)
            st.session_state.quiz = (q, opts)
            st.session_state.quiz_answer = ans
            st.session_state.progress[user]["quizzes"] += 1

        if st.session_state.quiz:
            q, opts = st.session_state.quiz
            st.subheader(q)

            choice = st.radio("Choose answer", opts)

            if st.button("Submit Answer"):
                correct = st.session_state.quiz_answer
                if choice.startswith(correct):
                    st.success("✅ Correct!")
                    st.session_state.progress[user]["correct"] += 1
                else:
                    st.error(f"❌ Wrong. Correct answer is {correct}")

                st.session_state.quiz = None

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
