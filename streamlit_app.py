import os
import re
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
KNOWLEDGE_DIR = ROOT / "knowledge"
DATA_DIR = ROOT / "data"
TICKETS_FILE = DATA_DIR / "tickets.json"
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}

KNOWLEDGE_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
load_dotenv(ROOT / ".env")

st.set_page_config(page_title="KnowFlow AI", page_icon="💬", layout="wide")

def get_client():
    key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "")).strip()
    return OpenAI(api_key=key) if key else None

def get_model():
    return st.secrets.get("OPENAI_MODEL", os.getenv("OPENAI_MODEL", "")).strip()

def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8", errors="ignore")

def tokenize(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))

def chunks(text, size=900):
    text = re.sub(r"\s+", " ", text).strip()
    return [text[i:i+size] for i in range(0, len(text), size)]

def retrieve(question, limit=4):
    qtokens = tokenize(question)
    results = []
    for path in KNOWLEDGE_DIR.iterdir():
        if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        try:
            content = extract_text(path)
        except Exception:
            continue
        for i, chunk in enumerate(chunks(content), 1):
            tokens = tokenize(chunk)
            score = len(qtokens & tokens) / max(len(qtokens), 1)
            if score > 0.05:
                results.append({"source": path.name, "chunk": i, "text": chunk, "score": score})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]

def load_tickets():
    try:
        return json.loads(TICKETS_FILE.read_text(encoding="utf-8")) if TICKETS_FILE.exists() else []
    except Exception:
        return []

def save_ticket(question, answer, email):
    tickets = load_tickets()
    ticket = {
        "id": "NF-" + uuid.uuid4().hex[:8].upper(),
        "question": question,
        "answer": answer,
        "email": email or None,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    tickets.insert(0, ticket)
    TICKETS_FILE.write_text(json.dumps(tickets, indent=2), encoding="utf-8")
    return ticket

def answer_question(question):
    client = get_client()
    model = get_model()
    if client is None:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it in Streamlit Secrets.")
    if not model:
        raise RuntimeError("OPENAI_MODEL is missing. Add a model available to your API account in Streamlit Secrets.")
    hits = retrieve(question)
    if not hits:
        return ("I couldn't find a relevant answer in the available support documents. "
                "Please create a support ticket so a human agent can help."), []
    context = "\n\n".join(
        f"[Source: {h['source']}, section {h['chunk']}]\n{h['text']}" for h in hits
    )
    instructions = (
        "You are KnowFlow, a careful customer-support assistant. Use only the supplied "
        "support-document excerpts to answer questions about company policies and products. "
        "Never invent policies, prices, order status, tracking links, approvals, or deadlines. "
        "If the excerpts do not clearly answer, say you cannot verify it and recommend a human "
        "support ticket. Be concise, friendly, and practical. Never ask for passwords, full card "
        "numbers, CVVs, or one-time passwords."
    )
    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=f"SUPPORT DOCUMENT EXCERPTS:\n{context}\n\nCUSTOMER QUESTION:\n{question}"
    )
    return (response.output_text or "I couldn't generate an answer. Please try again.").strip(), sorted({h["source"] for h in hits})

st.title("💬 KnowFlow AI")
st.caption("AI Customer Support Knowledge System")
st.info("Ask questions using the support documents. If the answer cannot be verified, create a support ticket.")

with st.sidebar:
    st.header("Knowledge base")
    files = sorted([p.name for p in KNOWLEDGE_DIR.iterdir() if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS])
    st.write(f"{len(files)} knowledge file(s) available")
    for name in files:
        st.caption("📄 " + name)
    uploaded = st.file_uploader("Add TXT, MD, or text-based PDF", type=["txt", "md", "pdf"])
    if uploaded and st.button("Upload document"):
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(uploaded.name).name)
        destination = KNOWLEDGE_DIR / safe_name
        destination.write_bytes(uploaded.getvalue())
        try:
            if not extract_text(destination).strip():
                destination.unlink(missing_ok=True)
                st.error("No selectable text found in this file.")
            else:
                st.success(f"Uploaded {safe_name}")
                st.rerun()
        except Exception:
            destination.unlink(missing_ok=True)
            st.error("Could not read this file. Try a text-based PDF, TXT, or MD.")

    st.divider()
    st.caption("Demo project. Do not upload confidential customer data.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            st.caption("Sources: " + ", ".join(msg["sources"]))

question = st.chat_input("Ask a question about products, returns, delivery, or policies...")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Searching support documents and preparing an answer..."):
            try:
                answer, sources = answer_question(question)
                st.markdown(answer)
                if sources:
                    st.caption("Sources: " + ", ".join(sources))
                st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
                st.session_state.last_question = question
                st.session_state.last_answer = answer
            except Exception as e:
                st.error(str(e))
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {e}"})

if st.session_state.get("last_question"):
    with st.expander("Create a support ticket"):
        email = st.text_input("Your email (optional)", key="ticket_email")
        if st.button("Create ticket"):
            ticket = save_ticket(st.session_state.last_question, st.session_state.get("last_answer", ""), email.strip())
            st.success(f"Ticket created: {ticket['id']}")

with st.expander("Demo tickets"):
    tickets = load_tickets()
    if tickets:
        for ticket in tickets[:20]:
            st.markdown(f"**{ticket['id']}** · {ticket['status']} · {ticket['created_at']}")
            st.write(ticket["question"])
            st.divider()
    else:
        st.caption("No tickets created yet.")
