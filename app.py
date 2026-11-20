import json
import streamlit as st
from google import genai
from google.genai import types

# 1. Setup Gemini Client (replace with your key from Google AI Studio)
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

# 2. Load your existing campus knowledge base
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

RULE 2 (Academic Doubts): If the user asks an academic question (like C programming, Python, Physics, Math, or engineering concepts), explain it clearly and step-by-step like a helpful senior or tutor.
"""

# 3. Build the Website UI
st.set_page_config(page_title="Campus Helpdesk & Tutor", page_icon="🎓")
st.title("🎓 Campus Helpdesk & Study Agent")
st.caption("Ask about campus labs, attendance, exam dates — or any academic doubt.")

# Keep chat history across reruns
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input box pinned to the bottom
if prompt := st.chat_input("Ask a campus or academic question..."):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

# Generate AI Agent response (with auto-fallback if a model is busy)
    MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.1-flash-lite"]

    with st.chat_message("assistant"):
        placeholder = st.empty()
        reply = ""
        last_error = None

        for model_name in MODELS:
            try:
                response = client.models.generate_content_stream(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                    ),
                )

                for chunk in response:
                    if chunk.text:
                        reply += chunk.text
                        placeholder.markdown(reply + "▌")

                placeholder.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                last_error = None
                break  # Worked! Stop checking backup models
            except Exception as e:
                last_error = e
                reply = ""
                placeholder.empty()
                continue  # Try the next model

        if last_error:
            st.error(f"All models are busy right now. Try again in a few seconds.\n\nDetails: {last_error}")
