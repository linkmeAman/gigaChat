from fido2.webauthn import PublicKeyCredentialRpEntity, Fido2Server
from fido2.utils import websafe_decode, websafe_encode
from fido2.webauthn import AttestedCredentialData, AuthenticatorData, CollectedClientData
from app.core.config import settings
from app.models.auth import User, WebAuthnCredential
from sqlalchemy.orm import Session
import json
import secrets

rp = PublicKeyCredentialRpEntity(settings.PROJECT_NAME, settings.PROJECT_NAME)
server = Fido2Server(rp)

def generate_registration_options(user: User) -> dict:
    """Generate WebAuthn registration options for a user."""
    options = server.register_begin(
        {
            "id": str(user.id).encode(),
            "name": user.username,
            "displayName": user.email
        },
        [],
        user_verification="preferred"
    )
    
    return {
        "publicKey": {
            "challenge": websafe_encode(options.challenge),
            "rp": {
                "name": options.rp.name,
                "id": options.rp.id
            },
            "user": {
                "id": websafe_encode(options.user.id),
                "name": options.user.name,
                "displayName": options.user.display_name
            },
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},  # ES256
                {"type": "public-key", "alg": -257}  # RS256
            ],
            "timeout": 60000,
            "attestation": "none",
            "authenticatorSelection": {
                "authenticatorAttachment": "cross-platform",
                "userVerification": "preferred"
            }
        }
    }

def verify_registration(
    db: Session,
    user: User,
    client_data: dict,
    attestation_object: bytes
) -> WebAuthnCredential:
    """Verify WebAuthn registration response and store credential."""
    auth_data = server.register_complete(
        websafe_decode(client_data["challenge"]),
        CollectedClientData(json.dumps(client_data).encode()),
        attestation_object
    )
    
    credential = WebAuthnCredential(
        user_id=user.id,
        credential_id=websafe_encode(auth_data.credential_data.credential_id),
        public_key=websafe_encode(auth_data.credential_data.public_key),
        sign_count=auth_data.counter
    )
    
    db.add(credential)
    db.commit()
    db.refresh(credential)
    
    return credential

def generate_authentication_options(user: User, db: Session) -> dict:
    """Generate WebAuthn authentication options for a user."""
    credentials = db.query(WebAuthnCredential).filter(
        WebAuthnCredential.user_id == user.id
    ).all()
    
    allowed_credentials = [
        {
            "type": "public-key",
            "id": websafe_decode(cred.credential_id),
            "transports": ["usb", "nfc", "ble", "internal"]
        }
        for cred in credentials
    ]
    
    options = server.authenticate_begin(
        allowed_credentials,
        user_verification="preferred"
    )
    
    return {
        "publicKey": {
            "challenge": websafe_encode(options.challenge),
            "timeout": 60000,
            "rpId": options.rp_id,
            "allowCredentials": allowed_credentials,
            "userVerification": "preferred"
        }
    }

def verify_authentication(
    db: Session,
    credential_id: str,
    client_data: dict,
    auth_data: bytes,
    signature: bytes
) -> bool:
    """Verify WebAuthn authentication response."""
    credential = db.query(WebAuthnCredential).filter(
        WebAuthnCredential.credential_id == credential_id
    ).first()
    
    if not credential:
        return False
    
    auth_data = server.authenticate_complete(
        websafe_decode(credential.credential_id),
        websafe_decode(credential.public_key),
        credential.sign_count,
        websafe_decode(client_data["challenge"]),
        CollectedClientData(json.dumps(client_data).encode()),
        auth_data,
        signature
    )
    
    # Update sign count
    credential.sign_count = auth_data.counter
    db.commit()
    
    return True