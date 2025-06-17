import streamlit as st
import uuid
from src import bot, run_ingestion

st.set_page_config(
    page_title="ObsiQuery",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        html, body, [class*="stApp"] {
            background-color: #0d1117;
            color: #c9d1d9;
            font-family: 'Segoe UI', sans-serif;
        }
        /* Chat message styling */
        [data-testid="stChatMessage"] {
            background-color: #161b22;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 10px;
            border: 1px solid #30363d;
            transition: background 0.3s;
        }
        [data-testid="stChatMessage"]:hover {
            background-color: #1c2128;
        }
        [data-testid="stChatMessage"]:has(div[data-testid="chat-avatar-user"]) {
            background-color: #0c0f13;
        }
        .stExpander, .stExpander header {
            color: #8b949e !important;
            background-color: #0d1117 !important;
            border: 1px solid #30363d !important;
        }
        .stChatInputContainer {
            padding-top: 2rem;
        }
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #161b22;
            color: #c9d1d9;
        }
        .block-container {
            padding-top: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🧠 ObsiQuery")
    st.markdown("""
    **Second brain, first-class answers.**  
    Explore your Obsidian vault with the power of RAG-based AI.

    - Built for context-rich queries  
    - Uses local notes only  
    - No cloud dependencies

    🛠️ Project by [@shridhar600](https://www.linkedin.com/in/shridhar600)
    """)

# --- Main Header ---
st.title("🧠 ObsiQuery")
st.markdown("Your personal AI over your Obsidian vault. Ask anything.")

# --- Session Initialization ---
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "How can I help you query your second brain?",
            "artifact": None
        }
    ]

# Load the bot instance
bot = bot  # Already imported

# Initialize ingestion state
if "is_ingesting" not in st.session_state:
    st.session_state.is_ingesting = False

def run_ingestion_pipeline():
    """
    Your ingestion logic here.
    This should be the method that loads new/updated notes into the vector DB.
    """
    # Simulate ingestion with time.sleep or call your real function here
    import time
    time.sleep(3)  # Replace with: your_ingestion_function()
    return "✅ Ingestion completed successfully!"

# Ingestion Section
st.markdown("### 📥 Ingestion Controls")

if st.session_state.is_ingesting:
    st.warning("Ingestion is currently running. Please wait...")
    st.button("Run Ingestion Pipeline", disabled=True)
else:
    if st.button("Run Ingestion Pipeline"):
        st.session_state.is_ingesting = True
        with st.spinner("🔄 Running ingestion..."):
            try:
                result = run_ingestion()
                st.success(result)
            except Exception as e:
                st.error(f"❌ Ingestion failed: {str(e)}")
            finally:
                st.session_state.is_ingesting = False

# --- Display Chat History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("artifact"):
            with st.expander("📁 Retrieved Sources"):
                for source in message["artifact"]:
                    st.info(f"📄 {source}", icon="📄")

# --- User Input & Bot Response ---
if user_input := st.chat_input("Ask your second brain..."):
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "artifact": None
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("🧠 Thinking..."):
            response = bot.invoke_graph(user_input, st.session_state.thread_id)
            reply = response.get("reply", "Sorry, I couldn't generate a response.")
            st.markdown(reply)

            if response.get("artifact"):
                with st.expander("📁 Retrieved Sources"):
                    for source in response["artifact"]:
                        st.info(f"📄 {source}", icon="📄")

            st.session_state.messages.append({
                "role": "assistant",
                "content": reply,
                "artifact": response.get("artifact", None)
            })
