#!/usr/bin/env python3
"""Minimal SigV4 S3 helper for the isolated AI267 classroom MinIO service.

This helper intentionally uses only the Python standard library so that task
setup and cleanup do not depend on boto3 being installed on the workstation.
It is not part of a candidate solution.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ENDPOINT = os.environ.get(
    "AI267_S3_ENDPOINT", "https://minio-api-minio.apps.lab.example.com"
).rstrip("/")
ACCESS_KEY = os.environ.get("AI267_S3_ACCESS_KEY", "minio")
SECRET_KEY = os.environ.get("AI267_S3_SECRET_KEY", "minio123")
REGION = os.environ.get("AI267_S3_REGION", "us-east-1")
SERVICE = "s3"


def sign(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def signed_request(
    method: str,
    bucket: str,
    key: str = "",
    *,
    query: list[tuple[str, str]] | None = None,
    payload: bytes = b"",
) -> tuple[int, bytes]:
    parsed = urllib.parse.urlsplit(ENDPOINT)
    raw_path = f"/{bucket}"
    if key:
        raw_path += f"/{key.lstrip('/')}"
    canonical_uri = urllib.parse.quote(raw_path, safe="/-_.~")
    canonical_query = urllib.parse.urlencode(
        sorted(query or []), quote_via=urllib.parse.quote
    )
    payload_hash = hashlib.sha256(payload).hexdigest()
    now = dt.datetime.now(dt.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    canonical_headers = (
        f"host:{parsed.netloc}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join(
        (
            method,
            canonical_uri,
            canonical_query,
            canonical_headers,
            signed_headers,
            payload_hash,
        )
    )
    scope = f"{date_stamp}/{REGION}/{SERVICE}/aws4_request"
    string_to_sign = "\n".join(
        (
            "AWS4-HMAC-SHA256",
            amz_date,
            scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        )
    )
    date_key = sign(("AWS4" + SECRET_KEY).encode("utf-8"), date_stamp)
    region_key = sign(date_key, REGION)
    service_key = sign(region_key, SERVICE)
    signing_key = sign(service_key, "aws4_request")
    signature = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    authorization = (
        f"AWS4-HMAC-SHA256 Credential={ACCESS_KEY}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    url = f"{parsed.scheme}://{parsed.netloc}{canonical_uri}"
    if canonical_query:
        url += f"?{canonical_query}"
    request = urllib.request.Request(
        url,
        data=payload if method in {"PUT", "POST"} else None,
        method=method,
        headers={
            "Authorization": authorization,
            "Host": parsed.netloc,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        },
    )
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(request, context=context, timeout=30) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def require_success(status: int, body: bytes, expected: set[int]) -> None:
    if status not in expected:
        detail = body.decode("utf-8", errors="replace")
        raise SystemExit(f"S3 request failed with HTTP {status}: {detail}")


def bucket_exists(bucket: str) -> bool:
    status, body = signed_request("HEAD", bucket)
    if status == 404:
        return False
    require_success(status, body, {200})
    return True


def object_exists(bucket: str, key: str) -> bool:
    status, body = signed_request("HEAD", bucket, key)
    if status == 404:
        return False
    require_success(status, body, {200})
    return True


def list_keys(bucket: str) -> list[str]:
    keys: list[str] = []
    token = ""
    while True:
        query = [("list-type", "2")]
        if token:
            query.append(("continuation-token", token))
        status, body = signed_request("GET", bucket, query=query)
        if status == 404:
            return []
        require_success(status, body, {200})
        root = ET.fromstring(body)
        namespace = ""
        if root.tag.startswith("{"):
            namespace = root.tag.split("}", 1)[0] + "}"
        keys.extend(
            node.text or "" for node in root.findall(f"{namespace}Contents/{namespace}Key")
        )
        truncated = (root.findtext(f"{namespace}IsTruncated") or "false").lower()
        if truncated != "true":
            break
        token = root.findtext(f"{namespace}NextContinuationToken") or ""
        if not token:
            raise SystemExit("S3 listing was truncated without a continuation token")
    return keys


def delete_owned_bucket(bucket: str, owner_key: str, owner_path: str) -> None:
    """Delete a fixture bucket only when its random ownership object matches.

    A missing bucket is already clean.  A present bucket with a missing or
    different ownership object is deliberately left untouched.
    """

    expected = Path(owner_path).read_bytes()
    if not expected:
        raise SystemExit("S3 ownership token is empty")
    if not bucket_exists(bucket):
        return

    status, actual = signed_request("GET", bucket, owner_key)
    require_success(status, actual, {200})
    if not hmac.compare_digest(actual, expected):
        raise SystemExit(
            f"refusing to delete s3://{bucket}: ownership token does not match"
        )

    for key in list_keys(bucket):
        status, body = signed_request("DELETE", bucket, key)
        require_success(status, body, {200, 204, 404})
    status, body = signed_request("DELETE", bucket)
    require_success(status, body, {200, 204, 404})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=(
            "bucket-exists",
            "object-exists",
            "create-bucket",
            "delete-bucket",
            "download",
            "upload",
            "delete-object",
            "purge-bucket",
            "delete-owned-bucket",
        ),
    )
    parser.add_argument("bucket")
    parser.add_argument("key", nargs="?")
    parser.add_argument("path", nargs="?")
    args = parser.parse_args()

    if args.action == "bucket-exists":
        raise SystemExit(0 if bucket_exists(args.bucket) else 1)
    if args.action == "object-exists":
        if not args.key:
            parser.error("object-exists requires KEY")
        raise SystemExit(0 if object_exists(args.bucket, args.key) else 1)
    if args.action == "create-bucket":
        status, body = signed_request("PUT", args.bucket)
        require_success(status, body, {200, 204})
        return
    if args.action == "delete-bucket":
        status, body = signed_request("DELETE", args.bucket)
        require_success(status, body, {200, 204, 404})
        return
    if args.action == "download":
        if not args.key or not args.path:
            parser.error("download requires KEY PATH")
        status, body = signed_request("GET", args.bucket, args.key)
        require_success(status, body, {200})
        Path(args.path).write_bytes(body)
        return
    if args.action == "upload":
        if not args.key or not args.path:
            parser.error("upload requires KEY PATH")
        payload = Path(args.path).read_bytes()
        status, body = signed_request("PUT", args.bucket, args.key, payload=payload)
        require_success(status, body, {200, 204})
        return
    if args.action == "delete-object":
        if not args.key:
            parser.error("delete-object requires KEY")
        status, body = signed_request("DELETE", args.bucket, args.key)
        require_success(status, body, {200, 204, 404})
        return
    if args.action == "purge-bucket":
        if not bucket_exists(args.bucket):
            return
        for key in list_keys(args.bucket):
            status, body = signed_request("DELETE", args.bucket, key)
            require_success(status, body, {200, 204, 404})
        return
    if args.action == "delete-owned-bucket":
        if not args.key or not args.path:
            parser.error("delete-owned-bucket requires OWNER_KEY OWNER_TOKEN_PATH")
        delete_owned_bucket(args.bucket, args.key, args.path)
        return
    raise AssertionError(args.action)


if __name__ == "__main__":
    main()
