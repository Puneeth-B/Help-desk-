import json
import uuid
from datetime import datetime
import streamlit as st
from google import genai
from google.genai import types

# 1. Page Configuration (must be the first Streamlit command)
st.set_page_config(
    page_title="Campus Helpdesk & Study Agent",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="expanded",
)

# 2. Custom CSS for a modern AI chatbot look
st.markdown(
    """
    <style>
        /* Hide default Streamlit footer */
        footer {visibility: hidden;}

        /* Left-align sidebar chat history buttons like ChatGPT / Gemini */
        section[data-testid="stSidebar"] .stButton > button {
            justify-content: flex-start;
            text-align: left;
            border-radius: 10px;
            padding: 0.45rem 0.75rem;
            font-size: 0.9rem;
        }

        /* Clean centered welcome header */
        .welcome-box {
            text-align: center;
            padding: 2.5rem 1rem 1.5rem 1rem;
        }
        .welcome-box h1 {
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 0.4rem;
        }
        .welcome-box p {
            opacity: 0.75;
            font-size: 1rem;
        }

        /* Subtle pill badge in sidebar */
        .status-badge {
            font-size: 0.78rem;
            padding: 0.35rem 0.65rem;
            border-radius: 8px;
            border: 1px solid rgba(128, 128, 128, 0.25);
            opacity: 0.85;
            margin-bottom: 0.75rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# 3. Setup Gemini Client & Campus Knowledge Base
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

with open("campus_data.json", "r", encoding="utf-8") as f:
    campus_data = json.load(f)

SYSTEM_PROMPT = f"""
You are a friendly, helpful college senior acting as both a Campus Helpdesk and Academic Tutor for engineering students.

TONE & STYLE:
- Always speak naturally, warmly, and conversationally — never copy-paste raw JSON text like a robot.
- Keep campus answers short, clear, and easy to skim on a phone.

RULE 1 (Campus Info — Strict Facts, Natural Voice):
When a student asks about college rules, attendance, labs, exam dates, or faculty cabins, rely ONLY on the verified facts below, but rephrase them naturally in your own words:
{json.dumps(campus_data, indent=2)}
- Never invent or guess any room number, date, percentage, or rule that isn't listed above.
- Mention the source naturally at the end (e.g., "— per the Academic Handbook, p. 12").
- If a campus question isn't covered above, politely let them know you don't have verified info on it yet and suggest checking with the department office.

RULE 2 (Academic Doubts):
For academic questions (C programming, Python, Physics, Math, or engineering concepts), explain them clearly and step-by-step with simple examples.
"""

MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.1-flash-lite"]

# 4. Initialize Multi-Chat Session Storage
def create_new_chat() -> str:
    chat_id = str(uuid.uuid4())
    st.session_state.chats[chat_id] = {
        "title": "New Chat",
        "created_at": datetime.now().strftime("%I:%M %p"),
        "messages": [],
    }
    st.session_state.current_chat_id = chat_id
    return chat_id

if "chats" not in st.session_state:
    st.session_state.chats = {}
    create_new_chat()

current_id = st.session_state.current_chat_id
current_chat = st.session_state.chats[current_id]

def format_chat_log(chat: dict) -> str:
    lines = [
        f"Campus Helpdesk & Study Agent — Chat Log",
        f"Topic: {chat['title']}",
        f"Started: {chat['created_at']}",
        "=" * 45,
        "",
    ]
    for m in chat["messages"]:
        speaker = "You" if m["role"] == "user" else "Campus Agent"
        lines.append(f"[{speaker}]\n{m['content']}\n")
    return "\n".join(lines)

# 5. Sidebar: New Chat, Chat Logs & Export
with st.sidebar:
    st.markdown("### 🎓 Campus Agent")
    st.markdown(
        f'<div class="status-badge">🟢 {len(campus_data)} verified campus topics loaded</div>',
        unsafe_allow_html=True,
    )

    # Start a new conversation (only creates one if current chat isn't already blank)
    if st.button("＋ New Chat", use_container_width=True, type="primary"):
        if len(current_chat["messages"]) > 0:
            create_new_chat()
            st.rerun()

    st.divider()
    st.caption("CHAT LOGS")

    # Show chats newest-first
    for cid, chat in list(st.session_state.chats.items())[::-1]:
        is_active = cid == current_id
        col_title, col_del = st.columns([0.82, 0.18], gap="small")

        with col_title:
            label = f"💬 {chat['title']}"
            if st.button(
                label,
                key=f"select_{cid}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.current_chat_id = cid
                st.rerun()

        with col_del:
            if st.button("✕", key=f"delete_{cid}", help="Delete chat"):
                del st.session_state.chats[cid]
                if not st.session_state.chats:
                    create_new_chat()
                elif cid == current_id:
                    st.session_state.current_chat_id = list(st.session_state.chats.keys())[-1]
                st.rerun()

    st.divider()

    # Export current chat as a text file
    if current_chat["messages"]:
        st.download_button(
            label="📥 Download Chat Log (.txt)",
            data=format_chat_log(current_chat),
            file_name=f"campus_chat_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    if st.button("🗑️ Clear All Logs", use_container_width=True):
        st.session_state.chats = {}
        create_new_chat()
        st.rerun()

# 6. Capture Input (either typed or from clicking a starter chip)
user_input = st.chat_input("Ask about campus labs, attendance, exam dates, or any subject...")
prompt = st.session_state.pop("pending_prompt", None) or user_input

if prompt:
    # Auto-name the chat using the first user question
    if len(current_chat["messages"]) == 0:
        clean_title = prompt.strip().replace("\n", " ")
        current_chat["title"] = (clean_title[:26] + "...") if len(clean_title) > 26 else clean_title

    current_chat["messages"].append({"role": "user", "content": prompt})

# 7. Main Chat Area: Welcome Screen OR Conversation History
if len(current_chat["messages"]) == 0:
    st.markdown(
        """
        <div class="welcome-box">
            <h1>🎓 Campus Helpdesk & Tutor</h1>
            <p>Verified campus schedules & rules — plus step-by-step help for your subjects.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Starter suggestion cards (2x2 grid)
    starters = [
        ("📅 C Lab Schedule", "When and where is Batch A1 C Lab?"),
        ("📋 Attendance Rules", "What is the minimum attendance required for exams?"),
        ("🔬 Physics Lab", "Where is the Engineering Physics Lab and what are its timings?"),
        ("💻 C Programming Help", "Explain pointers in C with a simple beginner example."),
    ]

    col1, col2 = st.columns(2)
    for idx, (card_title, card_prompt) in enumerate(starters):
        target_col = col1 if idx % 2 == 0 else col2
        with target_col:
            if st.button(f"**{card_title}**\n\n{card_prompt}", key=f"starter_{idx}", use_container_width=True):
                st.session_state.pending_prompt = card_prompt
                st.rerun()
else:
    for msg in current_chat["messages"]:
        avatar = "🧑‍🎓" if msg["role"] == "user" else "🎓"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

# 8. Generate & Stream AI Agent Reply
if prompt:
    history = [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part.from_text(text=m["content"])],
        )
        for m in current_chat["messages"]
    ]

    with st.chat_message("assistant", avatar="🎓"):
        placeholder = st.empty()
        reply = ""
        last_error = None

        for model_name in MODELS:
            try:
                response = client.models.generate_content_stream(
                    model=model_name,
                    contents=history,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                    ),
                )

                for chunk in response:
                    if chunk.text:
                        reply += chunk.text
                        placeholder.markdown(reply + "▌")

                placeholder.markdown(reply)
                current_chat["messages"].append({"role": "assistant", "content": reply})
                last_error = None
                break
            except Exception as e:
                last_error = e
                reply = ""
                placeholder.empty()
                continue

        if last_error:
            st.error(f"All models are busy right now. Please try again in a few seconds.\n\nDetails: {last_error}")
        else:
            # Refresh once so the sidebar title and Download Log button update immediately
            st.rerun()
