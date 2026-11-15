
import os
from azure.storage.blob import BlobServiceClient, ContentSettings


def upload_recording_segment(
    ceremony_id: str,
    segment_number: int,
    file_stream
):
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT")
    account_key = os.getenv("AZURE_STORAGE_KEY")
    container_name = os.getenv("AZURE_CONTAINER_NAME")

    if not all([account_name, account_key, container_name]):
        raise RuntimeError("Azure storage credentials are missing")

    if segment_number < 1:
        raise ValueError("Invalid segment number")

    blob_service = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=account_key
    )

    blob_name = (
        f"{ceremony_id}/segments/"
        f"segment-{segment_number:04d}.webm"
    )

    blob_client = blob_service.get_blob_client(
        container=container_name,
        blob=blob_name
    )

    # Stream the file to Azure instead of loading it into memory.
    blob_client.upload_blob(
        file_stream,
        overwrite=False,
        content_settings=ContentSettings(
            content_type="video/webm"
        )
    )

    properties = blob_client.get_blob_properties()

    return {
        "blob_name": blob_name,
        "size_bytes": properties.size,
        "status": "uploaded"
    }
