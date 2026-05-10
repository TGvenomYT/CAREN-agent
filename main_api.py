import os
import asyncio
import hmac
from datetime import datetime, timedelta, timezone
from functools import partial, lru_cache
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastrtc import Stream, ReplyOnPause, get_stt_model, get_tts_model, get_hf_turn_credentials
from typing import List, Optional
import tempfile
import shutil
import uvicorn
from dotenv import load_dotenv
import re
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt, JWTError
import ollama
import mailing_agent
import gradio as gr

load_dotenv()

# Debug: show which secrets are present at startup
_check_vars = ["SENDER_EMAIL", "EMAIL_PASSWORD", "IMAP_SERVER", "OLLAMA_API_KEY", "OLLAMA_HOST", "OLLAMA_MODEL", "APP_PASSWORD", "JWT_SECRET"]
for _v in _check_vars:
    _val = os.getenv(_v)
    print(f"[ENV] {_v} = {'SET' if _val else 'MISSING'}")


# ==========================================
# AUTH CONFIG
# ==========================================
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGO = "HS256"
JWT_TTL_HOURS = 24 * 7  # 7-day session
SESSION_COOKIE = "caren_session"
APP_PASSWORD = os.getenv("APP_PASSWORD", "")

if not JWT_SECRET:
    print("WARNING: JWT_SECRET is empty. Set it in your environment for production.")
if not APP_PASSWORD:
    print("WARNING: APP_PASSWORD is empty. The login endpoint will reject all requests.")


def _create_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_TTL_HOURS)
    return jwt.encode({"sub": "owner", "exp": expire}, JWT_SECRET, algorithm=JWT_ALGO)


def _verify_token(token: str) -> bool:
    if not token or not JWT_SECRET:
        return False
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return True
    except JWTError:
        return False


def _extract_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:]
    cookie = request.cookies.get(SESSION_COOKIE)
    if cookie:
        return cookie
    # Fallback for the voice iframe / static assets that can't set headers.
    return request.query_params.get("t")


def require_auth(request: Request):
    """FastAPI dependency: 401s any request without a valid JWT."""
    if not _verify_token(_extract_token(request)):
        raise HTTPException(status_code=401, detail="Unauthorized")


class VoiceAuthMiddleware(BaseHTTPMiddleware):
    """Gates the Gradio /voice mount (which is not a normal route, so a
    Depends() can't be attached). Verifies the same JWT via header,
    cookie, or ?t= query param."""
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/voice"):
            if not _verify_token(_extract_token(request)):
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)


@lru_cache(maxsize=1)
def _ollama_client() -> ollama.Client:
    """Single Ollama client. Talks to local daemon or Ollama Cloud based on env."""
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    api_key = os.getenv("OLLAMA_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    return ollama.Client(host=host, headers=headers)


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
# Comma-separated list of allowed origins (no trailing slashes).
_origins = [
    o.strip()
    for o in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Voice mount needs middleware-level auth (it's a sub-app, not a route).
app.add_middleware(VoiceAuthMiddleware)

# --- Models for API Requests ---
class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    attachment_path: Optional[str] = None

class SubjectRequest(BaseModel):
    subject: str

class LoginRequest(BaseModel):
    password: str

# ==========================================
# API ENDPOINTS
# ==========================================

@app.get("/api/health")
def health_check():
    return {"status": "online", "message": "FastAPI is running!"}


# ------------------------------------------
# AUTH ENDPOINTS
# ------------------------------------------
@app.post("/api/auth/login")
async def login(req: LoginRequest, response: Response):
    if not APP_PASSWORD or not JWT_SECRET:
        raise HTTPException(status_code=500, detail="Server auth not configured")
    # Constant-time compare to avoid trivial timing leaks.
    if not hmac.compare_digest(req.password.encode(), APP_PASSWORD.encode()):
        raise HTTPException(status_code=401, detail="Invalid password")
    token = _create_token()
    # Cookie covers the /voice iframe (same-origin to backend); the JSON
    # token covers cross-origin /api calls from GitHub Pages.
    response.set_cookie(
        SESSION_COOKIE, token,
        max_age=JWT_TTL_HOURS * 3600,
        httponly=True, secure=True, samesite="none", path="/",
    )
    return {"token": token, "expires_in": JWT_TTL_HOURS * 3600}


@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/", samesite="none", secure=True)
    return {"status": "ok"}


@app.get("/api/auth/check")
async def auth_check(_: None = Depends(require_auth)):
    return {"authenticated": True}


# ------------------------------------------
# MAIL ENDPOINTS (all gated by require_auth)
# ------------------------------------------
@app.get("/api/mail/summarize")
async def summarize_emails(limit: int = 10, _: None = Depends(require_auth)):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, partial(mailing_agent.summarize_inbox, limit=limit))
    if result.get("status") == "error":
        print(f"[summarize] ERROR: {result['message']}")
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.get("/api/mail/classify")
async def get_classification(limit: int = 10, _: None = Depends(require_auth)):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, partial(mailing_agent.classify_inbox, limit=limit))
    if result.get("status") == "error":
        print(f"[classify] ERROR: {result['message']}")
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.post("/api/mail/generate-body")
async def post_generate_body(req: SubjectRequest, _: None = Depends(require_auth)):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, partial(mailing_agent.generate_body, req.subject))
    if result.get("status") == "error":
        print(f"[generate-body] ERROR: {result['message']}")
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.post("/api/mail/send")
async def post_send_email(
    to: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    attachment: Optional[UploadFile] = File(None),
    _: None = Depends(require_auth),
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
        print(f"[send] ERROR: {result['message']}")
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

    try:
        response = _ollama_client().generate(
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

_hf_token = os.getenv("HF_TOKEN")
_rtc_config = get_hf_turn_credentials(token=_hf_token) if _hf_token else None

stream = Stream(
    handler=ReplyOnPause(caren_voice_handler),
    modality="audio",
    mode="send-receive",
    rtc_configuration=_rtc_config,
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
    port = int(os.getenv("PORT", 7860))
    print(f"Starting server... check http://0.0.0.0:{port} for the UI")
    uvicorn.run(app, host="0.0.0.0", port=port)