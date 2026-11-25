"""
Firebase Authentication Integration Module.
Handles token verification, user synchronization, and client-side configuration.
"""

import os
import logging
import json
import threading

logger = logging.getLogger(__name__)

_firebase_init_lock = threading.Lock()


def init_firebase():
    """Initialize Firebase Admin SDK once."""
    try:
        import firebase_admin
        from firebase_admin import credentials

        project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
        with _firebase_init_lock:
            try:
                app = firebase_admin.get_app()
            except ValueError:
                app = None

            if app is None:
                cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY", "").strip()
                cred = None

                if cred_path:
                    if os.path.isfile(cred_path):
                        cred = credentials.Certificate(cred_path)
                    elif cred_path.startswith("{"):
                        cred = credentials.Certificate(json.loads(cred_path))
                    else:
                        raise FileNotFoundError("Firebase service account file was not found.")

                if cred:
                    credential_project_id = cred.project_id
                    if project_id and project_id != credential_project_id:
                        raise ValueError(
                            "Firebase Web project ID does not match the service account project ID."
                        )
                    project_id = project_id or credential_project_id

                options = {"projectId": project_id} if project_id else None
                try:
                    app = firebase_admin.initialize_app(cred, options=options)
                except ValueError:
                    app = firebase_admin.get_app()
            elif project_id and app.project_id and app.project_id != project_id:
                raise ValueError("Initialized Firebase project ID does not match FIREBASE_PROJECT_ID.")

        logger.info("Firebase Admin initialized for project: %s", app.project_id or "default")
        return True
    except Exception as e:
        logger.warning("Firebase Admin initialization failed: %s", e)
        return False


def verify_firebase_token(id_token: str) -> dict | None:
    """
    Verify a Firebase ID token using the Firebase Admin SDK.
    Returns the verified claims on success, None when verification fails.
    """
    if not id_token:
        return None

    try:
        if not init_firebase():
            return None

        import firebase_admin
        from firebase_admin import auth as fb_auth

        return fb_auth.verify_id_token(id_token, app=firebase_admin.get_app())
    except Exception as e:
        logger.info("Firebase ID token verification failed: %s", e)

    return None


def get_firebase_client_config() -> dict:
    """Return dictionary of client Firebase configuration."""
    return {
        "apiKey": os.getenv("FIREBASE_API_KEY", ""),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", ""),
        "projectId": os.getenv("FIREBASE_PROJECT_ID", ""),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId": os.getenv("FIREBASE_APP_ID", ""),
    }


def is_firebase_configured() -> bool:
    """Check whether sufficient Firebase settings exist to run the client SDK."""
    cfg = get_firebase_client_config()
    return bool(cfg["apiKey"] and cfg["authDomain"] and cfg["projectId"] and cfg["appId"])
