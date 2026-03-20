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
    prompt = f"Create ONE multiple choice question about {topic}. Format: QUESTION: [text] A) [opt] B) [opt] C) [opt] D) [opt] ANSWER: [Letter]"
    try:
        response = llm.invoke(prompt).content
        lines = [l.strip() for l in response.split('\n') if l.strip()]
        q, opts, ans = "", [], ""
        for line in lines:
            if "QUESTION:" in line: q = line.replace("QUESTION:", "").strip()
            elif any(line.startswith(x) for x in ["A)", "B)", "C)", "D)"]): opts.append(line)
            elif "ANSWER:" in line: ans = line.replace("ANSWER:", "").strip().upper()
        return q, opts, ans
    except:
        return None, None, None

# =========================
# 3. SESSION INIT
# =========================
def init_session():
    if "logged_in" not in st.session_state:
        st.session_state.update({
            "logged_in": False, "users": {"admin": "1234"}, 
            "current_user": None, "page": "login", "mode": "Tutor", 
            "messages": [], "progress": {}, "quiz": None, "quiz_answer": None
        })

# =========================
# 4. PAGES
# =========================
def login_page():
    st.title("🎓 Concept Master Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u in st.session_state.users and st.session_state.users[u] == p:
            st.session_state.logged_in = True
            st.session_state.current_user = u
            # Initialize progress for user if it doesn't exist
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
            st.session_state.progress[u] = {"correct": 0} # Pre-init progress
            st.success("Account created! Go to Login.")
            st.session_state.page = "login"
            st.rerun()

def tutor_page():
    llm = load_llm()
    user = st.session_state.current_user
    
    # Safety Check for the KeyError fix
    if user not in st.session_state.progress:
        st.session_state.progress[user] = {"correct": 0}

    st.title("🎓 CONCEPT MASTER AI")

    with st.sidebar:
        st.write(f"Logged in as: **{user}**")
        st.session_state.mode = st.radio("Mode", ["Tutor", "Quiz"])
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    if st.session_state.mode == "Tutor":
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

        user_input = st.chat_input("Ask a question or say hello...")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"): st.markdown(user_input)
            
            with st.chat_message("assistant"):
                response = llm.invoke(user_input).content
                
                # --- SMART VIDEO FILTER ---
                keywords = ["how", "what", "why", "explain", "define", "concept", "mean"]
                if any(w in user_input.lower() for w in keywords):
                    q_encoded = urllib.parse.quote(user_input)
                    yt = f"\n\n🎬 **Suggested Video:** [YouTube Link](https://www.youtube.com/results?search_query={q_encoded})"
                    full_resp = response + yt
                else:
                    full_resp = response
                
                st.markdown(full_resp)
                st.session_state.messages.append({"role": "assistant", "content": full_resp})

    elif st.session_state.mode == "Quiz":
        st.header("📝 Quiz Mode")
        topic = st.text_input("Quiz Topic?")
        if st.button("Generate"):
            q, opts, ans = generate_quiz(topic)
            st.session_state.quiz = (q, opts)
            st.session_state.quiz_answer = ans
        
        if st.session_state.quiz:
            q, opts = st.session_state.quiz
            st.subheader(q)
            choice = st.radio("Select one:", opts)
            if st.button("Submit"):
                if choice.startswith(st.session_state.quiz_answer):
                    st.success("Correct!")
                    st.session_state.progress[user]["correct"] += 1
                else:
                    st.error(f"Wrong. It was {st.session_state.quiz_answer}")
                st.session_state.quiz = None

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