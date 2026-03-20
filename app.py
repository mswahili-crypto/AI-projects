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
        temperature=0.7 # Makes it more natural/creative
    )

# =========================
# 2. QUIZ ENGINE
# =========================
def generate_quiz(topic):
    llm = load_llm()
    prompt = f"""
    Create ONE multiple choice question about {topic} for a student.
    Format EXACTLY like this:
    QUESTION: [The question]
    A) [Option]
    B) [Option]
    C) [Option]
    D) [Option]
    ANSWER: [Letter only]
    """
    try:
        response = llm.invoke(prompt).content
        lines = [l.strip() for l in response.split('\n') if l.strip()]
        q, opts, ans = "", [], ""
        for line in lines:
            if "QUESTION:" in line: q = line.replace("QUESTION:", "").strip()
            elif any(line.startswith(x) for x in ["A)", "B)", "C)", "D)"]): opts.append(line)
            elif "ANSWER:" in line: ans = line.replace("ANSWER:", "").strip().upper()
        
        if q and len(opts) == 4:
            return q, opts, ans
        return "Couldn't generate a clean quiz. Try again?", ["A) No", "B) Yes", "C) Maybe", "D) None"], "A"
    except:
        return "AI Error.", ["A","B","C","D"], "A"

# =========================
# 3. SESSION & LOGIC
# =========================
def init_session():
    if "logged_in" not in st.session_state:
        st.session_state.update({
            "logged_in": False, "users": {"admin": "1234"}, 
            "current_user": None, "page": "login", "mode": "Tutor", 
            "messages": [], "progress": {}, "quiz": None, "quiz_answer": None
        })

def login_page():
    st.title("🔐 Concept Master Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if u in st.session_state.users and st.session_state.users[u] == p:
            st.session_state.logged_in = True
            st.session_state.current_user = u
            st.rerun()
        else:
            st.error("Invalid credentials")
    if st.button("Create Account"):
        st.session_state.page = "register"
        st.rerun()

def register_page():
    st.title("📝 Create Account")
    u = st.text_input("New Username")
    p = st.text_input("New Password", type="password")
    if st.button("Register"):
        st.session_state.users[u] = p
        st.success("Registered! Go login.")
        st.session_state.page = "login"
        st.rerun()

# =========================
# 4. THE TUTOR PAGE
# =========================
def tutor_page():
    llm = load_llm()
    user = st.session_state.current_user
    if user not in st.session_state.progress:
        st.session_state.progress[user] = {"correct": 0}

    st.title("🎓 CONCEPT MASTER AI")

    with st.sidebar:
        st.header(f"Welcome, {user}")
        st.session_state.mode = st.radio("Mode", ["Tutor", "Quiz"])
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.rerun()
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    if st.session_state.mode == "Tutor":
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input("Explain something to me...")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"): st.markdown(user_input)
            
            # Natural Memory context
            history = "\n".join([f"{m['role']}: {m['content'][:100]}" for m in st.session_state.messages[-5:]])
            
            with st.chat_message("assistant"):
                prompt = [
                    ("system", f"You are a fluent, human-like University Tutor. Be engaging. History: {history}"),
                    ("user", user_input)
                ]
                response = llm.invoke(prompt).content
                
                # YouTube integration
                q_encoded = urllib.parse.quote(user_input)
                yt_link = f"\n\n🎬 **Watch a breakdown:** [YouTube Link](https://www.youtube.com/results?search_query={q_encoded})"
                
                full_resp = response + yt_link
                st.markdown(full_resp)
                st.session_state.messages.append({"role": "assistant", "content": full_resp})

    elif st.session_state.mode == "Quiz":
        st.header("📝 Quiz Time")
        topic = st.text_input("Topic for the quiz?")
        if st.button("Get Question") and topic:
            with st.spinner("Creating..."):
                q, opts, ans = generate_quiz(topic)
                st.session_state.quiz = (q, opts)
                st.session_state.quiz_answer = ans
        
        if st.session_state.quiz:
            q, opts = st.session_state.quiz
            st.subheader(q)
            choice = st.radio("Answer:", opts)
            if st.button("Submit"):
                if choice.startswith(st.session_state.quiz_answer):
                    st.success("Correct! 🌟")
                    st.session_state.progress[user]["correct"] += 1
                else:
                    st.error(f"Nope! It was {st.session_state.quiz_answer}")
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