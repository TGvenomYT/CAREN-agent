"""
One-time script to get Gmail OAuth2 refresh token.
Run locally: python get_gmail_token.py

Steps:
1. Go to https://console.cloud.google.com
2. APIs & Services → Enable "Gmail API"
3. Credentials → Create OAuth 2.0 Client ID (Desktop app type)
4. Copy the Client ID and Client Secret from the credentials page
5. Run this script: python get_gmail_token.py
6. Enter client ID and secret when prompted
7. A browser opens — log in and grant access
8. Copy the 3 printed values → add to HF Space secrets
"""

import glob
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def main():
    # Auto-detect the downloaded client secret JSON
    matches = glob.glob("client_secret*.json")
    if not matches:
        print("ERROR: No client_secret*.json found in current directory.")
        return
    secret_file = matches[0]
    print(f"Using: {secret_file}")

    flow = InstalledAppFlow.from_client_secrets_file(secret_file, SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n========== ADD THESE TO HF SPACE SECRETS ==========")
    print(f"GMAIL_CLIENT_ID     = {creds.client_id}")
    print(f"GMAIL_CLIENT_SECRET = {creds.client_secret}")
    print(f"GMAIL_REFRESH_TOKEN = {creds.refresh_token}")
    print("====================================================\n")

if __name__ == "__main__":
    main()
