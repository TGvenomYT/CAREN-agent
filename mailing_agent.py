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
        # --- SPAM ---
        {"text": "Congratulations! You won a lottery. Claim now.", "label": 1},
        {"text": "Get cheap meds online!", "label": 1},
        {"text": "You have been selected for a prize.", "label": 1},
        {"text": "Urgent: Update your account information.", "label": 1},
        {"text": "Limited time offer just for you!", "label": 1},
        {"text": "Get rich quick with this simple trick!", "label": 1},
        {"text": "Click here to claim your free iPhone!", "label": 1},
        {"text": "You are a winner! Collect your reward now.", "label": 1},
        {"text": "Earn $5000 a week working from home.", "label": 1},
        {"text": "Nigerian prince needs your help transferring funds.", "label": 1},
        {"text": "Your account has been compromised. Verify now.", "label": 1},
        {"text": "URGENT: You have a pending payment. Act now!", "label": 1},
        {"text": "Make money fast with this secret method!", "label": 1},
        {"text": "You have won a $1000 gift card. Redeem now.", "label": 1},
        {"text": "100% free weight loss pills that actually work!", "label": 1},
        {"text": "Increase your credit score instantly!", "label": 1},
        {"text": "Hot singles in your area want to meet you!", "label": 1},
        {"text": "Work from home and make thousands daily.", "label": 1},
        {"text": "Exclusive deal: Buy now before it's too late!", "label": 1},
        {"text": "Your PayPal account is suspended. Click to verify.", "label": 1},
        {"text": "FREE mortgage rates for qualified applicants!", "label": 1},
        {"text": "You've been chosen! Claim your reward.", "label": 1},
        {"text": "Lose 20 pounds in 2 weeks guaranteed!", "label": 1},
        {"text": "Double your investment in 24 hours!", "label": 1},
        {"text": "WINNER! Your email has been randomly selected.", "label": 1},
        {"text": "Cheap Viagra, Cialis, and more online!", "label": 1},
        {"text": "Act now! This offer expires in 1 hour.", "label": 1},
        {"text": "Your computer is infected! Download our free cleaner.", "label": 1},
        {"text": "Millions waiting for you. Click to claim.", "label": 1},
        {"text": "IRS notice: You have an outstanding refund.", "label": 1},
        {"text": "Be your own boss. Join our MLM network today.", "label": 1},
        {"text": "Guaranteed loan approval, no credit check needed.", "label": 1},
        {"text": "We can help erase your student debt now.", "label": 1},
        {"text": "Special Bitcoin investment opportunity - 300% returns!", "label": 1},
        {"text": "Enlarge your account with our exclusive offer!", "label": 1},
        {"text": "You qualify for a free government grant.", "label": 1},
        {"text": "Risk-free investment opportunity. Limited spots available.", "label": 1},
        {"text": "Meet beautiful women online. Sign up for free!", "label": 1},
        {"text": "Your subscription was charged. Click to cancel.", "label": 1},
        {"text": "Unclaimed package. Provide details to receive it.", "label": 1},
        # --- CLEAN ---
        {"text": "Meeting at 10am tomorrow.", "label": 0},
        {"text": "attached document", "label": 0},
        {"text": "Please find attached the report.", "label": 0},
        {"text": "Lunch at 1pm?", "label": 0},
        {"text": "Reminder: Your appointment is tomorrow.", "label": 0},
        {"text": "your amazon order has been shipped", "label": 0},
        {"text": "Your bank statement is ready.", "label": 0},
        {"text": "Your flight details are confirmed.", "label": 0},
        {"text": "Team standup is at 9am. Please join the call.", "label": 0},
        {"text": "Hi, can you review the pull request I submitted?", "label": 0},
        {"text": "Your interview is scheduled for Monday at 2pm.", "label": 0},
        {"text": "Invoice #4521 is attached for your records.", "label": 0},
        {"text": "Project deadline has been extended to next Friday.", "label": 0},
        {"text": "Your order has been delivered successfully.", "label": 0},
        {"text": "Please review the attached contract before signing.", "label": 0},
        {"text": "Could you send me the Q3 financial report?", "label": 0},
        {"text": "Your subscription has been renewed for another year.", "label": 0},
        {"text": "Doctor's appointment reminder for Thursday at 3pm.", "label": 0},
        {"text": "Your resume has been received. We will be in touch.", "label": 0},
        {"text": "The board meeting minutes are attached.", "label": 0},
        {"text": "Happy birthday! Hope you have a wonderful day.", "label": 0},
        {"text": "Here are the notes from today's meeting.", "label": 0},
        {"text": "Your password was changed successfully.", "label": 0},
        {"text": "The package was delivered to your mailbox.", "label": 0},
        {"text": "Can we reschedule our call to next week?", "label": 0},
        {"text": "Your tax documents are ready for download.", "label": 0},
        {"text": "New comment on your GitHub issue #234.", "label": 0},
        {"text": "Your Zoom meeting starts in 15 minutes.", "label": 0},
        {"text": "Quarterly performance review scheduled for next week.", "label": 0},
        {"text": "Let me know when you are free for a quick sync.", "label": 0},
        {"text": "Your hotel booking has been confirmed.", "label": 0},
        {"text": "Please find the updated project timeline in the attachment.", "label": 0},
        {"text": "Your electricity bill is due on the 15th.", "label": 0},
        {"text": "New PR merged into main branch successfully.", "label": 0},
        {"text": "Reminder: submit your timesheet by end of day Friday.", "label": 0},
        {"text": "The client approved the proposal. Great work!", "label": 0},
        {"text": "Your prescription is ready for pickup.", "label": 0},
        {"text": "Call agenda for tomorrow has been shared.", "label": 0},
        {"text": "Your Wi-Fi bill payment receipt is attached.", "label": 0},
        {"text": "Seminar registration confirmation for next Monday.", "label": 0},
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
    # Truncate to first 500 chars — the model was trained on short sentences,
    # feeding it a 100KB HTML email body wastes time and wrecks accuracy.
    snippet = email_text[:500] if email_text else ""
    X_new = spam_vectorizer.transform([snippet])
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
    """Fetches recent emails and summarizes them."""
    IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
    EMAIL_ACCOUNT = os.getenv("SENDER_EMAIL")
    PASSWORD = os.getenv("EMAIL_PASSWORD")

    if not EMAIL_ACCOUNT or not PASSWORD:
        return {"status": "error", "message": "Email credentials missing in environment."}

    summaries = []
    try:
        # Create ONE Ollama instance (not per-email)
        llm = Ollama(model=os.getenv("OLLAMA_MODEL", "llama2"))
        splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
        prompt = PromptTemplate(
            input_variables=["email_content"],
            template="Summarize the following email in a concise manner and in less than 5 lines:\n{email_content}"
        )

        with imapclient.IMAPClient(IMAP_SERVER) as client:
            client.login(EMAIL_ACCOUNT, PASSWORD)
            client.select_folder("INBOX")
            messages = client.search("ALL")
            target_ids = messages[-limit:]

            # Batch-fetch all emails in one IMAP call
            if not target_ids:
                return {"status": "success", "data": []}
            raw_messages = client.fetch(target_ids, ["RFC822"])

            for msg_id in target_ids:
                raw_message = raw_messages[msg_id][b"RFC822"]
                email_msg = email.message_from_bytes(raw_message)

                subject = decode_subject(email_msg["Subject"])
                body = extract_email_body(email_msg)

                chunks = splitter.split_text(body)
                if chunks:
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

            if not recent_messages:
                return {"status": "success", "data": []}

            # Batch-fetch ALL emails in one IMAP call (not one-by-one)
            raw_messages = client.fetch(recent_messages, ["RFC822"])

            for msg_id in recent_messages:
                raw_message = raw_messages[msg_id][b"RFC822"]
                email_msg = email.message_from_bytes(raw_message)

                subject = decode_subject(email_msg["Subject"])
                body = extract_email_body(email_msg)

                # Combine subject + body for better classification
                combined = f"{subject} {body}" if body else subject
                spam_pred = predict_spam(combined)
                label = "Spam" if spam_pred == 1 else "Clean"

                results.append({
                    "subject": subject,
                    "label": label
                })

        return {"status": "success", "data": list(reversed(results))}
    except Exception as e:
        return {"status": "error", "message": str(e)}