import smtplib
import ssl
import os
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
from dotenv import load_dotenv
import imapclient
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.prompts import PromptTemplate  
from langchain_community.llms import Ollama 

# Load environment variables
load_dotenv()

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def decode_subject(subject_header):
    """Decodes email subject to a readable string."""
    if not subject_header:
        return "(No Subject)"
    decoded = decode_header(subject_header)
    subject_str = ''
    for s, enc in decoded:
        if isinstance(s, bytes):
            subject_str += s.decode(enc or 'utf-8', errors='ignore')
        else:
            subject_str += s
    return subject_str

def extract_email_body(email_msg):
    """Extracts plain text body from an email message."""
    if email_msg.is_multipart():
        for part in email_msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode("utf-8", errors="ignore")
    else:
        return email_msg.get_payload(decode=True).decode("utf-8", errors="ignore")
    return "No readable content found."

# ==========================================
# SPAM CLASSIFIER SETUP (Loads once on startup)
# ==========================================
def _train_spam_classifier():
    """Trains the spam model in memory on startup to save time."""
    data = [
        {"text": "Congratulations! You won a lottery. Claim now.", "label": 1},
        {"text": "Meeting at 10am tomorrow.", "label": 0},
        {"text": "Get cheap meds online!", "label": 1},
        {'text': 'attached document','label':0},
        {"text": "Please find attached the report.", "label": 0},
        {"text": "You have been selected for a prize.", "label": 1},
        {"text": "Lunch at 1pm?", "label": 0},
        {"text": "Urgent: Update your account information.", "label": 1},
        {"text": "Reminder: Your appointment is tomorrow.", "label": 0},
        {"text": "Limited time offer just for you!", "label": 1},
        {"text": "your amazon order has been shipped", "label": 0},
        {"text": "Your bank statement is ready.", "label": 0},
        {"text": "Get rich quick with this simple trick!", "label": 1},
        {"text": "Your flight details are confirmed.", "label": 0},
    ]
    df = pd.DataFrame(data)
    vectorizer = CountVectorizer()
    X = vectorizer.fit_transform(df["text"])
    y = df["label"]
    model = LogisticRegression()
    model.fit(X, y)
    return model, vectorizer

# Initialize model globally
spam_model, spam_vectorizer = _train_spam_classifier()

def predict_spam(email_text: str) -> int:
    """Returns 1 for spam, 0 for clean."""
    X_new = spam_vectorizer.transform([email_text])
    return int(spam_model.predict(X_new)[0])


# ==========================================
# CORE API FUNCTIONS
# ==========================================

def send_email(smtp_server: str, port: int, sender_email: str, password: str,
               receiver_email: str, subject: str, email_body: str,
               attachment_path: str = None) -> dict:
    """Composes and sends an email. Returns a status dictionary."""
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(email_body, "plain"))

    if attachment_path and os.path.isfile(attachment_path):
        try:
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(attachment_path)}")
            message.attach(part)
        except Exception as e:
            return {"status": "error", "message": f"Failed to attach file: {str(e)}"}

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        return {"status": "success", "message": "Email sent successfully!"}
    except Exception as e:
        return {"status": "error", "message": f"SMTP Error: {str(e)}"}


def generate_body(subject: str) -> dict:
    """Generates a summarized email body using Ollama."""
    prompt_template = PromptTemplate(
        input_variables=["subject"],
        template=(
            "Generate a concise, crisp, 3-line email body without a salutation. "
            "Do NOT output 'Here is a concise email body'. "
            "Base it on this subject: {subject}\n\n"
            "Ensure the response has specific details filled in without placeholders. "
            "Do not use names of personalities until specified. "
            "Do not add your own context, use only the given data."
        )
    )
    
    try:
        # Use Ollama locally (requires Ollama to be running)
        llm = Ollama(model=os.getenv("OLLAMA_MODEL", "llama2"), temperature=0.7)
        chain = prompt_template | llm
        body = chain.invoke({'subject': subject})
        
        if body.strip():
            return {"status": "success", "body": body.strip()}
        else:
            return {"status": "error", "message": "Ollama generated an empty response."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def summarize_inbox(limit: int = 10) -> dict:
    """Fetches up to 5 unread emails and summarizes them."""
    IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
    EMAIL_ACCOUNT = os.getenv("SENDER_EMAIL")
    PASSWORD = os.getenv("EMAIL_PASSWORD")

    if not EMAIL_ACCOUNT or not PASSWORD:
        return {"status": "error", "message": "Email credentials missing in environment."}

    summaries = []
    try:
        with imapclient.IMAPClient(IMAP_SERVER) as client:
            client.login(EMAIL_ACCOUNT, PASSWORD)
            client.select_folder("INBOX")
            messages = client.search("ALL")

            # Fetch the last 5 unread messages
            for msg_id in messages[-limit:]:
                raw_message = client.fetch([msg_id], ["RFC822"])[msg_id][b"RFC822"]
                email_msg = email.message_from_bytes(raw_message)
                
                subject = decode_subject(email_msg["Subject"])
                body = extract_email_body(email_msg)
                
                # Summarize with LangChain/Ollama
                llm = Ollama(model=os.getenv("OLLAMA_MODEL", "llama2"))
                splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
                chunks = splitter.split_text(body)
                
                if chunks:
                    prompt = PromptTemplate(
                        input_variables=["email_content"],
                        template="Summarize the following email in a concise manner and in less than 5 lines:\n{email_content}"
                    )
                    formatted_prompt = prompt.format(email_content=chunks[0])
                    summary_text = llm.invoke(formatted_prompt)
                else:
                    summary_text = "No readable content to summarize."

                summaries.append({
                    "subject": subject,
                    "summary": summary_text.strip()
                })
                
        return {"status": "success", "data": summaries}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def classify_inbox(limit: int = 10) -> dict:
    """Fetches the {limit} most recent emails and classifies them as Spam or Clean."""
    IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
    EMAIL_ACCOUNT = os.getenv("SENDER_EMAIL")
    PASSWORD = os.getenv("EMAIL_PASSWORD")

    if not EMAIL_ACCOUNT or not PASSWORD:
        return {"status": "error", "message": "Email credentials missing in environment."}

    results = []
    try:
        with imapclient.IMAPClient(IMAP_SERVER) as client:
            client.login(EMAIL_ACCOUNT, PASSWORD)
            client.select_folder("INBOX")
            
            messages = client.search("ALL")
            recent_messages = messages[-limit:] 
            
            for msg_id in recent_messages:
                raw_message = client.fetch([msg_id], ["RFC822"])[msg_id][b"RFC822"]
                email_msg = email.message_from_bytes(raw_message)
                
                subject = decode_subject(email_msg["Subject"])
                body = extract_email_body(email_msg)
                
                spam_pred = predict_spam(body)
                label = "Spam" if spam_pred == 1 else "Clean"
                
                results.append({
                    "subject": subject,
                    "label": label
                })
                
        return {"status": "success", "data": list(reversed(results))} # Newest first
    except Exception as e:
        return {"status": "error", "message": str(e)}