from __future__ import annotations

import datetime as dt
import ipaddress
import json
import socket
import urllib.parse


def now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def decode_assets(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return []
    return decoded if isinstance(decoded, list) else []


def _is_private_host(hostname: str) -> bool:
    try:
        addr = ipaddress.ip_address(hostname)
    except ValueError:
        if hostname in ("localhost", "0.0.0.0"):
            return True
        try:
            resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
        except socket.gaierror:
            return False
        for family, _stype, _proto, _canon, sockaddr in resolved:
            ip_str = sockaddr[0]
            try:
                addr = ipaddress.ip_address(ip_str)
            except ValueError:
                continue
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
                return True
        return False
    return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved


def is_safe_fetch_url(url: str) -> bool:
    """Return True only for http/https URLs that do not resolve to private ranges."""
    try:
        parsed = urllib.parse.urlparse(url)
    except (ValueError, TypeError):
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname or ""
    if not hostname:
        return False
    return not _is_private_host(hostname)
