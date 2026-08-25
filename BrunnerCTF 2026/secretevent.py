import base64
import hashlib
import hmac
import json
import time


def base64url_encode(data: bytes) -> str:
    """Base64url encode without padding, as required by JWT spec."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def base64url_decode(data: str) -> bytes:
    """Base64url decode, adding back padding if needed."""
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def sign_jwt(payload: dict, secret: str, header: dict = None) -> str:
    """Create an HS256-signed JWT."""
    if header is None:
        header = {"alg": "HS256", "typ": "JWT"}

    # Encode header and payload as compact JSON, then base64url
    encoded_header = base64url_encode(
        json.dumps(header, separators=(',', ':')).encode('utf-8')
    )
    encoded_payload = base64url_encode(
        json.dumps(payload, separators=(',', ':')).encode('utf-8')
    )

    signing_input = f"{encoded_header}.{encoded_payload}".encode('utf-8')

    # HMAC-SHA256 signature
    signature = hmac.new(
        secret.encode('utf-8'),
        signing_input,
        hashlib.sha256
    ).digest()
    encoded_signature = base64url_encode(signature)

    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def verify_jwt(token: str, secret: str) -> dict:
    """Verify an HS256 JWT and return the decoded payload if valid."""
    try:
        encoded_header, encoded_payload, encoded_signature = token.split('.')
    except ValueError:
        raise ValueError("Invalid token format")

    signing_input = f"{encoded_header}.{encoded_payload}".encode('utf-8')

    expected_signature = hmac.new(
        secret.encode('utf-8'),
        signing_input,
        hashlib.sha256
    ).digest()
    expected_encoded_signature = base64url_encode(expected_signature)

    # Constant-time comparison to avoid timing attacks
    if not hmac.compare_digest(encoded_signature, expected_encoded_signature):
        raise ValueError("Invalid signature")

    payload = json.loads(base64url_decode(encoded_payload))

    # Check expiry if present
    if 'exp' in payload and time.time() > payload['exp']:
        raise ValueError("Token has expired")

    return payload


if __name__ == "__main__":
    secret = "secret" 

    payload = {
    "user": "Mikayn",
    "role": "commissioner"
    }

    token = sign_jwt(payload, secret)
    print("Token:", token)

    decoded = verify_jwt(token, secret)
    print("Decoded:", decoded)