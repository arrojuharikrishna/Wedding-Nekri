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
