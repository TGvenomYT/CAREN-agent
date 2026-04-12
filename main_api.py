import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastrtc import Stream, ReplyOnPause, get_stt_model, get_tts_model
from typing import List, Optional
import uvicorn
from dotenv import load_dotenv
import re
from fastapi.middleware.cors import CORSMiddleware
# Import your refactored mailing agent logic
import mailing_agent
import gradio as gr
load_dotenv()


def clean_text(text: str) -> str:
    """
    Strips markdown, special characters, and emojis to make text TTS-friendly.
    """
    if not text:
        return ""
        
    # 1. Remove markdown symbols (*, _, ~, #, `)
    text = re.sub(r'[*_~#`]+', '', text)
    
    # 2. Remove emojis and weird unicode by keeping only standard alphanumeric and punctuation
    # \w = letters/numbers, \s = whitespace. We also explicitly keep . , ! ? ' " and -
    text = re.sub(r'[^\w\s.,!?\'"-]', '', text)
    
    # 3. Clean up any accidental double spaces created by removing symbols
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text



app = FastAPI(title="Caren AI Web Backend")

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, change this to your React app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],)


# --- Models for API Requests ---
class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    attachment_path: Optional[str] = None

class SubjectRequest(BaseModel):
    subject: str

# --- Standard API Endpoints (For React Buttons) ---

@app.get("/api/mail/summarize")
async def summarize_emails(limit: int = 10):
    # Use the correct function name from your mailing_agent.py
    # and since summarize_inbox() already returns the {"data": ...} format,
    # you can just return its output directly.
    result = mailing_agent.summarize_inbox(limit=limit)
    return result

@app.get("/api/mail/classify")
async def get_classification(limit: int = 10):
    result = mailing_agent.classify_inbox(limit=limit)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.post("/api/mail/generate-body")
async def post_generate_body(req: SubjectRequest):
    result = mailing_agent.generate_body(req.subject)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.post("/api/mail/send")
async def post_send_email(req: EmailRequest):
    # Pull credentials from ENV for security
    sender = os.getenv("SENDER_EMAIL")
    password = os.getenv("EMAIL_PASSWORD")
    server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", 465))
    
    result = mailing_agent.send_email(
        server, port, sender, password, 
        req.to, req.subject, req.body, req.attachment_path
    )
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

# --- FastRTC Voice Stream Logic (Standalone Mode) ---

# Initialize High-Speed Models
# Initialize High-Speed Models
stt_model = get_stt_model() # Moonshine
tts_model = get_tts_model() # Kokoro

# Removed "async" here!
def caren_voice_handler(audio_input):
    """
    This is the core voice loop for FastRTC.
    It receives audio from the browser, turns it to text, 
    gets a response from Ollama, and sends audio back.
    """
    # 1. Speech to Text (STT)
    transcript = stt_model.stt(audio_input)
    if not transcript or not transcript.strip():
        return 

    print(f"User said: {transcript}")

    # 2. Query Ollama (Personality/Standalone Mode)
    import ollama
    try:
        response = ollama.generate(
            model=os.getenv("OLLAMA_MODEL", "llama2"),
            prompt=f"You are Caren, a helpful AI assistant. Be concise. User: {transcript}"
        )
        raw_ai_text = response.get('response', 'I am not sure how to respond to that.')
    except Exception as e:
        raw_ai_text = f"I encountered an error: {str(e)}"

    # --- CLEAN THE TEXT HERE ---
    ai_text = clean_text(raw_ai_text)
    
    print(f"Caren says: {ai_text}")

    # 3. Text to Speech (TTS)
    for audio_chunk in tts_model.stream_tts_sync(ai_text):
        yield audio_chunk
# Create the WebRTC Stream and wrap the handler in ReplyOnPause!
# 1. Setup the Stream
# --- AT THE BOTTOM OF main_api.py ---

# 1. Define the Voice Stream logic
stream = Stream(
    handler=ReplyOnPause(caren_voice_handler),
    modality="audio",
    mode="send-receive"
)

# 2. Add a Health Check (To test if the server is even awake)
@app.get("/api/health")
def health_check():
    return {"status": "online", "message": "FastAPI is running!"}

# 3. Mount the Gradio UI to the FastAPI app
# This explicitly puts the Voice UI at /voice
app = gr.mount_gradio_app(app, stream.ui, path="/voice")

if __name__ == "__main__":
    import uvicorn
    # Important: Run the 'app' variable on port 8000
    print("Starting server... check http://localhost:8000/voice for the UI")
    uvicorn.run(app, host="127.0.0.1", port=8000)