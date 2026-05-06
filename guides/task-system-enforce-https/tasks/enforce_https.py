import http.client
import ssl
from urllib.parse import urlparse


def compute_evidence():
    url = "<< config.url >>"
    parsed = urlparse(url if "://" in url else "http://" + url)
    host = parsed.netloc or parsed.path
    path = parsed.path if parsed.netloc else "/"
    if not path:
        path = "/"

    # Step 1: send plain HTTP request without following redirects
    http_enforced = False
    http_reason = ""
    try:
        conn = http.client.HTTPConnection(host, timeout=10)
        conn.request("GET", path)
        resp = conn.getresponse()
        conn.close()
        location = resp.getheader("Location", "")
        if resp.status in (301, 302, 307, 308) and location.lower().startswith(
            "https://"
        ):
            http_enforced = True
            http_reason = f"Plain HTTP returns {resp.status} → '{location}'"
        elif resp.status in (301, 302, 307, 308):
            http_reason = f"Plain HTTP returns {resp.status} but Location is not HTTPS: '{location}'"
        else:
            http_reason = f"Plain HTTP returned {resp.status} with no HTTPS redirect"
    except OSError:
        # Connection refused / reset → HTTP is blocked entirely
        http_enforced = True
        http_reason = (
            "Plain HTTP connection was refused (HTTP blocked at transport level)"
        )

    # Step 2: check HSTS header on the HTTPS endpoint
    hsts = False
    hsts_reason = ""
    try:
        ctx = ssl.create_default_context()
        conn = http.client.HTTPSConnection(host, context=ctx, timeout=10)
        conn.request("GET", path)
        resp = conn.getresponse()
        conn.close()
        sts = resp.getheader("Strict-Transport-Security", "")
        if sts:
            hsts = True
            hsts_reason = f"HSTS header present: '{sts}'"
        else:
            hsts_reason = "No HSTS header on HTTPS response"
    except Exception as e:
        hsts_reason = f"HTTPS check failed: {e}"

    enforces = http_enforced or hsts
    reason = f"HTTP check: {http_reason}. HSTS check: {hsts_reason}."
    return {"metrics": {"Enforces HTTPS": {"value": int(enforces), "reason": reason}}}
