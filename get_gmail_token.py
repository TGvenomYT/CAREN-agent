"""
One-time script to get Gmail OAuth2 refresh token.
Run locally: python get_gmail_token.py

Steps before running:
1. Go to https://console.cloud.google.com
2. Create a project (or select existing)
3. APIs & Services → Enable APIs → Enable "Gmail API"
4. APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID
5. Application type: Desktop app
6. Download the JSON → save as client_secret.json in this folder
7. Run: python get_gmail_token.py
8. A browser will open — log in and grant access
9. Copy the printed GMAIL_REFRESH_TOKEN → add to HF Space secrets
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def main():
    flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n========== ADD THESE TO HF SPACE SECRETS ==========")
    print(f"GMAIL_CLIENT_ID     = {creds.client_id}")
    print(f"GMAIL_CLIENT_SECRET = {creds.client_secret}")
    print(f"GMAIL_REFRESH_TOKEN = {creds.refresh_token}")
    print("====================================================\n")

if __name__ == "__main__":
    main()
