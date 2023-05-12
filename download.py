import argparse
import json
import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from icecream import ic


def main(file_id):
    """Downloads a file from Google Drive."""

    AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
    TOKEN_URL = "https://accounts.google.com/o/oauth2/token"

    # this will be created if it doesn't exist
    creds_file = "credentials.json"

    # this shold be downloaded from the google cloud console OAuth 2.0 Client IDs
    # https://console.cloud.google.com/apis/credentials
    client_secrets_file = "client_secrets.json"

    with open(client_secrets_file) as f:
        client_secrets = json.load(f)

    REDIRECT_URI = "http://localhost:8080"
    client_config = {
        "installed": {
            "client_id": client_secrets["installed"]["client_id"],
            "client_secret": client_secrets["installed"]["client_secret"],
            "redirect_uris": [REDIRECT_URI],
            "auth_uri": AUTH_URL,
            "token_uri": TOKEN_URL,
            "project_id": client_secrets["installed"]["project_id"],
        }
    }
    # setup scopes for google drive api v3
    SCOPES = [
        "https://www.googleapis.com/auth/drive",
    ]
    ic(client_config)
    # Set up the OAuth2 flow.
    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)

    # Try to load existing credentials from the file.
    creds = None
    if os.path.exists(creds_file):
        with open(creds_file, "r") as f:
            creds_data = json.load(f)
        creds = Credentials.from_authorized_user_info(info=creds_data)

    # If there are no existing credentials, run the OAuth2 flow to get them.
    if not creds or not creds.valid:
        creds = flow.run_local_server(port=8080)

        # Save the credentials to the file for future use.
        with open(creds_file, "w") as f:
            creds_json_str = creds.to_json()
            f.write(creds_json_str)

    # Build the Google Drive API service object.
    drive_service = build("drive", "v3", credentials=creds)

    ic(file_id)
    # get the file content.
    # Use Export with Docs Editors files.', 'domain': 'global', 'reason': 'fileNotDownloadable', 'location': 'alt', 'locationType': 'parameter'}]">
    # download a google sheet
    file_content = (
        drive_service.files().export(fileId=file_id, mimeType="text/csv").execute()
    )

    # print length of the file content or None
    if file_content:
        ic(len(file_content))
    else:
        ic(file_content)

    # Save the file content to a file.
    with open(f"{file_id}.csv", "wb") as f:
        f.write(file_content)
        print(f"wrote {file_id}.csv")


if __name__ == "__main__":
    # usage --sheet file_id
    parser = argparse.ArgumentParser(description="Download a file from Google Drive")
    parser.add_argument("--sheet", dest="file_id", help="Google Sheet file id")
    args = parser.parse_args()
    file_id = args.file_id

    main(file_id)
