from __future__ import annotations
import base64
import os
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"VC21A1\0"


def key_from_text(text: str) -> bytes:
    raw = base64.urlsafe_b64decode(text.strip().encode("ascii"))
    if len(raw) != 32:
        raise ValueError("VC21 key must decode to exactly 32 bytes")
    return raw


def encrypt_file(src: Path, dst: Path, key_text: str) -> None:
    key = key_from_text(key_text)
    nonce = os.urandom(12)
    data = src.read_bytes()
    ct = AESGCM(key).encrypt(nonce, data, MAGIC)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(MAGIC + nonce + ct)


def decrypt_file(src: Path, dst: Path, key_text: str) -> None:
    blob = src.read_bytes()
    if not blob.startswith(MAGIC) or len(blob) < len(MAGIC) + 12 + 16:
        raise ValueError(f"Invalid VASTcode21 encrypted payload: {src}")
    nonce = blob[len(MAGIC):len(MAGIC)+12]
    ct = blob[len(MAGIC)+12:]
    data = AESGCM(key_from_text(key_text)).decrypt(nonce, ct, MAGIC)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
