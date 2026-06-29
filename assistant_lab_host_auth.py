"""
Assistant Lab — verified host authorization for public chat servers.

Public servers (0.0.0.0) require a host key from the owner portal unless you are
the lab owner (ASSISTANT_LAB_ADMIN_PIN set).

Local testing on 127.0.0.1 does not require a host key.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from assistant_lab_data import get_admin_server_pin

DEFAULT_PORTAL_URL = "https://assistant-lab-host.onrender.com"
VALIDATE_TIMEOUT_SEC = 12


def get_portal_url() -> str:
    return os.environ.get("ASSISTANT_LAB_PORTAL_URL", DEFAULT_PORTAL_URL).rstrip("/")


def get_host_token() -> str:
    return os.environ.get("ASSISTANT_LAB_HOST_TOKEN", "").strip()


def is_local_bind(bind_host: str) -> bool:
    return bind_host in ("127.0.0.1", "localhost", "::1")


def is_owner_host() -> bool:
    return bool(get_admin_server_pin())


def validate_host_token(token: str, *, portal_url: str | None = None) -> tuple[bool, str]:
    """Check host key with the verification portal API."""
    token = (token or "").strip()
    if not token:
        return False, "Missing host key."
    base = (portal_url or get_portal_url()).rstrip("/")
    url = f"{base}/api/validate?{urllib.parse.urlencode({'token': token})}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AssistantLab-Host/1.0"})
        with urllib.request.urlopen(req, timeout=VALIDATE_TIMEOUT_SEC) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            return False, body.get("error", f"Portal rejected host key (HTTP {exc.code}).")
        except (json.JSONDecodeError, OSError):
            return False, f"Portal rejected host key (HTTP {exc.code})."
    except urllib.error.URLError as exc:
        return False, (
            f"Could not reach host portal ({base}). "
            f"Check internet or set ASSISTANT_LAB_PORTAL_URL. ({exc.reason})"
        )
    except (json.JSONDecodeError, OSError, TimeoutError) as exc:
        return False, f"Host portal check failed: {exc}"

    if not data.get("valid"):
        return False, data.get("error", "Host key is not valid.")
    name = data.get("server_name") or "Community Server"
    return True, f"Verified host: {name}"


def authorize_server_start(bind_host: str) -> tuple[bool, str]:
    """
    Return (ok, message) before binding a public chat server.

    - 127.0.0.1 / localhost: always OK (local testing)
    - Owner (ASSISTANT_LAB_ADMIN_PIN): OK, full admin
    - 0.0.0.0 / public: needs ASSISTANT_LAB_HOST_TOKEN verified by portal
    """
    if is_local_bind(bind_host):
        return True, "Local test server — no host key required."
    if is_owner_host():
        return True, "Lab owner server — admin enabled."
    token = get_host_token()
    if not token:
        return False, (
            "Public servers need a verified host key.\n"
            "  1. Verify your email at the Assistant Lab Host Portal\n"
            "  2. Copy your Host Key\n"
            "  3. Run: ASSISTANT_LAB_HOST_TOKEN=your_key ./run.sh server\n"
            f"  Portal: {get_portal_url()}"
        )
    return validate_host_token(token)