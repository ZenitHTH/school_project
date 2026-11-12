#!/usr/bin/env python3
"""Diagnose why Chulabook fetching fails on a specific machine (e.g. Linux Mint school PC).

Stdlib only — runs with the system python, no project import needed for the core checks.

Usage (on the machine that cannot fetch):
    python3 scripts/diagnose_chulabook.py [ISBN]
Example:
    python3 scripts/diagnose_chulabook.py 9786169444541

Copy the full output back to the developer. [FAIL] lines tell which layer
is blocking: proxy, DNS, TLS/CA certificates, or the API itself.
"""
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request

HOST = "api.chulabook.com"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
HEADERS = {
    "User-Agent": UA,
    "Origin": "https://www.chulabook.com",
    "Referer": "https://www.chulabook.com/",
}


def step(label, fn):
    t0 = time.time()
    try:
        print(f"[OK]   {label} ({time.time() - t0:.2f}s) — {fn()}")
        return True
    except Exception as exc:  # noqa: BLE001 — diagnostic reports every exception type
        print(f"[FAIL] {label} ({time.time() - t0:.2f}s) — {type(exc).__name__}: {exc}")
        return False


def main() -> int:
    isbn = sys.argv[1] if len(sys.argv) > 1 else "9786169444541"
    print(f"python {sys.version.split()[0]} | host={socket.gethostname()} | platform={sys.platform}")

    proxies = {k: v for k, v in os.environ.items() if "proxy" in k.lower()}
    print(f"proxy env vars: {proxies or 'none (direct connection; GNOME proxy settings are NOT read by Python)'}")

    def dns():
        infos = socket.getaddrinfo(HOST, 443)
        return f"resolved to {sorted(i[4][0] for i in infos)}"

    def tls():
        ctx = ssl.create_default_context()
        with socket.create_connection((HOST, 443), timeout=10) as raw:
            with ctx.wrap_socket(raw, server_hostname=HOST) as ssock:
                return f"TLS {ssock.version()} — system CA store verified api.chulabook.com OK"

    def http():
        url = f"https://{HOST}/products?search={isbn}&limit=5"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
            rows = data.get("rows") or []
            exact = next((r for r in rows if str(r.get("barcode", "")) == isbn), None)
            return f"HTTP {resp.status} count={data.get('count')} exact-barcode-match={'yes: id ' + str(exact.get('id')) if exact else 'no'}"

    ok = step(f"1. DNS lookup {HOST}", dns)
    ok &= step("2. TLS handshake (needs working system CA certificates)", tls)
    ok &= step("3. HTTP GET /products?search=<isbn> with app headers", http)

    if not ok:
        print("\nInterpretation:")
        print("  [FAIL] at 1 -> DNS broken on this machine (school DNS / no internet).")
        print("  [FAIL] at 2 -> missing/stale CA certificates (try: sudo apt install --reinstall ca-certificates && update-ca-certificates),")
        print("               or a MITM proxy intercepting TLS. Check GNOME Network -> Proxy settings:")
        print("               if the school uses a proxy, export it for Python: export https_proxy=http://<proxy>:<port>")
        print("  [FAIL] at 3 -> network reaches the API but the request failed: firewall rule, proxy env mismatch, or API outage.")
        print("               If a proxy IS required, set: export https_proxy=http://<proxy>:<port> then re-run.")
        return 1

    print("\nAll layers OK — the API is reachable from this machine.")
    print("If the app still cannot fetch, the installed app is an old build (pre-Chulabook provider): check app version >= 1.2.8.")
    return 0


if __name__ == "__main__":
    sys.exit(main())