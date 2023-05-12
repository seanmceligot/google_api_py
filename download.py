import argparse
import json
import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from icecream import ic

"""
This script downloads a google sheet as a csv file.

to create the client_secrets.json file, follow the instructions here:
https://developers.google.com/identity/protocols/oauth2/native-app#step-1-configure-your-project

add the google drive api to your project:
https://console.cloud.google.com/apis/library/drive.googleapis.com

"""
AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://accounts.google.com/o/oauth2/token"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
]
REDIRECT_URI = "http://localhost:8080"


def get_client_config(client_secrets, REDIRECT_URI):
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
    ic(client_config)
    return client_config


def get_flow_using_browser(client_secrets):
    client_config = get_client_config(client_secrets, REDIRECT_URI)
    # Set up the OAuth2 flow.
    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    return flow


"""
This is the flow for offline access

documenation:
https://googleapis.github.io/google-api-python-client/docs/oauth.html

https://developers.google.com/identity/protocols/oauth2/native-app#offline-access

"""


def get_flow_offline(client_secrets):
    ic(client_secrets)
    flow = InstalledAppFlow.from_client_secrets_file(
        client_secrets, scopes=SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob"
    )
    ic(flow)
    # Generate authorization URL
    auth_url, _ = flow.authorization_url(prompt="consent")

    # Print the authorization URL
    print("Please visit the following URL to authorize the application:")
    print(auth_url)

    # Wait for the response
    authorization_code = input("Enter the authorization code: ")
    ic(authorization_code)
    flow.fetch_token(code=authorization_code)

    return flow


def main(file_id, is_offline=False):
    """Downloads a file from Google Drive."""

    # this will be created if it doesn't exist
    creds_file = "credentials.json"

    # this shold be downloaded from the google cloud console OAuth 2.0 Client IDs
    # https://console.cloud.google.com/apis/credentials
    client_secrets_file = "client_secrets.json"

    with open(client_secrets_file) as f:
        client_secrets = json.load(f)

    if is_offline:
        flow = get_flow_offline(client_secrets_file)
    else:
        flow = get_flow_using_browser(client_secrets)

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
    parser.add_argument("--offline", dest="is_offline", action="store_true")
    args = parser.parse_args()
    file_id = args.file_id
    is_offline = args.is_offline

    main(file_id, is_offline)
