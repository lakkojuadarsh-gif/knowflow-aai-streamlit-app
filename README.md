# KnowFlow AI — Customer Support Knowledge System

A hackathon MVP built with FastAPI, a simple browser UI, local document retrieval, OpenAI Responses API, and JSON-based support tickets.

## Features
- Chatbot answers from the knowledge documents in `knowledge/`.
- TXT, MD, and text-based PDF upload.
- Shows source filenames used for an answer.
- Refuses to guess when no relevant passage is found.
- Creates local support tickets.
- Runs in retrieval-only fallback mode if no API key is configured.

## Requirements
- Python 3.11+
- OpenAI API key with API access/billing for AI-generated answers

## Setup on Windows (VS Code terminal / PowerShell)

1. Open this folder in VS Code.
2. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt and run:
   `\.venv\Scripts\activate.bat`

3. Install packages:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env`. Put your API key in `.env`:

   `OPENAI_API_KEY=your_real_api_key_here`

   Keep the `.env` file private. Never paste the API key into `static/index.html`, GitHub, screenshots, or public chats.

5. Start the server from the project root:

   ```powershell
   python -m uvicorn app.main:app --reload
   ```

6. Open http://127.0.0.1:8000 in your browser.
7. Optional: open http://127.0.0.1:8000/docs to test the API endpoints.

## Try these questions
- How long does standard delivery take?
- What is the return policy?
- How long do refunds take?
- Tell me about the backpack.
- Can you tell me my live order status? (The app should not invent order data; it should say the knowledge base has no live order integration.)

## Upload your own knowledge
Use the Knowledge base panel to upload an authorized TXT, MD, or text-based PDF policy document. Ask questions about its contents afterwards.

## Important limitations before public launch
This is a hackathon prototype, not a production customer-support service:
- Ticket storage is a local JSON file and is not suitable for multiple server instances.
- There is no user authentication or agent-only authorization yet.
- Retrieval is lightweight keyword matching, not semantic vector search.
- It does not connect to live orders, payments, shipping providers, or CRM systems.
- Add authentication, tenant isolation, persistent database storage, upload scanning, rate limiting, monitoring, retention controls, and secure deployment before handling real customer data.
- Scanned PDFs require OCR.
