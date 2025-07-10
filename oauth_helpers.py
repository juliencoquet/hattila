"""
oauth_helpers.py - Handles OAuth authentication for Google API access
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

def get_oauth_credentials():
    """
    Get OAuth credentials for Google APIs.
    
    Returns:
        Credentials: Google OAuth credentials
    """
    # Define the scopes needed
    SCOPES = [
        'https://www.googleapis.com/auth/documents',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds = None
    # The token file stores the user's access and refresh tokens
    if os.path.exists('credentials/token.json'):
        try:
            with open('credentials/token.json', 'r') as token:
                creds = Credentials.from_authorized_user_info(
                    json.load(token), SCOPES
                )
        except Exception as e:
            print(f"Error loading token: {e}")
    
    # If credentials don't exist or are invalid, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                creds = None
        
        if not creds:
            try:
                # This will open a browser window for authentication
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials/credentials.json', SCOPES
                )
                creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open('credentials/token.json', 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                print(f"Error in authentication flow: {e}")
                return None
    
    return creds