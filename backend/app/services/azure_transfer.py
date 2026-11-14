
import os
import tempfile

from azure.storage.blob import BlobServiceClient
from app.services.google_drive import upload_to_drive


def transfer_recording_to_drive(ceremony_id: str):

    account_name = os.getenv("AZURE_STORAGE_ACCOUNT")
    account_key = os.getenv("AZURE_STORAGE_KEY")
    container_name = os.getenv("AZURE_CONTAINER_NAME")

    if not all([account_name, account_key, container_name]):
        raise RuntimeError("Azure credentials are missing")

    service = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=account_key
    )

    blob_name = f"{ceremony_id}/ceremony.mp4"

    blob = service.get_blob_client(
        container=container_name,
        blob=blob_name
    )

    if not blob.exists():
        raise FileNotFoundError(
            f"Recording not found in Azure: {blob_name}"
        )

    with tempfile.TemporaryDirectory() as temp_dir:

        local_path = os.path.join(
            temp_dir,
            f"{ceremony_id}.mp4"
        )

        with open(local_path, "wb") as file:
            stream = blob.download_blob()
            stream.readinto(file)

        result = upload_to_drive(
            local_path=local_path,
            ceremony_id=ceremony_id
        )

    return result
