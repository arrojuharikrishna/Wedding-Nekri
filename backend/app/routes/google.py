
import os
import secrets

from pathlib import Path
from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from app.services.azure_transfer import transfer_recording_to_drive
from app.services.google_drive import SCOPES, get_token_path

router = APIRouter(tags=["Google Drive"])

oauth_states = {}


def create_flow(state=None):

    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                os.getenv("GOOGLE_REDIRECT_URI")
            ]
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        state=state
    )

    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    return flow


@router.get("/api/google/authorize")
def google_authorize():

    state = secrets.token_urlsafe(32)
    oauth_states[state] = True

    flow = create_flow(state=state)

    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )

    return RedirectResponse(url)


@router.get("/api/google/callback")
def google_callback(request: Request):

    state = request.query_params.get("state")
    code = request.query_params.get("code")
    error = request.query_params.get("error")

    if error:
        raise HTTPException(
            status_code=400,
            detail="Google authorization was not completed"
        )

    if not state or state not in oauth_states or not code:
        raise HTTPException(
            status_code=400,
            detail="Invalid OAuth state or authorization code"
        )

    oauth_states.pop(state, None)

    flow = create_flow(state=state)
    flow.fetch_token(code=code)

    credentials = flow.credentials

    token_path = get_token_path()
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json())

    return {
        "status": "connected",
        "message": "Google Drive connected successfully"
    }


@router.get("/api/google/status")
def google_status():

    token_path = get_token_path()

    return {
        "connected": token_path.exists()
    }

@router.post("/api/ceremonies/{ceremony_id}/drive/upload")
def upload_ceremony_to_drive(
    ceremony_id: str,
    x_admin_secret: str = Header(default="")
):

    import secrets

    admin_secret = os.getenv("ADMIN_BROADCAST_SECRET")

    if not admin_secret or not secrets.compare_digest(
        x_admin_secret,
        admin_secret
    ):
        raise HTTPException(
            status_code=403,
            detail="Admin access denied"
        )

    try:
        result = transfer_recording_to_drive(ceremony_id)

        return {
            "status": "uploaded",
            "ceremony_id": ceremony_id,
            "google_drive": result
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Drive transfer failed: {type(exc).__name__}"
        )
