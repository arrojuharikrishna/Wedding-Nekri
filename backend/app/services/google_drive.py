
import os
import json

from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_token_path():
    return Path(
        os.getenv("GOOGLE_TOKEN_FILE", "google_token.json")
    ).resolve()


def get_credentials():

    token_path = get_token_path()

    if not token_path.exists():
        raise RuntimeError("Google Drive is not connected")

    creds = Credentials.from_authorized_user_file(
        str(token_path), SCOPES
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())

    if not creds.valid:
        raise RuntimeError("Google credentials are invalid")

    return creds


def get_drive_service():
    return build(
        "drive",
        "v3",
        credentials=get_credentials()
    )


def get_or_create_folder():

    service = get_drive_service()

    folder_name = os.getenv(
        "GOOGLE_DRIVE_FOLDER_NAME",
        "Wedding-Nekri"
    )

    query = (
        f"name = '{folder_name}' "
        "and mimeType = 'application/vnd.google-apps.folder' "
        "and trashed = false"
    )

    results = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id,name)",
        pageSize=100
    ).execute()

    folders = results.get("files", [])

    if folders:
        return folders[0]["id"]

    folder = service.files().create(
        body={
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        },
        fields="id,name"
    ).execute()

    return folder["id"]


def upload_to_drive(local_path: str, ceremony_id: str):

    service = get_drive_service()
    folder_id = get_or_create_folder()

    metadata = {
        "name": f"{ceremony_id}_ceremony.mp4",
        "parents": [folder_id]
    }

    media = MediaFileUpload(
        local_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=8 * 1024 * 1024
    )

    uploaded = service.files().create(
        body=metadata,
        media_body=media,
        fields="id,name,webViewLink"
    ).execute()

    # Allow anyone with the recording link to view it.
    service.permissions().create(
        fileId=uploaded["id"],
        body={
            "type": "anyone",
            "role": "reader"
        }
    ).execute()

    return {
        "file_id": uploaded["id"],
        "file_name": uploaded["name"],
        "drive_url": uploaded.get("webViewLink")
    }
