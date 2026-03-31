#!/usr/bin/env python3
"""
Etsy OAuth 2.0 Authentication Script
=====================================
Guides the user through Etsy's OAuth 2.0 flow to obtain and store access tokens.

Usage:
    python etsy_auth.py              # Start OAuth flow
    python etsy_auth.py --refresh    # Refresh existing token
"""

import os
import sys
import json
import hashlib
import secrets
import string
import base64
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' package is required. Install with: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ETSY_AUTH_URL = "https://www.etsy.com/oauth/connect"
ETSY_TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = "listings_w listings_r shops_r"  # Required scopes for listing management

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
GITIGNORE_FILE = PROJECT_ROOT / ".gitignore"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _generate_pkce_pair():
    """Generate a PKCE code_verifier and code_challenge (S256)."""
    code_verifier = "".join(
        secrets.choice(string.ascii_letters + string.digits + "-._~")
        for _ in range(128)
    )
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def _read_env() -> dict:
    """Read existing .env file into a dict."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip().strip("\"'")
    return env


def _write_env(env: dict):
    """Write dict back to .env, preserving comments for known keys."""
    lines = []
    for key, value in sorted(env.items()):
        lines.append(f'{key}={value}')
    ENV_FILE.write_text("\n".join(lines) + "\n")
    print(f"[OK] Tokens saved to {ENV_FILE}")


def _ensure_gitignore():
    """Make sure .env is listed in .gitignore."""
    if GITIGNORE_FILE.exists():
        content = GITIGNORE_FILE.read_text()
        if ".env" not in content.splitlines():
            with open(GITIGNORE_FILE, "a") as f:
                f.write("\n.env\n")
            print("[OK] Added .env to .gitignore")
    else:
        GITIGNORE_FILE.write_text(".env\n")
        print("[OK] Created .gitignore with .env entry")


# ---------------------------------------------------------------------------
# OAuth callback server
# ---------------------------------------------------------------------------
class _CallbackHandler(BaseHTTPRequestHandler):
    """Tiny HTTP handler that captures the OAuth callback."""

    auth_code = None
    state_received = None

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        _CallbackHandler.auth_code = params.get("code", [None])[0]
        _CallbackHandler.state_received = params.get("state", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        body = (
            "<html><body><h2>Authorization successful!</h2>"
            "<p>You can close this tab and return to the terminal.</p>"
            "</body></html>"
        )
        self.wfile.write(body.encode())

    def log_message(self, format, *args):
        pass  # Suppress default logging


# ---------------------------------------------------------------------------
# Core auth functions
# ---------------------------------------------------------------------------
def start_oauth_flow(api_key: str) -> dict:
    """
    Run the full OAuth 2.0 + PKCE flow.
    Returns dict with access_token, refresh_token, expires_in.
    """
    state = secrets.token_urlsafe(16)
    code_verifier, code_challenge = _generate_pkce_pair()

    params = {
        "response_type": "code",
        "client_id": api_key,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    auth_url = f"{ETSY_AUTH_URL}?{urlencode(params)}"
    print("\n=== Etsy OAuth 2.0 Authorization ===\n")
    print("Opening browser for authorization...")
    print(f"If the browser does not open, visit this URL manually:\n\n{auth_url}\n")
    webbrowser.open(auth_url)

    # Start local server to capture the callback
    server = HTTPServer(("localhost", 8080), _CallbackHandler)
    print("Waiting for authorization callback on http://localhost:8080 ...")
    server.handle_request()  # Handle single request
    server.server_close()

    if not _CallbackHandler.auth_code:
        raise RuntimeError("No authorization code received.")

    if _CallbackHandler.state_received != state:
        raise RuntimeError("State mismatch — possible CSRF attack.")

    print("[OK] Authorization code received. Exchanging for tokens...")

    # Exchange authorization code for tokens
    token_data = {
        "grant_type": "authorization_code",
        "client_id": api_key,
        "redirect_uri": REDIRECT_URI,
        "code": _CallbackHandler.auth_code,
        "code_verifier": code_verifier,
    }
    resp = requests.post(ETSY_TOKEN_URL, data=token_data, timeout=30)
    resp.raise_for_status()
    tokens = resp.json()

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "expires_in": tokens.get("expires_in", 3600),
    }


def refresh_access_token(api_key: str, refresh_token: str) -> dict:
    """
    Refresh an expired access token using the refresh token.
    Returns dict with new access_token, refresh_token, expires_in.
    """
    print("\n=== Refreshing Etsy Access Token ===\n")
    data = {
        "grant_type": "refresh_token",
        "client_id": api_key,
        "refresh_token": refresh_token,
    }
    resp = requests.post(ETSY_TOKEN_URL, data=data, timeout=30)
    if resp.status_code != 200:
        print(f"[ERROR] Token refresh failed: {resp.status_code} {resp.text}")
        raise RuntimeError("Token refresh failed. You may need to re-authorize.")
    tokens = resp.json()
    print("[OK] Token refreshed successfully.")
    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "expires_in": tokens.get("expires_in", 3600),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    env = _read_env()
    api_key = os.environ.get("ETSY_API_KEY") or env.get("ETSY_API_KEY")

    if not api_key:
        print("Error: ETSY_API_KEY not found.")
        print("Set it in your environment or in the .env file.")
        sys.exit(1)

    if "--refresh" in sys.argv:
        refresh_token = os.environ.get("ETSY_REFRESH_TOKEN") or env.get("ETSY_REFRESH_TOKEN")
        if not refresh_token:
            print("Error: No refresh token found. Run without --refresh to authorize first.")
            sys.exit(1)
        tokens = refresh_access_token(api_key, refresh_token)
    else:
        tokens = start_oauth_flow(api_key)

    # Save tokens to .env
    env["ETSY_API_KEY"] = api_key
    env["ETSY_ACCESS_TOKEN"] = tokens["access_token"]
    env["ETSY_REFRESH_TOKEN"] = tokens["refresh_token"]

    # Preserve other keys that may already exist
    _write_env(env)
    _ensure_gitignore()

    print("\nDone! You can now run etsy_uploader.py to upload listings.")


if __name__ == "__main__":
    main()
