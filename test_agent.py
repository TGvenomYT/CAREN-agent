import os
import json
from dotenv import load_dotenv

# Import the functions from your newly refactored file
from mailing_agent import (
    send_email, 
    generate_body, 
    summarize_inbox, 
    classify_inbox
)

# Load environment variables to ensure it picks up your .env file
load_dotenv()

def print_result(title, result):
    """Helper function to print the JSON dictionaries nicely."""
    print(f"\n{'='*40}")
    print(f" TESTING: {title}")
    print(f"{'='*40}")
    print(json.dumps(result, indent=2))
    print("\n")

def main():
    while True:
        print("\n--- Test Menu ---")
        print("1. Test generate_body (Ollama)")
        print("2. Test summarize_inbox (IMAP + Ollama)")
        print("3. Test classify_inbox (IMAP + Scikit-Learn)")
        print("4. Test send_email (SMTP)")
        print("5. Exit")
        
        choice = input("Select a function to test: ")

        if choice == "1":
            subject = input("Enter a test subject: ")
            print("Generating... (This might take a few seconds)")
            result = generate_body(subject)
            print_result("Generate Body", result)

        elif choice == "2":
            print("Fetching and summarizing... (This will take time depending on unread emails)")
            result = summarize_inbox()
            print_result("Summarize Inbox", result)

        elif choice == "3":
            print("Fetching and classifying... (Checking the last 10 emails)")
            result = classify_inbox()
            print_result("Classify Inbox", result)

        elif choice == "4":
            receiver = input("Enter receiver email: ")
            subject = input("Enter subject: ")
            body = input("Enter body text: ")
            
            # Fetch sender creds from .env
            sender = os.getenv("SENDER_EMAIL")
            password = os.getenv("EMAIL_PASSWORD")
            server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
            port = int(os.getenv("SMTP_PORT", 465))
            
            print("Sending...")
            result = send_email(server, port, sender, password, receiver, subject, body)
            print_result("Send Email", result)

        elif choice == "5":
            print("Exiting test script.")
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()