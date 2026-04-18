import os
import asyncio
from functools import partial
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastrtc import Stream, ReplyOnPause, get_stt_model, get_tts_model
from typing import List, Optional
import tempfile
import shutil
import uvicorn
from dotenv import load_dotenv
import re
from fastapi.middleware.cors import CORSMiddleware
import mailing_agent
import gradio as gr

load_dotenv()


def clean_text(text: str) -> str:
    """
    Strips markdown, special characters, and emojis to make text TTS-friendly.
    """
    if not text:
        return ""
    text = re.sub(r'[*_~#`]+', '', text)
    text = re.sub(r'[^\w\s.,!?\'"-]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


app = FastAPI(title="Caren AI Web Backend")

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models for API Requests ---
class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    attachment_path: Optional[str] = None

class SubjectRequest(BaseModel):
    subject: str

# ==========================================
# API ENDPOINTS
# ==========================================

@app.get("/api/health")
def health_check():
    return {"status": "online", "message": "FastAPI is running!"}

@app.get("/api/mail/summarize")
async def summarize_emails(limit: int = 10):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, partial(mailing_agent.summarize_inbox, limit=limit))
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.get("/api/mail/classify")
async def get_classification(limit: int = 10):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, partial(mailing_agent.classify_inbox, limit=limit))
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.post("/api/mail/generate-body")
async def post_generate_body(req: SubjectRequest):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, partial(mailing_agent.generate_body, req.subject))
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.post("/api/mail/send")
async def post_send_email(
    to: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    attachment: Optional[UploadFile] = File(None)
):
    sender = os.getenv("SENDER_EMAIL")
    password = os.getenv("EMAIL_PASSWORD")
    server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", 465))

    temp_path = None
    if attachment and attachment.filename:
        suffix = os.path.splitext(attachment.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(attachment.file, tmp)
            temp_path = tmp.name

    try:
        result = mailing_agent.send_email(
            server, port, sender, password,
            to, subject, body, temp_path
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

# ==========================================
# FASTRTC VOICE STREAM
# ==========================================

stt_model = get_stt_model()  # Moonshine
tts_model = get_tts_model()  # Kokoro

def caren_voice_handler(audio_input):
    """
    Core voice loop for FastRTC.
    Receives audio -> STT -> Ollama -> TTS -> streams audio back.
    """
    transcript = stt_model.stt(audio_input)
    if not transcript or not transcript.strip():
        return

    print(f"User said: {transcript}")

    import ollama
    try:
        response = ollama.generate(
            model=os.getenv("OLLAMA_MODEL", "llama2"),
            prompt=f"You are Caren, a helpful AI assistant. Be concise. User: {transcript}"
        )
        raw_ai_text = response.get('response', 'I am not sure how to respond to that.')
    except Exception as e:
        raw_ai_text = f"I encountered an error: {str(e)}"

    ai_text = clean_text(raw_ai_text)
    print(f"Caren says: {ai_text}")

    for audio_chunk in tts_model.stream_tts_sync(ai_text):
        yield audio_chunk

stream = Stream(
    handler=ReplyOnPause(caren_voice_handler),
    modality="audio",
    mode="send-receive"
)

# ==========================================
# MOUNT GRADIO VOICE UI
# ==========================================
app = gr.mount_gradio_app(app, stream.ui, path="/voice")

# Redirect /voice -> /voice/ (Gradio needs the trailing slash)
@app.get("/voice")
async def voice_redirect():
    return RedirectResponse(url="/voice/")

# ==========================================
# STATIC FILES — MUST BE LAST
# (A catch-all mount at "/" will intercept API routes if placed earlier)
# ==========================================
if os.path.exists("caren-ui/dist"):
    app.mount("/", StaticFiles(directory="caren-ui/dist", html=True), name="static")
else:
    print("Warning: caren-ui/dist not found. Serving API only.")

if __name__ == "__main__":
    print("Starting server... check http://0.0.0.0:8000 for the UI")
    uvicorn.run(app, host="0.0.0.0", port=8000)