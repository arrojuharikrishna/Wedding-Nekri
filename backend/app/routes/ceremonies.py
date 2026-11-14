from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from uuid import uuid4

router = APIRouter(prefix="/ceremonies", tags=["Ceremonies"])

ceremonies = {}

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
