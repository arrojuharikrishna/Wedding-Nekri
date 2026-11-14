
import os
from livekit import api


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
