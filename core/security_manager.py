"""
Qubinode Navigator Security Manager

Comprehensive security hardening and access control system
for deployment operations and infrastructure management.

Based on ADR-0024, ADR-0025: Security Architecture and Hardening
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import secrets
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import bcrypt
import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecurityLevel(Enum):
    """Security levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AccessLevel(Enum):
    """Access levels for RBAC"""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class VulnerabilityType(Enum):
    """Types of security vulnerabilities"""

    CREDENTIAL_EXPOSURE = "credential_exposure"
    WEAK_AUTHENTICATION = "weak_authentication"
    INSECURE_COMMUNICATION = "insecure_communication"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    CODE_INJECTION = "code_injection"
    PATH_TRAVERSAL = "path_traversal"
    WEAK_ENCRYPTION = "weak_encryption"
    OUTDATED_DEPENDENCIES = "outdated_dependencies"


@dataclass
class SecurityVulnerability:
    """Security vulnerability definition"""

    vulnerability_id: str
    vulnerability_type: VulnerabilityType
    severity: SecurityLevel
    title: str
    description: str
    affected_components: List[str]
    remediation_steps: List[str]
    detected_at: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class AccessToken:
    """Access token for authentication"""

    token_id: str
    user_id: str
    access_level: AccessLevel
    permissions: List[str]
    issued_at: datetime
    expires_at: datetime
    last_used: Optional[datetime] = None
    revoked: bool = False


@dataclass
class SecurityAuditLog:
    """Security audit log entry"""

    log_id: str
    event_type: str
    user_id: Optional[str]
    resource: str
    action: str
    result: str  # success, failure, denied
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    additional_data: Dict[str, Any] = None


class SecurityManager:
    """
    Comprehensive Security Manager

    Provides security hardening, access control, vulnerability scanning,
    and audit logging for deployment operations.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Configuration
        self.security_level = SecurityLevel(self.config.get("security_level", "high"))
        self.vault_integration = self.config.get("vault_integration", True)
        self.audit_logging = self.config.get("audit_logging", True)
        self.token_expiry_hours = self.config.get("token_expiry_hours", 24)

        # Storage paths
        self.security_storage_path = Path(
            self.config.get("security_storage_path", "data/security")
        )
        self.audit_log_path = Path(
            self.config.get("audit_log_path", "data/security/audit.log")
        )
        self.credentials_path = Path(
            self.config.get("credentials_path", "data/security/credentials")
        )

        # Initialize storage
        self.security_storage_path.mkdir(parents=True, exist_ok=True)
        self.credentials_path.mkdir(parents=True, exist_ok=True)

        # Security state
        self.active_tokens: Dict[str, AccessToken] = {}
        self.security_vulnerabilities: List[SecurityVulnerability] = []
        self.audit_logs: List[SecurityAuditLog] = []

        # Encryption
        self.encryption_key = self._initialize_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)

        # JWT secret
        self.jwt_secret = self._initialize_jwt_secret()

        # Security patterns
        self.sensitive_patterns = self._load_sensitive_patterns()

        # Load existing data
        self._load_security_data()

    def _initialize_encryption_key(self) -> bytes:
        """Initialize or load encryption key"""
        key_file = self.security_storage_path / "encryption.key"

        if key_file.exists():
            with open(key_file, "rb") as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Restrict permissions
            return key

    def _initialize_jwt_secret(self) -> str:
        """Initialize or load JWT secret"""
        secret_file = self.security_storage_path / "jwt.secret"

        if secret_file.exists():
            with open(secret_file, "r") as f:
                return f.read().strip()
        else:
            # Generate new secret
            secret = secrets.token_urlsafe(32)
            with open(secret_file, "w") as f:
                f.write(secret)
            os.chmod(secret_file, 0o600)
            return secret

    def _load_sensitive_patterns(self) -> List[str]:
        """Load patterns for detecting sensitive information"""
        return [
            # API Keys and tokens
            r'(?i)(api[_-]?key|token|secret)["\s]*[:=]["\s]*([a-zA-Z0-9_\-]{20,})',
            # Passwords
            r'(?i)(password|passwd|pwd)["\s]*[:=]["\s]*["\']([^"\']{8,})["\']',
            # SSH Keys
            r"-----BEGIN [A-Z ]+PRIVATE KEY-----",
            # Database URLs
            r"(?i)(mongodb|mysql|postgresql|redis)://[^:\s]+:[^@\s]+@[^\s]+",
            # AWS credentials
            r"(?i)(aws[_-]?access[_-]?key[_-]?id|aws[_-]?secret[_-]?access[_-]?key)",
            # Generic secrets
            r"(?i)(client[_-]?secret|private[_-]?key|encryption[_-]?key)",
            # IP addresses (private ranges)
            r"(?:10\.|172\.(?:1[6-9]|2[0-9]|3[01])\.|192\.168\.)\d{1,3}\.\d{1,3}",
            # Email addresses
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        ]

    def _load_security_data(self):
        """Load existing security data"""
        try:
            # Load vulnerabilities
            vuln_file = self.security_storage_path / "vulnerabilities.json"
            if vuln_file.exists():
                with open(vuln_file, "r") as f:
                    vuln_data = json.load(f)
                    self.security_vulnerabilities = [
                        self._deserialize_vulnerability(v) for v in vuln_data
                    ]

            # Load audit logs (recent only)
            if self.audit_log_path.exists():
                self._load_recent_audit_logs()

            self.logger.info(
                f"Loaded {len(self.security_vulnerabilities)} vulnerabilities and {len(self.audit_logs)} audit logs"
            )

        except Exception as e:
            self.logger.error(f"Failed to load security data: {e}")

    def _load_recent_audit_logs(self):
        """Load recent audit logs"""
        try:
            with open(self.audit_log_path, "r") as f:
                lines = f.readlines()
                # Load last 1000 lines
                for line in lines[-1000:]:
                    try:
                        log_data = json.loads(line.strip())
                        audit_log = self._deserialize_audit_log(log_data)
                        self.audit_logs.append(audit_log)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            self.logger.error(f"Failed to load audit logs: {e}")

    def _save_security_data(self):
        """Save security data to storage"""
        try:
            # Save vulnerabilities
            vuln_file = self.security_storage_path / "vulnerabilities.json"
            vuln_data = [
                self._serialize_vulnerability(v) for v in self.security_vulnerabilities
            ]
            with open(vuln_file, "w") as f:
                json.dump(vuln_data, f, indent=2, default=str)

            self.logger.debug("Saved security data")

        except Exception as e:
            self.logger.error(f"Failed to save security data: {e}")

    def _serialize_vulnerability(self, vuln: SecurityVulnerability) -> Dict[str, Any]:
        """Serialize vulnerability to JSON format"""
        data = asdict(vuln)
        data["vulnerability_type"] = vuln.vulnerability_type.value
        data["severity"] = vuln.severity.value
        data["detected_at"] = vuln.detected_at.isoformat()
        data["resolved_at"] = vuln.resolved_at.isoformat() if vuln.resolved_at else None
        return data

    def _deserialize_vulnerability(self, data: Dict[str, Any]) -> SecurityVulnerability:
        """Deserialize vulnerability from JSON format"""
        return SecurityVulnerability(
            vulnerability_id=data["vulnerability_id"],
            vulnerability_type=VulnerabilityType(data["vulnerability_type"]),
            severity=SecurityLevel(data["severity"]),
            title=data["title"],
            description=data["description"],
            affected_components=data["affected_components"],
            remediation_steps=data["remediation_steps"],
            detected_at=datetime.fromisoformat(data["detected_at"]),
            resolved=data["resolved"],
            resolved_at=(
                datetime.fromisoformat(data["resolved_at"])
                if data.get("resolved_at")
                else None
            ),
        )

    def _serialize_audit_log(self, log: SecurityAuditLog) -> Dict[str, Any]:
        """Serialize audit log to JSON format"""
        data = asdict(log)
        data["timestamp"] = log.timestamp.isoformat()
        return data

    def _deserialize_audit_log(self, data: Dict[str, Any]) -> SecurityAuditLog:
        """Deserialize audit log from JSON format"""
        return SecurityAuditLog(
            log_id=data["log_id"],
            event_type=data["event_type"],
            user_id=data.get("user_id"),
            resource=data["resource"],
            action=data["action"],
            result=data["result"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            additional_data=data.get("additional_data", {}),
        )

    # Authentication and Authorization

    def generate_access_token(
        self, user_id: str, access_level: AccessLevel, permissions: List[str] = None
    ) -> AccessToken:
        """Generate access token for user"""

        token_id = secrets.token_urlsafe(32)
        issued_at = datetime.now()
        expires_at = issued_at + timedelta(hours=self.token_expiry_hours)

        token = AccessToken(
            token_id=token_id,
            user_id=user_id,
            access_level=access_level,
            permissions=permissions or [],
            issued_at=issued_at,
            expires_at=expires_at,
        )

        self.active_tokens[token_id] = token

        # Create JWT
        jwt_payload = {
            "token_id": token_id,
            "user_id": user_id,
            "access_level": access_level.value,
            "permissions": permissions or [],
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
        }

        jwt_token = jwt.encode(jwt_payload, self.jwt_secret, algorithm="HS256")

        # Log token generation
        self.log_security_event(
            event_type="token_generated",
            user_id=user_id,
            resource="authentication",
            action="generate_token",
            result="success",
            additional_data={"access_level": access_level.value},
        )

        return token, jwt_token

    def validate_access_token(self, jwt_token: str) -> Optional[AccessToken]:
        """Validate JWT access token"""

        try:
            payload = jwt.decode(jwt_token, self.jwt_secret, algorithms=["HS256"])
            token_id = payload["token_id"]

            if token_id not in self.active_tokens:
                return None

            token = self.active_tokens[token_id]

            # Check if token is expired or revoked
            if token.revoked or datetime.now() > token.expires_at:
                if token_id in self.active_tokens:
                    del self.active_tokens[token_id]
                return None

            # Update last used
            token.last_used = datetime.now()

            return token

        except jwt.InvalidTokenError:
            return None

    def revoke_access_token(self, token_id: str, user_id: str = None) -> bool:
        """Revoke access token"""

        if token_id in self.active_tokens:
            token = self.active_tokens[token_id]
            token.revoked = True

            # Log token revocation
            self.log_security_event(
                event_type="token_revoked",
                user_id=user_id or token.user_id,
                resource="authentication",
                action="revoke_token",
                result="success",
                additional_data={"token_id": token_id},
            )

            return True

        return False

    def check_permission(self, token: AccessToken, required_permission: str) -> bool:
        """Check if token has required permission"""

        # Super admin has all permissions
        if token.access_level == AccessLevel.SUPER_ADMIN:
            return True

        # Check specific permissions
        if required_permission in token.permissions:
            return True

        # Check access level permissions
        access_level_permissions = {
            AccessLevel.READ: ["read"],
            AccessLevel.WRITE: ["read", "write"],
            AccessLevel.ADMIN: ["read", "write", "admin"],
            AccessLevel.SUPER_ADMIN: ["read", "write", "admin", "super_admin"],
        }

        allowed_permissions = access_level_permissions.get(token.access_level, [])
        return required_permission in allowed_permissions

    # Vulnerability Scanning

    async def scan_for_vulnerabilities(
        self, scan_paths: List[str] = None
    ) -> List[SecurityVulnerability]:
        """Scan for security vulnerabilities"""

        vulnerabilities = []
        scan_paths = scan_paths or ["."]

        for scan_path in scan_paths:
            path = Path(scan_path)
            if not path.exists():
                continue

            # Scan files for sensitive information
            if path.is_file():
                file_vulns = await self._scan_file_for_vulnerabilities(path)
                vulnerabilities.extend(file_vulns)
            else:
                # Scan directory recursively
                for file_path in path.rglob("*"):
                    if file_path.is_file() and not self._should_skip_file(file_path):
                        file_vulns = await self._scan_file_for_vulnerabilities(
                            file_path
                        )
                        vulnerabilities.extend(file_vulns)

        # Scan for system vulnerabilities
        system_vulns = await self._scan_system_vulnerabilities()
        vulnerabilities.extend(system_vulns)

        # Add new vulnerabilities
        for vuln in vulnerabilities:
            if not any(
                v.vulnerability_id == vuln.vulnerability_id
                for v in self.security_vulnerabilities
            ):
                self.security_vulnerabilities.append(vuln)

        # Save vulnerabilities
        self._save_security_data()

        self.logger.info(
            f"Vulnerability scan completed: {len(vulnerabilities)} new vulnerabilities found"
        )

        return vulnerabilities

    async def _scan_file_for_vulnerabilities(
        self, file_path: Path
    ) -> List[SecurityVulnerability]:
        """Scan individual file for vulnerabilities"""

        vulnerabilities = []

        try:
            # Read file content
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Scan for sensitive patterns
            for i, pattern in enumerate(self.sensitive_patterns):
                matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)

                for match in matches:
                    vuln_id = (
                        f"cred_exposure_{file_path.name}_{i}_{hash(match.group())}"
                    )

                    vulnerability = SecurityVulnerability(
                        vulnerability_id=vuln_id,
                        vulnerability_type=VulnerabilityType.CREDENTIAL_EXPOSURE,
                        severity=SecurityLevel.HIGH,
                        title=f"Potential sensitive information in {file_path.name}",
                        description=f"Detected pattern that may contain sensitive information: {match.group()[:50]}...",
                        affected_components=[str(file_path)],
                        remediation_steps=[
                            "Review the detected content for sensitive information",
                            "Move sensitive data to environment variables or vault",
                            "Add file to .gitignore if it contains secrets",
                            "Use proper secret management tools",
                        ],
                        detected_at=datetime.now(),
                    )

                    vulnerabilities.append(vulnerability)

            # Check file permissions
            if file_path.stat().st_mode & 0o077:  # World or group readable
                vuln_id = f"file_permissions_{file_path.name}_{hash(str(file_path))}"

                vulnerability = SecurityVulnerability(
                    vulnerability_id=vuln_id,
                    vulnerability_type=VulnerabilityType.WEAK_AUTHENTICATION,
                    severity=SecurityLevel.MEDIUM,
                    title=f"Insecure file permissions: {file_path.name}",
                    description=f"File has overly permissive permissions: {oct(file_path.stat().st_mode)[-3:]}",
                    affected_components=[str(file_path)],
                    remediation_steps=[
                        f"Change file permissions: chmod 600 {file_path}",
                        "Review file content for sensitive information",
                        "Ensure only necessary users have access",
                    ],
                    detected_at=datetime.now(),
                )

                vulnerabilities.append(vulnerability)

        except Exception as e:
            self.logger.error(f"Failed to scan file {file_path}: {e}")

        return vulnerabilities

    async def _scan_system_vulnerabilities(self) -> List[SecurityVulnerability]:
        """Scan for system-level vulnerabilities"""

        vulnerabilities = []

        # Check for outdated packages (example for RHEL/CentOS)
        try:
            result = subprocess.run(
                ["dnf", "check-update"], capture_output=True, text=True, timeout=30
            )

            if result.returncode == 100:  # Updates available
                vuln_id = f"outdated_packages_{int(time.time())}"

                vulnerability = SecurityVulnerability(
                    vulnerability_id=vuln_id,
                    vulnerability_type=VulnerabilityType.OUTDATED_DEPENDENCIES,
                    severity=SecurityLevel.MEDIUM,
                    title="Outdated system packages detected",
                    description="System has outdated packages that may contain security vulnerabilities",
                    affected_components=["system_packages"],
                    remediation_steps=[
                        "Run 'dnf update' to update system packages",
                        "Review security advisories for critical updates",
                        "Schedule regular system updates",
                    ],
                    detected_at=datetime.now(),
                )

                vulnerabilities.append(vulnerability)

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # Skip if dnf not available or times out

        return vulnerabilities

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during scanning"""

        skip_extensions = {
            ".pyc",
            ".pyo",
            ".so",
            ".dylib",
            ".dll",
            ".exe",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".pdf",
            ".zip",
            ".tar",
            ".gz",
        }
        skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv"}

        # Skip binary files
        if file_path.suffix.lower() in skip_extensions:
            return True

        # Skip files in excluded directories
        if any(part in skip_dirs for part in file_path.parts):
            return True

        # Skip large files (> 10MB)
        try:
            if file_path.stat().st_size > 10 * 1024 * 1024:
                return True
        except OSError:
            return True

        return False

    # Encryption and Secure Storage

    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        encrypted_data = self.cipher_suite.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
        return decrypted_data.decode()

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

    def secure_delete_file(self, file_path: Path) -> bool:
        """Securely delete file by overwriting"""

        try:
            if not file_path.exists():
                return True

            # Get file size
            file_size = file_path.stat().st_size

            # Overwrite with random data multiple times
            with open(file_path, "r+b") as f:
                for _ in range(3):  # 3 passes
                    f.seek(0)
                    f.write(secrets.token_bytes(file_size))
                    f.flush()
                    os.fsync(f.fileno())

            # Remove file
            file_path.unlink()

            return True

        except Exception as e:
            self.logger.error(f"Failed to securely delete {file_path}: {e}")
            return False

    # Audit Logging

    def log_security_event(
        self,
        event_type: str,
        user_id: Optional[str],
        resource: str,
        action: str,
        result: str,
        ip_address: str = None,
        user_agent: str = None,
        additional_data: Dict[str, Any] = None,
    ):
        """Log security event"""

        if not self.audit_logging:
            return

        log_id = secrets.token_urlsafe(16)

        audit_log = SecurityAuditLog(
            log_id=log_id,
            event_type=event_type,
            user_id=user_id,
            resource=resource,
            action=action,
            result=result,
            timestamp=datetime.now(),
            ip_address=ip_address,
            user_agent=user_agent,
            additional_data=additional_data or {},
        )

        # Add to memory
        self.audit_logs.append(audit_log)

        # Write to file
        try:
            log_data = self._serialize_audit_log(audit_log)
            with open(self.audit_log_path, "a") as f:
                f.write(json.dumps(log_data, default=str) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write audit log: {e}")

    # Security Analysis and Reporting

    def get_security_summary(self) -> Dict[str, Any]:
        """Get security summary"""

        # Count vulnerabilities by severity
        vuln_counts = {}
        for severity in SecurityLevel:
            vuln_counts[severity.value] = len(
                [
                    v
                    for v in self.security_vulnerabilities
                    if v.severity == severity and not v.resolved
                ]
            )

        # Recent security events
        recent_events = len(
            [
                log
                for log in self.audit_logs
                if log.timestamp > datetime.now() - timedelta(hours=24)
            ]
        )

        # Active tokens
        active_token_count = len(
            [
                token
                for token in self.active_tokens.values()
                if not token.revoked and datetime.now() < token.expires_at
            ]
        )

        return {
            "security_level": self.security_level.value,
            "vault_integration": self.vault_integration,
            "vulnerabilities": {
                "total_active": sum(vuln_counts.values()),
                "by_severity": vuln_counts,
                "total_resolved": len(
                    [v for v in self.security_vulnerabilities if v.resolved]
                ),
            },
            "authentication": {
                "active_tokens": active_token_count,
                "expired_tokens": len(self.active_tokens) - active_token_count,
            },
            "audit": {
                "total_events": len(self.audit_logs),
                "recent_events_24h": recent_events,
                "audit_logging_enabled": self.audit_logging,
            },
            "encryption": {
                "encryption_enabled": True,
                "key_rotation_needed": False,  # Would implement key age checking
            },
        }

    def get_vulnerability_report(
        self, severity_filter: SecurityLevel = None
    ) -> List[SecurityVulnerability]:
        """Get vulnerability report"""

        vulnerabilities = self.security_vulnerabilities

        if severity_filter:
            vulnerabilities = [
                v for v in vulnerabilities if v.severity == severity_filter
            ]

        # Sort by severity and detection time
        severity_order = {
            SecurityLevel.CRITICAL: 0,
            SecurityLevel.HIGH: 1,
            SecurityLevel.MEDIUM: 2,
            SecurityLevel.LOW: 3,
        }

        vulnerabilities.sort(
            key=lambda v: (severity_order[v.severity], v.detected_at), reverse=True
        )

        return vulnerabilities

    def resolve_vulnerability(
        self, vulnerability_id: str, resolution_notes: str = None
    ) -> bool:
        """Mark vulnerability as resolved"""

        for vuln in self.security_vulnerabilities:
            if vuln.vulnerability_id == vulnerability_id:
                vuln.resolved = True
                vuln.resolved_at = datetime.now()

                # Log resolution
                self.log_security_event(
                    event_type="vulnerability_resolved",
                    user_id=None,
                    resource="security",
                    action="resolve_vulnerability",
                    result="success",
                    additional_data={
                        "vulnerability_id": vulnerability_id,
                        "resolution_notes": resolution_notes,
                    },
                )

                # Save data
                self._save_security_data()

                return True

        return False

    def cleanup_expired_tokens(self):
        """Clean up expired tokens"""

        current_time = datetime.now()
        expired_tokens = [
            token_id
            for token_id, token in self.active_tokens.items()
            if current_time > token.expires_at
        ]

        for token_id in expired_tokens:
            del self.active_tokens[token_id]

        if expired_tokens:
            self.logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")

    def get_audit_logs(
        self, hours: int = 24, event_type: str = None
    ) -> List[SecurityAuditLog]:
        """Get audit logs for specified time period"""

        cutoff_time = datetime.now() - timedelta(hours=hours)

        logs = [log for log in self.audit_logs if log.timestamp > cutoff_time]

        if event_type:
            logs = [log for log in logs if log.event_type == event_type]

        return sorted(logs, key=lambda x: x.timestamp, reverse=True)
