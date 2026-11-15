
import os
import secrets

from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

from app.services.azure_transfer import transfer_recording_to_drive
from app.services.google_drive import SCOPES, get_token_path


router = APIRouter(tags=["Google Drive"])

# Stores the PKCE verifier against each OAuth state.
oauth_states = {}


def create_flow(state=None, code_verifier=None, auto_generate=False):

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
        state=state,
        code_verifier=code_verifier,
        autogenerate_code_verifier=auto_generate
    )

    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    return flow


@router.get("/api/google/authorize")
def google_authorize():

    state = secrets.token_urlsafe(32)

    # Generate a PKCE verifier for this authorization.
    flow = create_flow(
        state=state,
        auto_generate=True
    )

    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )

    # Preserve the verifier until Google's callback arrives.
    oauth_states[state] = flow.code_verifier

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

    if not state or not code or state not in oauth_states:
        raise HTTPException(
            status_code=400,
            detail="Invalid OAuth state or authorization code"
        )

    # Retrieve the original PKCE verifier.
    code_verifier = oauth_states.pop(state)

    if not code_verifier:
        raise HTTPException(
            status_code=400,
            detail="OAuth code verifier is missing. Please authorize again."
        )

    # Recreate the flow with the original verifier.
    flow = create_flow(
        state=state,
        code_verifier=code_verifier
    )

    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Google token exchange failed: {type(exc).__name__}"
        )

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
