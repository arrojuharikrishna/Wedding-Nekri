
import os
from livekit import api


async def start_room_recording(room_name: str, filepath: str):

    account_name = os.getenv("AZURE_STORAGE_ACCOUNT")
    account_key = os.getenv("AZURE_STORAGE_KEY")
    container_name = os.getenv("AZURE_CONTAINER_NAME")

    if not all([account_name, account_key, container_name]):
        raise RuntimeError("Azure storage credentials are missing")

    azure_storage = api.AzureBlobUpload(
        account_name=account_name,
        account_key=account_key,
        container_name=container_name
    )

    file_output = api.EncodedFileOutput(
        file_type=api.EncodedFileType.MP4,
        filepath=filepath,
        azure=azure_storage
    )

    request = api.RoomCompositeEgressRequest(
        room_name=room_name,
        layout="speaker",
        preset=api.EncodingOptionsPreset.H264_1080P_30,
        audio_only=False,
        file_outputs=[file_output]
    )

    async with api.LiveKitAPI() as lkapi:
        info = await lkapi.egress.start_room_composite_egress(request)

    return info


async def stop_room_recording(egress_id: str):

    request = api.StopEgressRequest(
        egress_id=egress_id
    )

    async with api.LiveKitAPI() as lkapi:
        info = await lkapi.egress.stop_egress(request)

    return info
