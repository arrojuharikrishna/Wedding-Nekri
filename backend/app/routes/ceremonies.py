import hashlib
import time

from fastapi import UploadFile, File

from app.services.segment_storage import upload_recording_segment
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from uuid import uuid4
import os
import secrets
from fastapi import Header
from app.services.livekit import generate_token
from app.services.recording import (
    start_room_recording,
    stop_room_recording
)
router = APIRouter(prefix="/ceremonies", tags=["Ceremonies"])

ceremonies = {}
active_recordings = {}
segment_upload_tokens = {}
class CeremonyCreate(BaseModel):
    title: str

@router.post("/")
def create_ceremony(data: CeremonyCreate):

    ceremony_id = str(uuid4())

    ceremony = {
        "id": ceremony_id,
        "title": data.title,
        "status": "created",
        "room_name": f"ceremony-{ceremony_id}"
    }

    ceremonies[ceremony_id] = ceremony

    return ceremony

@router.get("/")
def get_ceremonies():
    return list(ceremonies.values())

            
@router.get("/{ceremony_id}")
def get_ceremony(ceremony_id: str):

    ceremony = ceremonies.get(ceremony_id)

    if not ceremony:
        raise HTTPException(
            status_code=404,
            detail="Ceremony not found"
        )

    return ceremony

@router.post("/{ceremony_id}/token")
def get_ceremony_token(
    ceremony_id: str,
    role: str = "viewer",
    x_admin_secret: str = Header(default="")
):
    ceremony = ceremonies.get(ceremony_id)

    if not ceremony:
        raise HTTPException(
            status_code=404,
            detail="Ceremony not found"
        )

    if role not in ("viewer", "broadcaster"):
        raise HTTPException(
            status_code=400,
            detail="Invalid role"
        )

    if role == "broadcaster":
        admin_secret = os.getenv("ADMIN_BROADCAST_SECRET")

        if not admin_secret or not secrets.compare_digest(
            x_admin_secret, admin_secret
        ):
            raise HTTPException(
                status_code=403,
                detail="Broadcast access denied"
            )

    token = generate_token(
        room_name=ceremony["room_name"],
        identity=f"{role}-{secrets.token_hex(8)}",
        role=role
    )

    return {
        "token": token,
        "server_url": os.getenv("LIVEKIT_URL"),
        "room_name": ceremony["room_name"],
        "role": role
    }

@router.post("/{ceremony_id}/recording/start")
async def start_recording(
    ceremony_id: str,
    x_admin_secret: str = Header(default="")
):
    ceremony = ceremonies.get(ceremony_id)

    if not ceremony:
        raise HTTPException(
            status_code=404,
            detail="Ceremony not found"
        )

    admin_secret = os.getenv("ADMIN_BROADCAST_SECRET")

    if not admin_secret or not secrets.compare_digest(
        x_admin_secret, admin_secret
    ):
        raise HTTPException(
            status_code=403,
            detail="Broadcast access denied"
        )

    if ceremony_id in active_recordings:
        raise HTTPException(
            status_code=409,
            detail="Recording already active"
        )

    try:
        info = await start_room_recording(
            room_name=ceremony["room_name"],
            filepath=f"{ceremony_id}/ceremony.mp4"
        )

        active_recordings[ceremony_id] = info.egress_id

        ceremony["recording_status"] = "recording"

        return {
            "status": "recording",
            "egress_id": info.egress_id,
            "room_name": ceremony["room_name"],
            "storage": "Azure Blob Storage"
        }

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Recording could not start: {type(exc).__name__}"
        )


@router.post("/{ceremony_id}/recording/stop")
async def stop_recording(
    ceremony_id: str,
    x_admin_secret: str = Header(default="")
):
    ceremony = ceremonies.get(ceremony_id)

    if not ceremony:
        raise HTTPException(
            status_code=404,
            detail="Ceremony not found"
        )

    admin_secret = os.getenv("ADMIN_BROADCAST_SECRET")

    if not admin_secret or not secrets.compare_digest(
        x_admin_secret, admin_secret
    ):
        raise HTTPException(
            status_code=403,
            detail="Broadcast access denied"
        )

    egress_id = active_recordings.get(ceremony_id)

    if not egress_id:
        raise HTTPException(
            status_code=404,
            detail="No active recording found"
        )

    try:
        info = await stop_room_recording(egress_id)

        active_recordings.pop(ceremony_id, None)

        ceremony["recording_status"] = "stopped"

        return {
            "status": "stopped",
            "egress_id": egress_id,
            "message": "Recording stop requested"
        }

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Recording could not stop: {type(exc).__name__}"
        )

@router.post("/{ceremony_id}/segments/upload-token")
def create_segment_upload_token(
    ceremony_id: str,
    x_admin_secret: str = Header(default="")
):
    ceremony = ceremonies.get(ceremony_id)

    if not ceremony:
        raise HTTPException(
            status_code=404,
            detail="Ceremony not found"
        )

    admin_secret = os.getenv("ADMIN_BROADCAST_SECRET")

    if not admin_secret or not secrets.compare_digest(
        x_admin_secret, admin_secret
    ):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    segment_upload_tokens[token_hash] = {
        "ceremony_id": ceremony_id,
        "expires_at": time.time() + (12 * 60 * 60)
    }

    return {
        "upload_token": token,
        "expires_in_hours": 12,
        "ceremony_id": ceremony_id
    }


@router.post("/{ceremony_id}/segments/{segment_number}")
def upload_segment(
    ceremony_id: str,
    segment_number: int,
    file: UploadFile = File(...),
    authorization: str = Header(default="")
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Upload token required"
        )

    token = authorization[7:]
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    token_data = segment_upload_tokens.get(token_hash)

    if not token_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid upload token"
        )

    if token_data["expires_at"] < time.time():
        segment_upload_tokens.pop(token_hash, None)

        raise HTTPException(
            status_code=401,
            detail="Upload token expired"
        )

    if token_data["ceremony_id"] != ceremony_id:
        raise HTTPException(
            status_code=403,
            detail="Token does not belong to this ceremony"
        )

    if segment_number < 1:
        raise HTTPException(
            status_code=400,
            detail="Invalid segment number"
        )

    if not file.filename or not file.filename.lower().endswith(".webm"):
        raise HTTPException(
            status_code=400,
            detail="Only WebM recordings are accepted"
        )

    try:
        result = upload_recording_segment(
            ceremony_id=ceremony_id,
            segment_number=segment_number,
            file_stream=file.file
        )

        return result

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Segment upload failed: {type(exc).__name__}"
        )

    finally:
        file.file.close()
