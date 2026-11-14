
import os
from livekit import api
import secrets
from fastapi import Header
from app.services.livekit import generate_token
from dotenv import load_dotenv

load_dotenv()
def generate_token(
    room_name: str,
        identity: str,
            role: str
            ):
                livekit_url = os.getenv("LIVEKIT_URL")
                    api_key = os.getenv("LIVEKIT_API_KEY")
                        api_secret = os.getenv("LIVEKIT_API_SECRET")

                            if not all([livekit_url, api_key, api_secret]):
                                    raise RuntimeError("LiveKit credentials are missing")

                                        if role not in ("broadcaster", "viewer"):
                                                raise ValueError("Invalid participant role")

                                                    is_broadcaster = role == "broadcaster"

                                                        token = api.AccessToken(api_key, api_secret)

                                                            token.with_identity(identity)
                                                                token.with_name(role.capitalize())

                                                                    token.with_grants(
                                                                            api.VideoGrants(
                                                                                        room_join=True,
                                                                                                    room=room_name,
                                                                                                                can_publish=is_broadcaster,
                                                                                                                            can_subscribe=True,
                                                                                                                                        can_publish_data=is_broadcaster,
                                                                                                                                                )
                                                                                                                                                    )

                                                                                                                                                        return token.to_jwt()
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
                                                                                                                                                                                                                                                                                