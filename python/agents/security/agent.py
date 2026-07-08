"""
security/agent.py
Agent #21: SecurityAgent -- credential hygiene, real encryption, API key
management, and file integrity checks.

Practical scope, not the fictional 9-layer stack from the original
architecture doc (TPM attestation, blockchain verification, facial
recognition, etc. -- most of that is either hardware-specific,
enterprise-scale, or edges into surveillance territory that's out of
place in a personal assistant). This agent covers what actually matters
for a single-user local system: don't store secrets in plaintext, don't
let just anyone hit the API, and be able to tell if a file was tampered with.
"""

from __future__ import annotations
import base64
import hashlib
import hmac
import os
import re
import secrets
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    _HAS_CRYPTOGRAPHY = True
except ImportError:
    _HAS_CRYPTOGRAPHY = False


class SecurityAgent(BaseAgent):
    name = "security"
    description = (
        "Password strength checks, hashing, real AES encryption (via the `cryptography` "
        "library's Fernet), API key generation/verification for securing the REST API, "
        "and file integrity checks. Never stores plaintext secrets itself."
    )
    agent_id = 21

    def __init__(self):
        super().__init__()
        # In-memory API key store: {key_hash: label}. For real persistence,
        # back this with agents/memory (SQLite) -- kept separate here so a
        # memory-agent bug can never leak or corrupt security state.
        self._api_key_hashes: Dict[str, str] = {}

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("check_password_strength", "Score a password's strength", {"password": "str"}),
            AgentCapability("hash_value", "SHA-256 hash a string", {"value": "str"}),
            AgentCapability("derive_key", "Derive an AES key from a password + salt (PBKDF2)", {"password": "str", "salt": "str (optional, hex)"}),
            AgentCapability("encrypt", "Encrypt text with a password (AES via Fernet)", {"text": "str", "password": "str"}),
            AgentCapability("decrypt", "Decrypt text encrypted by `encrypt`", {"token": "str", "password": "str", "salt": "str"}),
            AgentCapability("generate_api_key", "Generate a new API key for securing the REST API", {"label": "str (optional, e.g. 'hologram-frontend')"}),
            AgentCapability("verify_api_key", "Check whether a given API key is valid", {"key": "str"}),
            AgentCapability("revoke_api_key", "Revoke a previously issued API key", {"key": "str"}),
            AgentCapability("file_checksum", "SHA-256 checksum a file, for integrity verification", {"path": "str"}),
            AgentCapability("verify_file_integrity", "Compare a file's current checksum against a known-good one", {"path": "str", "expected_sha256": "str"}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "hash_value":
            return {"sha256": hashlib.sha256(params["value"].encode()).hexdigest()}

        if action == "check_password_strength":
            return self._check_password_strength(params["password"])

        if action == "derive_key":
            return self._derive_key(params["password"], params.get("salt"))

        if action == "encrypt":
            return self._encrypt(params["text"], params["password"])

        if action == "decrypt":
            return self._decrypt(params["token"], params["password"], params["salt"])

        if action == "generate_api_key":
            return self._generate_api_key(params.get("label", "unlabeled"))

        if action == "verify_api_key":
            return {"valid": self._hash_key(params["key"]) in self._api_key_hashes}

        if action == "revoke_api_key":
            key_hash = self._hash_key(params["key"])
            existed = key_hash in self._api_key_hashes
            self._api_key_hashes.pop(key_hash, None)
            return {"revoked": existed}

        if action == "file_checksum":
            return self._file_checksum(params["path"])

        if action == "verify_file_integrity":
            result = self._file_checksum(params["path"])
            matches = hmac.compare_digest(result["sha256"], params["expected_sha256"])
            return {"path": params["path"], "matches": matches, "actual_sha256": result["sha256"]}

    # ---- password strength -------------------------------------------------
    def _check_password_strength(self, pw: str) -> Dict[str, Any]:
        checks = {
            "length_ok": len(pw) >= 12,
            "has_upper": bool(re.search(r"[A-Z]", pw)),
            "has_lower": bool(re.search(r"[a-z]", pw)),
            "has_digit": bool(re.search(r"\d", pw)),
            "has_symbol": bool(re.search(r"[^A-Za-z0-9]", pw)),
        }
        score = sum(checks.values())
        return {"score": score, "max_score": 5, "checks": checks, "strong": score >= 4}

    # ---- real encryption (AES via Fernet, key derived with PBKDF2) ------------------
    def _derive_key(self, password: str, salt_hex: str = None) -> Dict[str, Any]:
        if not _HAS_CRYPTOGRAPHY:
            return {"error": "cryptography not installed. Run: pip install cryptography"}
        salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=390_000)
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return {"key": key.decode(), "salt": salt.hex()}

    def _encrypt(self, text: str, password: str) -> Dict[str, Any]:
        if not _HAS_CRYPTOGRAPHY:
            return {"error": "cryptography not installed. Run: pip install cryptography"}
        derived = self._derive_key(password)
        fernet = Fernet(derived["key"].encode())
        token = fernet.encrypt(text.encode())
        return {"token": token.decode(), "salt": derived["salt"]}

    def _decrypt(self, token: str, password: str, salt_hex: str) -> Dict[str, Any]:
        if not _HAS_CRYPTOGRAPHY:
            return {"error": "cryptography not installed. Run: pip install cryptography"}
        derived = self._derive_key(password, salt_hex)
        fernet = Fernet(derived["key"].encode())
        plaintext = fernet.decrypt(token.encode())
        return {"text": plaintext.decode()}

    # ---- API key management ---------------------------------------------------
    def _hash_key(self, key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    def _generate_api_key(self, label: str) -> Dict[str, Any]:
        key = "jarvis_" + secrets.token_urlsafe(32)
        self._api_key_hashes[self._hash_key(key)] = label
        return {
            "key": key,
            "label": label,
            "note": "Store this now -- only the hash is kept, the raw key cannot be recovered later.",
        }

    # ---- file integrity ------------------------------------------------------
    def _file_checksum(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return {"path": path, "sha256": h.hexdigest(), "size_bytes": os.path.getsize(path)}
