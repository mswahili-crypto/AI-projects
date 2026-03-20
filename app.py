import streamlit as st
import os
import urllib.parse
from langchain_groq import ChatGroq

# =========================
# 1. LLM SETUP
# =========================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    st.error("Missing GROQ_API_KEY in Streamlit Secrets!")
    st.stop()

@st.cache_resource
def load_llm():
    return ChatGroq(
        model_name="llama-3.1-8b-instant",
        groq_api_key=GROQ_API_KEY,
        temperature=0.7
    )

# =========================
# 2. QUIZ ENGINE
# =========================
def generate_quiz(topic):
    llm = load_llm()
    prompt = f"""
    Create ONE challenging multiple choice question about {topic}.
    Format:
    QUESTION: [text]
    A) [option]
    B) [option]
    C) [option]
    D) [option]
    ANSWER: [Just the Letter]
    """
    try:
        response = llm.invoke(prompt).content
        lines = [l.strip() for l in response.split('\n') if l.strip()]
        q, opts, ans = "", [], ""
        for line in lines:
            if "QUESTION:" in line: q = line.replace("QUESTION:", "").strip()
            elif any(line.startswith(x) for x in ["A)", "B)", "C)", "D)"]): opts.append(line)
            elif "ANSWER:" in line: 
                ans_line = line.replace("ANSWER:", "").strip().upper()
                ans = ans_line[0] if ans_line else ""
        return q, opts, ans
    except:
        return None, None, None

# =========================
# 3. SESSION & PAGES
# =========================
def init_session():
    if "logged_in" not in st.session_state:
        st.session_state.update({
            "logged_in": False, "users": {"admin": "1234"}, 
            "current_user": None, "page": "login", "mode": "Tutor", 
            "messages": [], "progress": {}, "quiz": None, "quiz_answer": None
        })

def login_page():
    st.title("🎓 Concept Master Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u in st.session_state.users and st.session_state.users[u] == p:
            st.session_state.logged_in = True
            st.session_state.current_user = u
            if u not in st.session_state.progress:
                st.session_state.progress[u] = {"correct": 0}
            st.rerun()
        else:
            st.error("Invalid credentials")
    if st.button("Go to Register"):
        st.session_state.page = "register"
        st.rerun()

def register_page():
    st.title("📝 Register")
    u = st.text_input("Choose Username")
    p = st.text_input("Choose Password", type="password")
    if st.button("Create Account"):
        if u:
            st.session_state.users[u] = p
            st.session_state.progress[u] = {"correct": 0}
            st.success("Account created! Go to Login.")
            st.session_state.page = "login"
            st.rerun()

# =========================
# 4. THE TUTOR & QUIZ PAGE
# =========================
def tutor_page():
    llm = load_llm()
    user = st.session_state.current_user
    
    if user not in st.session_state.progress:
        st.session_state.progress[user] = {"correct": 0}

    st.title("🎓 CONCEPT MASTER AI")

    with st.sidebar:
        st.write(f"User: **{user}** | Score: **{st.session_state.progress[user]['correct']}**")
        st.session_state.mode = st.radio("Switch Mode", ["Tutor", "Quiz"])
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.rerun()
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    # --- TUTOR MODE ---
    if st.session_state.mode == "Tutor":
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

        user_input = st.chat_input("Ask a question...")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"): st.markdown(user_input)
            
            with st.chat_message("assistant"):
                response = llm.invoke(user_input).content
                keywords = ["how", "what", "why", "explain", "define", "concept"]
                if any(w in user_input.lower() for w in keywords):
                    q_enc = urllib.parse.quote(user_input)
                    yt = f"\n\n🎬 **Video:** [Watch here](https://www.youtube.com/results?search_query={q_enc})"
                    full_resp = response + yt
                else:
                    full_resp = response
                st.markdown(full_resp)
                st.session_state.messages.append({"role": "assistant", "content": full_resp})

    # --- QUIZ MODE ---
    elif st.session_state.mode == "Quiz":
        st.header("📝 Challenge Mode")
        topic = st.text_input("Test me on...")
        
        if st.button("Generate Question") and topic:
            with st.spinner("Thinking..."):
                q, opts, ans = generate_quiz(topic)
                if q:
                    st.session_state.quiz = (q, opts)
                    st.session_state.quiz_answer = ans
                else:
                    st.error("Try again!")

        if st.session_state.quiz:
            q, opts = st.session_state.quiz
            st.subheader(q)
            choice = st.radio("Choose:", opts, key=f"q_{q[:15]}")
            if st.button("Submit Answer"):
                if choice.startswith(st.session_state.quiz_answer):
                    st.success("✅ Correct!")
                    st.session_state.progress[user]["correct"] += 1
                else:
                    st.error(f"❌ Wrong. It was {st.session_state.quiz_answer}")
                st.session_state.quiz = None # Ready for next one

# =========================
# 5. MAIN
# =========================
def main():
    init_session()
    if not st.session_state.logged_in:
        if st.session_state.page == "login": login_page()
        else: register_page()
    else:
        tutor_page()

if __name__ == "__main__":
    main()