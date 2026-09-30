"""Bounded, opt-in checks of public publication URLs.

Each DNS result is checked for a globally routable address, and the request
connects to that checked address. Redirects are checked anew. URL user-info and
query strings are rejected. These observations prove only what the HTTP
exchange showed; callers must separately bind the URL to the assessed dataset.
"""

from __future__ import annotations

import http.client
import ipaddress
import re
import socket
import ssl
from datetime import datetime, timezone
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

_MAX_REDIRECTS = 3
_MAX_BODY = 65_536
_TIMEOUT_SECONDS = 6


class PublicURLRequired(ValueError):
    """The supplied URL is unsuitable for a public network probe."""


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, address: str, port: int):
        super().__init__(host, port=port, timeout=_TIMEOUT_SECONDS)
        self._checked_address = address

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self._checked_address, self.port), timeout=self.timeout
        )


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, port: int):
        super().__init__(
            host, port=port, timeout=_TIMEOUT_SECONDS, context=ssl.create_default_context()
        )
        self._checked_address = address

    def connect(self) -> None:
        plain = socket.create_connection((self._checked_address, self.port), timeout=self.timeout)
        self.sock = self._context.wrap_socket(plain, server_hostname=self.host)


def _safe_url(value: str) -> tuple[str, str, int, str]:
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise PublicURLRequired("publication URL must not contain control characters")
    if len(value) > 2048:
        raise PublicURLRequired("publication URL is too long")
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise PublicURLRequired("publication URL must be HTTP or HTTPS")
    if parsed.username or parsed.password:
        raise PublicURLRequired("publication URL must not contain credentials")
    if parsed.query:
        raise PublicURLRequired("publication URL must not contain a query string")
    try:
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    except ValueError as error:
        raise PublicURLRequired("publication URL has an invalid port") from error
    if port != (443 if parsed.scheme.lower() == "https" else 80):
        raise PublicURLRequired("publication URL must use the standard HTTP or HTTPS port")
    host = parsed.hostname.rstrip(".").lower()
    if not host or host == "localhost":
        raise PublicURLRequired("publication URL must use a public host")
    clean = urlunsplit((parsed.scheme.lower(), parsed.netloc, parsed.path or "/", parsed.query, ""))
    return clean, host, port, parsed.scheme.lower()


def matching_declared_doi(value: str, declared_identifiers: list[str]) -> str | None:
    """Return a dataset DOI only when its exact resolver URL was supplied."""
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https" or (parsed.hostname or "").lower() != "doi.org":
        return None
    if parsed.query or parsed.username or parsed.password or parsed.port not in {None, 443}:
        return None
    doi_in_url = unquote(parsed.path).lstrip("/").lower()
    for identifier in declared_identifiers:
        candidate = identifier.lower().strip()
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if candidate.startswith(prefix):
                candidate = candidate[len(prefix) :]
                break
        if candidate.startswith("10.") and candidate == doi_in_url:
            return identifier
    return None


def bound_doi_url(value: str, declared_identifiers: list[str]) -> bool:
    """True only for the DOI resolver URL of a locally declared dataset DOI."""
    return matching_declared_doi(value, declared_identifiers) is not None


def _public_address(host: str, port: int) -> str:
    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as error:
        raise PublicURLRequired("publication host could not be resolved") from error
    addresses = [record[4][0] for record in records]
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise PublicURLRequired("publication host resolves to a non-public address")
    return addresses[0]


def _fetch_once(value: str) -> dict[str, Any]:
    clean, host, port, scheme = _safe_url(value)
    address = _public_address(host, port)
    parsed = urlsplit(clean)
    target = (parsed.path or "/") + (f"?{parsed.query}" if parsed.query else "")
    connection = (
        _PinnedHTTPSConnection(host, address, port)
        if scheme == "https"
        else _PinnedHTTPConnection(host, address, port)
    )
    try:
        connection.request(
            "GET",
            target,
            headers={
                "Host": parsed.netloc,
                "User-Agent": "Data2Agent-FAIR/0.1",
                "Accept": "text/html,application/json,*/*",
                "Range": f"bytes=0-{_MAX_BODY - 1}",
                "Connection": "close",
            },
        )
        response = connection.getresponse()
        body = response.read(_MAX_BODY)
        return {
            "url": clean,
            "status_code": response.status,
            "location": response.getheader("Location"),
            "content_type": response.getheader("Content-Type"),
            "body_sample": body.decode("utf-8", errors="replace"),
        }
    finally:
        connection.close()


def probe_public_url(value: str, *, expected_identifier: str | None = None) -> dict[str, Any]:
    """Observe a public HTTP route without claiming dataset identity from status alone."""
    clean, _, _, _ = _safe_url(value)
    observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    chain: list[dict[str, Any]] = []
    current = clean
    try:
        for _ in range(_MAX_REDIRECTS + 1):
            response = _fetch_once(current)
            chain.append(
                {
                    key: response[key]
                    for key in ("url", "status_code", "location", "content_type")
                }
            )
            if response["status_code"] in {301, 302, 303, 307, 308}:
                location = response["location"]
                if not location:
                    break
                current = urljoin(current, location)
                _safe_url(current)
                continue
            break
    except (OSError, ssl.SSLError, http.client.HTTPException) as error:
        return {
            "method": "bounded-public-http-get",
            "source": clean,
            "observed_at": observed_at,
            "result": "network_error",
            "error_type": type(error).__name__,
            "chain": chain,
        }
    final = response if chain else None
    reached = bool(final and 200 <= final["status_code"] < 300)
    identifier_seen = bool(
        reached
        and expected_identifier
        and re.search(
            rf"(?<![A-Za-z0-9._/-]){re.escape(expected_identifier)}(?![A-Za-z0-9._/-])",
            final["body_sample"],
            flags=re.IGNORECASE,
        )
    )
    return {
        "method": "bounded-public-http-get",
        "source": clean,
        "observed_at": observed_at,
        "result": "reached" if reached else "not_reached",
        "final_url": final["url"] if final else None,
        "status_code": final["status_code"] if final else None,
        "identifier_seen_in_sample": identifier_seen,
        "body_sample_bytes": (
            min(len(final["body_sample"].encode("utf-8")), _MAX_BODY) if final else 0
        ),
        "chain": chain,
    }
