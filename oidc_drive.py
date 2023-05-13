import argparse
import json
import os
import sys
from enum import Enum
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from icecream import ic

"""
This script downloads a google sheet as a csv file.

to create the client_secrets.json file, follow the instructions here:
https://developers.google.com/identity/protocols/oauth2/native-app#step-1-configure-your-project

add the google drive api to your project:
https://console.cloud.google.com/apis/library/drive.googleapis.com

"""


class FileType(Enum):
    SHEET = "sheet"
    DOC = "doc"


AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://accounts.google.com/o/oauth2/token"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
]
REDIRECT_URI = "http://localhost:8080"

sheet_mime_type_map = {
    # Spreadsheets	Microsoft Excel	application/vnd.openxmlformats-officedocument.spreadsheetml.sheet	.xlsx
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    # OpenDocument	application/x-vnd.oasis.opendocument.spreadsheet	.ods
    "ods": "application/x-vnd.oasis.opendocument.spreadsheet",
    # PDF	application/pdf	.pdf
    "pdf": "application/pdf",
    # Web Page (HTML)	application/zip	.zip
    "html": "application/zip",
    # Comma Separated Values (first-sheet only)	text/csv	.csv
    "csv": "text/csv",
    # Tab Separated Values (first-sheet only)	text/tab-separated-values	.tsv
    "tsv": "text/tab-separated-values",
}
doc_type_mape = {
    # Microsoft Word	application/vnd.openxmlformats-officedocument.wordprocessingml.document	.docx
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # OpenDocument	application/vnd.oasis.opendocument.text	.odt
    "odt": "application/vnd.oasis.opendocument.text",
    # Rich Text	application/rtf	.rtf
    "rtf": "application/rtf",
    # PDF	application/pdf	.pdf
    "pdf": "application/pdf",
    # Plain Text	text/plain	.txt
    "txt": "text/plain",
    # Web Page (HTML)	application/zip	.zip
    "html": "application/zip",
    # EPUB	application/epub+zip	.epub
    "epub": "application/epub+zip",
}


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


def upload(
    drive_service,
    file_type: FileType,
    upload_mime_type: str,
    file_id: str,
    input_file: Path,
):
    assert file_type in [FileType.SHEET, FileType.DOC]

    # documentation: https://developers.google.com/drive/api/v3/manage-uploads
    # mime types at https://developers.google.com/drive/api/v3/ref-export-formats
    file_metadata = {"name": input_file.name, "mimeType": upload_mime_type}
    media = MediaFileUpload(input_file, mimetype=upload_mime_type)
    drive_service.files().update(
        fileId=file_id, body=file_metadata, media_body=media
    ).execute()
    if file_type == FileType.SHEET:
        print(
            f"your file is uploaded to the url https://docs.google.com/spreadsheets/d/{file_id}/edit"
        )
    if file_type == FileType.DOC:
        print(
            f"your file is uploaded to the url https://docs.google.com/document/d/{file_id}/edit"
        )


def download(drive_service, file_type, download_mime_type, file_id):
    assert file_type in [FileType.SHEET, FileType.DOC]

    # documentation: https://developers.google.com/drive/api/v3/manage-downloads
    # mime types at https://developers.google.com/drive/api/guides/ref-export-formats
    if file_type == FileType.SHEET:
        file_content = (
            drive_service.files()
            .export(fileId=file_id, mimeType=download_mime_type)
            .execute()
        )
    # download a google doc
    elif file_type == FileType.DOC:
        file_content = (
            drive_service.files()
            .export(fileId=file_id, mimeType=download_mime_type)
            .execute()
        )
    else:
        raise ValueError(f"file_type {file_type} not supported")
    return file_content


def load_creds(is_offline):
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
    return creds


def read_and_upload(
    file_type: FileType,
    file_mime_type: str,
    file_id: str,
    in_file: Path,
    is_offline: bool,
):
    creds = load_creds(is_offline)
    # Build the Google Drive API service object.
    drive_service = build("drive", "v3", credentials=creds)

    ic(file_id)
    upload(drive_service, file_type, file_mime_type, file_id, in_file)


def download_and_write_file(
    file_type, file_mime_type, file_id, output_file, is_offline
):
    """Downloads a file from Google Drive."""
    creds = load_creds(is_offline)
    # Build the Google Drive API service object.
    drive_service = build("drive", "v3", credentials=creds)

    ic(file_id)
    # get the file content.
    # Use Export with Docs Editors files.', 'domain': 'global', 'reason': 'fileNotDownloadable', 'location': 'alt', 'locationType': 'parameter'}]">
    # download a google sheet
    file_content = download(drive_service, file_type, file_mime_type, file_id)

    # print length of the file content or None
    if file_content:
        ic(len(file_content))
    else:
        ic(file_content)

    # Save the file content to a file.
    output_file.write(file_content)
    print(f"wrote {output_file}")


if __name__ == "__main__":
    # usage --sheet file_id
    parser = argparse.ArgumentParser(description="Download a file from Google Drive")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--sheet",
        choices=["xlsx", "ods", "pdf", "html", "csv", "tsv"],
        help="download a google sheet to the given export type",
    )

    group.add_argument(
        "--doc",
        choices=["docx", "odt", "rtf", "pdf", "txt", "html", "epub"],
        help="download a google doc to the given export type",
    )
    # offline: print URL and allow the user to copy and paste into any browner
    # google will present a cliploaard copy block for the authorization code
    # the user pastes the code into the terminal
    parser.add_argument("--offline", dest="is_offline", action="store_true")
    # get the file id from the URL of the document. It looks like this:
    # "https://docs.google.com/document/d/THE_FILE_ID/edit
    parser.add_argument(
        "--file-id", dest="file_id", required=True, help="Google Drive file id"
    )
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "-o", "--download", dest="output", type=argparse.FileType("wb")
    )
    action_group.add_argument("--upload", dest="infile")
    args = parser.parse_args()
    file_id = args.file_id
    is_offline = args.is_offline
    output_file = args.output

    if args.sheet:
        file_type = FileType.SHEET
        file_mime_type = sheet_mime_type_map[args.sheet]
    elif args.doc:
        file_type = FileType.DOC
        file_mime_type = doc_type_mape[args.doc]
    else:
        # print help
        parser.print_help()
        sys.exit(1)
    ic(file_type)
    ic(file_mime_type)
    if args.output:
        download_and_write_file(
            file_type, file_mime_type, file_id, output_file, is_offline
        )
    elif args.infile:
        infile = Path(args.infile)
        if not infile.exists():
            print(f"--upload argument: {args.infile} does not exist")
            sys.exit(1)
        read_and_upload(file_type, file_mime_type, file_id, infile, is_offline)
    else:
        # print help
        parser.print_help()
        sys.exit(1)
