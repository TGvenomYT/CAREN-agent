# CAREN AI: Neural Mailing Agent & Voice Interface

CAREN (Cybernetic Adaptive Remote Email Network) is a high-performance, glossy-themed AI dashboard designed for advanced email management, automated classification, and real-time voice interaction. It combines a React-based "Glassmorphism" frontend with a robust FastAPI/Python backend utilizing Ollama for local LLM processing.

---

## 🚀 Core Features

- **Neural Hub (Voice Interface):**  
  A persistent, real-RTC voice bridge powered by FastRTC. Interact with CAREN using natural speech with low-latency STT (Moonshine) and TTS (Kokoro).
- **Intel Briefing (Email Summarization):**  
  Fetches recent emails and uses local LLMs (Ollama) to generate concise, 5-line summaries of your inbox content.

- **Security Audit (Spam Classification):**  
  Employs a Scikit-Learn Logistic Regression model to audit incoming data packets and classify them as *Spam* or *Clean*.

- **Dynamic Scan Depth:**  
  A user-controlled slider in the interface allows you to adjust the number of emails processed (5 to 50+) for summaries and audits.

- **Outbound Payload (AI Compose):**  
  A technical compose modal that features **AI Synthesis** to automatically generate professional email bodies based on a subject line.

---

## 🛠️ Technical Stack

- **Frontend:** React, Tailwind CSS, Lucide Icons, Framer Motion (animations), Axios  
- **Backend:** FastAPI (Python), Uvicorn  
- **Voice Engine:** FastRTC, Gradio (mounted), Moonshine (STT), Kokoro (TTS)  
- **AI/ML:** Ollama (Llama2/local models), LangChain, Scikit-Learn (Spam Classifier)  
- **Email Protocol:** IMAP (IMAPClient) for fetching, SMTP (smtplib) for sending  

---

## 📦 Project Structure

```text
caren/
├── caren-ui/           # React Frontend (Vite)
│   ├── src/
│   │   ├── App.jsx     # Main Application Logic & UI
│   │   └── index.css   # Global Styles & Glassmorphism Theme
├── main_api.py         # FastAPI Backend & FastRTC Voice Stream
├── mailing_agent.py    # Core Logic (Email, Summarization, Spam)
├── test_agent.py       # CLI Tool for backend verification
└── .env                # Environment Credentials
```

---

## ⚙️ Setup & Installation

### 1. Backend Configuration

Ensure you have **Python 3.12+** and **Ollama** installed and running.

```bash
# Install dependencies
pip install fastapi uvicorn fastrtc ollama langchain imapclient pandas scikit-learn python-dotenv
```

---

### 2. Environment Variables

Create a `.env` file in the root directory:

```env
SENDER_EMAIL=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
IMAP_SERVER=imap.gmail.com
OLLAMA_MODEL=llama2
```

---

### 3. Run the Backend

```bash
python main_api.py
```

The backend will run on:  
👉 http://localhost:8000  
Voice interface:  
👉 http://localhost:8000/voice  

---

### 4. Run the Frontend

```bash
cd caren-ui
npm install
npm run dev
```

---

## 🛡️ Security Protocol

CAREN uses secure SSL contexts for SMTP and IMAP connections.  
The Spam Classifier is trained in-memory on startup to ensure no local data leakage during the audit process.

---

## 🎨 Design Philosophy

CAREN utilizes a **Glassmorphism aesthetic**, featuring:

- High-blur backdrop filters  
- Translucent panels  
- Vibrant neon accents *(Cyan, Purple, Emerald)*  

This creates a premium, futuristic user experience.

## 💬 Connect With Me

<p align="center">
  <a href="https://github.com/TGvenomYT">
    <img src="https://img.shields.io/badge/GitHub-000?style=for-the-badge&logo=github&logoColor=white"/>
  </a>
  <a href="https://Discord.com/users/tgvenom0441">
     <img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white"/>
  </a>
  <a href="mailto:r.niranjan.dev@proton.me">
    <img src="https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white"/>
  </a>
</p>