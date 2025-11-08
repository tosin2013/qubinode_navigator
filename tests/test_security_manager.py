"""
Tests for Qubinode Navigator Security Manager

Tests security hardening, access control, vulnerability scanning,
and audit logging for deployment operations.
"""

import pytest
import pytest_asyncio
import tempfile
import json
import secrets
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.security_manager import (
    SecurityManager, SecurityVulnerability, AccessToken, SecurityAuditLog,
    SecurityLevel, AccessLevel, VulnerabilityType
)


class TestSecurityManager:
    """Test cases for security manager"""
    
    def setup_method(self):
        """Setup test environment"""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        
        # Security manager configuration
        self.config = {
            'security_level': 'high',
            'vault_integration': True,
            'audit_logging': True,
            'token_expiry_hours': 1,  # Short expiry for testing
            'security_storage_path': f"{self.temp_dir}/security",
            'audit_log_path': f"{self.temp_dir}/security/audit.log",
            'credentials_path': f"{self.temp_dir}/security/credentials"
        }
        
        # Create security manager
        self.security_manager = SecurityManager(self.config)
    
    def test_security_manager_initialization(self):
        """Test security manager initialization"""
        assert self.security_manager.security_level == SecurityLevel.HIGH
        assert self.security_manager.vault_integration is True
        assert self.security_manager.audit_logging is True
        assert self.security_manager.token_expiry_hours == 1
        
        # Check storage paths exist
        assert self.security_manager.security_storage_path.exists()
        assert self.security_manager.credentials_path.exists()
        
        # Check encryption components initialized
        assert self.security_manager.encryption_key is not None
        assert self.security_manager.cipher_suite is not None
        assert self.security_manager.jwt_secret is not None
        
        # Check sensitive patterns loaded
        assert len(self.security_manager.sensitive_patterns) > 0
    
    def test_encryption_key_initialization(self):
        """Test encryption key initialization and persistence"""
        # Key should be generated and saved
        key_file = self.security_manager.security_storage_path / "encryption.key"
        assert key_file.exists()
        
        # Key should be 44 bytes (Fernet key)
        with open(key_file, 'rb') as f:
            key = f.read()
        assert len(key) == 44  # Base64 encoded 32-byte key
        
        # File should have restricted permissions
        assert oct(key_file.stat().st_mode)[-3:] == '600'
    
    def test_jwt_secret_initialization(self):
        """Test JWT secret initialization and persistence"""
        # Secret should be generated and saved
        secret_file = self.security_manager.security_storage_path / "jwt.secret"
        assert secret_file.exists()
        
        # Secret should be non-empty
        with open(secret_file, 'r') as f:
            secret = f.read().strip()
        assert len(secret) > 0
        
        # File should have restricted permissions
        assert oct(secret_file.stat().st_mode)[-3:] == '600'
    
    def test_generate_access_token(self):
        """Test access token generation"""
        user_id = "test_user"
        access_level = AccessLevel.ADMIN
        permissions = ["read", "write", "deploy"]
        
        token, jwt_token = self.security_manager.generate_access_token(
            user_id=user_id,
            access_level=access_level,
            permissions=permissions
        )
        
        # Check token properties
        assert isinstance(token, AccessToken)
        assert token.user_id == user_id
        assert token.access_level == access_level
        assert token.permissions == permissions
        assert not token.revoked
        assert token.expires_at > datetime.now()
        
        # Check JWT token
        assert isinstance(jwt_token, str)
        assert len(jwt_token) > 0
        
        # Token should be in active tokens
        assert token.token_id in self.security_manager.active_tokens
    
    def test_validate_access_token(self):
        """Test access token validation"""
        # Generate token
        token, jwt_token = self.security_manager.generate_access_token(
            user_id="test_user",
            access_level=AccessLevel.READ,
            permissions=["read"]
        )
        
        # Validate token
        validated_token = self.security_manager.validate_access_token(jwt_token)
        
        assert validated_token is not None
        assert validated_token.token_id == token.token_id
        assert validated_token.user_id == token.user_id
        assert validated_token.access_level == token.access_level
        assert validated_token.last_used is not None
    
    def test_validate_invalid_token(self):
        """Test validation of invalid token"""
        invalid_token = "invalid.jwt.token"
        
        validated_token = self.security_manager.validate_access_token(invalid_token)
        assert validated_token is None
    
    def test_revoke_access_token(self):
        """Test access token revocation"""
        # Generate token
        token, jwt_token = self.security_manager.generate_access_token(
            user_id="test_user",
            access_level=AccessLevel.READ
        )
        
        # Revoke token
        success = self.security_manager.revoke_access_token(token.token_id, "test_user")
        assert success is True
        
        # Token should be marked as revoked
        assert self.security_manager.active_tokens[token.token_id].revoked is True
        
        # Validation should fail
        validated_token = self.security_manager.validate_access_token(jwt_token)
        assert validated_token is None
    
    def test_check_permission(self):
        """Test permission checking"""
        # Generate token with specific permissions
        token, _ = self.security_manager.generate_access_token(
            user_id="test_user",
            access_level=AccessLevel.WRITE,
            permissions=["deploy", "monitor"]
        )
        
        # Test access level permissions
        assert self.security_manager.check_permission(token, "read") is True
        assert self.security_manager.check_permission(token, "write") is True
        assert self.security_manager.check_permission(token, "admin") is False
        
        # Test specific permissions
        assert self.security_manager.check_permission(token, "deploy") is True
        assert self.security_manager.check_permission(token, "monitor") is True
        assert self.security_manager.check_permission(token, "delete") is False
    
    def test_super_admin_permissions(self):
        """Test super admin has all permissions"""
        token, _ = self.security_manager.generate_access_token(
            user_id="admin",
            access_level=AccessLevel.SUPER_ADMIN
        )
        
        # Super admin should have all permissions
        assert self.security_manager.check_permission(token, "read") is True
        assert self.security_manager.check_permission(token, "write") is True
        assert self.security_manager.check_permission(token, "admin") is True
        assert self.security_manager.check_permission(token, "any_permission") is True
    
    def test_encrypt_decrypt_sensitive_data(self):
        """Test encryption and decryption of sensitive data"""
        original_data = "This is sensitive information: password123"
        
        # Encrypt data
        encrypted_data = self.security_manager.encrypt_sensitive_data(original_data)
        assert encrypted_data != original_data
        assert len(encrypted_data) > 0
        
        # Decrypt data
        decrypted_data = self.security_manager.decrypt_sensitive_data(encrypted_data)
        assert decrypted_data == original_data
    
    def test_hash_verify_password(self):
        """Test password hashing and verification"""
        password = "test_password_123"
        
        # Hash password
        hashed = self.security_manager.hash_password(password)
        assert hashed != password
        assert len(hashed) > 0
        
        # Verify correct password
        assert self.security_manager.verify_password(password, hashed) is True
        
        # Verify incorrect password
        assert self.security_manager.verify_password("wrong_password", hashed) is False
    
    async def test_scan_for_vulnerabilities(self):
        """Test vulnerability scanning"""
        # Create test files with vulnerabilities
        test_dir = Path(self.temp_dir) / "test_scan"
        test_dir.mkdir(exist_ok=True)
        
        # File with potential API key
        api_key_file = test_dir / "config.py"
        with open(api_key_file, 'w') as f:
            f.write('API_KEY = "sk-1234567890abcdef1234567890abcdef"\n')
            f.write('password = "secret123"\n')
        
        # File with insecure permissions
        insecure_file = test_dir / "secrets.txt"
        with open(insecure_file, 'w') as f:
            f.write("database_password = secret123")
        insecure_file.chmod(0o644)  # World readable
        
        # Scan for vulnerabilities
        vulnerabilities = await self.security_manager.scan_for_vulnerabilities([str(test_dir)])
        
        # Should find vulnerabilities
        assert len(vulnerabilities) > 0
        
        # Check vulnerability types
        vuln_types = [v.vulnerability_type for v in vulnerabilities]
        assert VulnerabilityType.CREDENTIAL_EXPOSURE in vuln_types
        assert VulnerabilityType.WEAK_AUTHENTICATION in vuln_types
    
    async def test_scan_file_for_vulnerabilities(self):
        """Test individual file vulnerability scanning"""
        # Create test file with sensitive content
        test_file = Path(self.temp_dir) / "test_config.py"
        with open(test_file, 'w') as f:
            f.write('DATABASE_URL = "postgresql://user:pass@localhost/db"\n')
            f.write('SECRET_KEY = "very-secret-key-12345"\n')
        
        vulnerabilities = await self.security_manager._scan_file_for_vulnerabilities(test_file)
        
        # Should find credential exposure vulnerabilities
        assert len(vulnerabilities) > 0
        assert all(v.vulnerability_type == VulnerabilityType.CREDENTIAL_EXPOSURE for v in vulnerabilities)
    
    def test_should_skip_file(self):
        """Test file skipping logic"""
        # Should skip binary files
        assert self.security_manager._should_skip_file(Path("test.pyc")) is True
        assert self.security_manager._should_skip_file(Path("test.jpg")) is True
        assert self.security_manager._should_skip_file(Path("test.exe")) is True
        
        # Should not skip text files
        assert self.security_manager._should_skip_file(Path("test.py")) is False
        assert self.security_manager._should_skip_file(Path("test.txt")) is False
        assert self.security_manager._should_skip_file(Path("config.yml")) is False
        
        # Should skip files in excluded directories
        assert self.security_manager._should_skip_file(Path(".git/config")) is True
        assert self.security_manager._should_skip_file(Path("__pycache__/test.pyc")) is True
    
    def test_log_security_event(self):
        """Test security event logging"""
        # Log security event
        self.security_manager.log_security_event(
            event_type="test_event",
            user_id="test_user",
            resource="test_resource",
            action="test_action",
            result="success",
            ip_address="192.168.1.100",
            additional_data={"key": "value"}
        )
        
        # Check event was logged
        assert len(self.security_manager.audit_logs) == 1
        
        log_entry = self.security_manager.audit_logs[0]
        assert log_entry.event_type == "test_event"
        assert log_entry.user_id == "test_user"
        assert log_entry.resource == "test_resource"
        assert log_entry.action == "test_action"
        assert log_entry.result == "success"
        assert log_entry.ip_address == "192.168.1.100"
        assert log_entry.additional_data["key"] == "value"
        
        # Check log file was written
        assert self.security_manager.audit_log_path.exists()
    
    def test_get_security_summary(self):
        """Test security summary generation"""
        # Add some test data
        self.security_manager.security_vulnerabilities.append(
            SecurityVulnerability(
                vulnerability_id="test_vuln_1",
                vulnerability_type=VulnerabilityType.CREDENTIAL_EXPOSURE,
                severity=SecurityLevel.HIGH,
                title="Test vulnerability",
                description="Test description",
                affected_components=["test_component"],
                remediation_steps=["Fix it"],
                detected_at=datetime.now()
            )
        )
        
        # Generate token
        self.security_manager.generate_access_token("test_user", AccessLevel.READ)
        
        # Log event
        self.security_manager.log_security_event(
            "test_event", "test_user", "resource", "action", "success"
        )
        
        summary = self.security_manager.get_security_summary()
        
        assert summary['security_level'] == 'high'
        assert summary['vault_integration'] is True
        assert summary['vulnerabilities']['total_active'] == 1
        assert summary['vulnerabilities']['by_severity']['high'] == 1
        assert summary['authentication']['active_tokens'] == 1
        assert summary['audit']['total_events'] == 2  # Token generation + test event
        assert summary['encryption']['encryption_enabled'] is True
    
    def test_get_vulnerability_report(self):
        """Test vulnerability report generation"""
        # Add test vulnerabilities
        vuln1 = SecurityVulnerability(
            vulnerability_id="vuln_1",
            vulnerability_type=VulnerabilityType.CREDENTIAL_EXPOSURE,
            severity=SecurityLevel.CRITICAL,
            title="Critical vulnerability",
            description="Critical description",
            affected_components=["component1"],
            remediation_steps=["Fix critical"],
            detected_at=datetime.now() - timedelta(hours=2)
        )
        
        vuln2 = SecurityVulnerability(
            vulnerability_id="vuln_2",
            vulnerability_type=VulnerabilityType.WEAK_AUTHENTICATION,
            severity=SecurityLevel.MEDIUM,
            title="Medium vulnerability",
            description="Medium description",
            affected_components=["component2"],
            remediation_steps=["Fix medium"],
            detected_at=datetime.now() - timedelta(hours=1)
        )
        
        self.security_manager.security_vulnerabilities = [vuln1, vuln2]
        
        # Get all vulnerabilities
        all_vulns = self.security_manager.get_vulnerability_report()
        assert len(all_vulns) == 2
        
        # Should be sorted by severity (critical first)
        assert all_vulns[0].severity == SecurityLevel.CRITICAL
        assert all_vulns[1].severity == SecurityLevel.MEDIUM
        
        # Filter by severity
        critical_vulns = self.security_manager.get_vulnerability_report(SecurityLevel.CRITICAL)
        assert len(critical_vulns) == 1
        assert critical_vulns[0].vulnerability_id == "vuln_1"
    
    def test_resolve_vulnerability(self):
        """Test vulnerability resolution"""
        # Add test vulnerability
        vuln = SecurityVulnerability(
            vulnerability_id="test_vuln",
            vulnerability_type=VulnerabilityType.CREDENTIAL_EXPOSURE,
            severity=SecurityLevel.HIGH,
            title="Test vulnerability",
            description="Test description",
            affected_components=["test_component"],
            remediation_steps=["Fix it"],
            detected_at=datetime.now()
        )
        
        self.security_manager.security_vulnerabilities.append(vuln)
        
        # Resolve vulnerability
        success = self.security_manager.resolve_vulnerability("test_vuln", "Fixed by test")
        assert success is True
        
        # Check vulnerability is marked as resolved
        resolved_vuln = self.security_manager.security_vulnerabilities[0]
        assert resolved_vuln.resolved is True
        assert resolved_vuln.resolved_at is not None
        
        # Try to resolve non-existent vulnerability
        success = self.security_manager.resolve_vulnerability("non_existent", "Notes")
        assert success is False
    
    def test_cleanup_expired_tokens(self):
        """Test expired token cleanup"""
        # Generate token with short expiry
        token, _ = self.security_manager.generate_access_token(
            user_id="test_user",
            access_level=AccessLevel.READ
        )
        
        # Manually expire token
        token.expires_at = datetime.now() - timedelta(hours=1)
        
        # Cleanup expired tokens
        self.security_manager.cleanup_expired_tokens()
        
        # Token should be removed
        assert token.token_id not in self.security_manager.active_tokens
    
    def test_get_audit_logs(self):
        """Test audit log retrieval"""
        # Log some events
        self.security_manager.log_security_event(
            "event1", "user1", "resource1", "action1", "success"
        )
        self.security_manager.log_security_event(
            "event2", "user2", "resource2", "action2", "failure"
        )
        self.security_manager.log_security_event(
            "event1", "user3", "resource3", "action3", "success"
        )
        
        # Get all logs
        all_logs = self.security_manager.get_audit_logs(hours=24)
        assert len(all_logs) == 3
        
        # Filter by event type
        event1_logs = self.security_manager.get_audit_logs(hours=24, event_type="event1")
        assert len(event1_logs) == 2
        assert all(log.event_type == "event1" for log in event1_logs)
    
    def test_secure_delete_file(self):
        """Test secure file deletion"""
        # Create test file
        test_file = Path(self.temp_dir) / "test_delete.txt"
        with open(test_file, 'w') as f:
            f.write("Sensitive content to be deleted")
        
        assert test_file.exists()
        
        # Securely delete file
        success = self.security_manager.secure_delete_file(test_file)
        assert success is True
        assert not test_file.exists()
        
        # Try to delete non-existent file
        success = self.security_manager.secure_delete_file(Path("non_existent.txt"))
        assert success is True  # Should return True for non-existent files
    
    def test_serialization_deserialization(self):
        """Test vulnerability and audit log serialization/deserialization"""
        # Test vulnerability serialization
        vuln = SecurityVulnerability(
            vulnerability_id="test_vuln",
            vulnerability_type=VulnerabilityType.CREDENTIAL_EXPOSURE,
            severity=SecurityLevel.HIGH,
            title="Test vulnerability",
            description="Test description",
            affected_components=["component1", "component2"],
            remediation_steps=["Step 1", "Step 2"],
            detected_at=datetime.now(),
            resolved=True,
            resolved_at=datetime.now()
        )
        
        # Serialize and deserialize
        serialized = self.security_manager._serialize_vulnerability(vuln)
        deserialized = self.security_manager._deserialize_vulnerability(serialized)
        
        assert deserialized.vulnerability_id == vuln.vulnerability_id
        assert deserialized.vulnerability_type == vuln.vulnerability_type
        assert deserialized.severity == vuln.severity
        assert deserialized.title == vuln.title
        assert deserialized.resolved == vuln.resolved
        
        # Test audit log serialization
        audit_log = SecurityAuditLog(
            log_id="test_log",
            event_type="test_event",
            user_id="test_user",
            resource="test_resource",
            action="test_action",
            result="success",
            timestamp=datetime.now(),
            ip_address="192.168.1.1",
            user_agent="test_agent",
            additional_data={"key": "value"}
        )
        
        # Serialize and deserialize
        serialized = self.security_manager._serialize_audit_log(audit_log)
        deserialized = self.security_manager._deserialize_audit_log(serialized)
        
        assert deserialized.log_id == audit_log.log_id
        assert deserialized.event_type == audit_log.event_type
        assert deserialized.user_id == audit_log.user_id
        assert deserialized.ip_address == audit_log.ip_address
        assert deserialized.additional_data == audit_log.additional_data


class TestSecurityVulnerability:
    """Test security vulnerability data class"""
    
    def test_security_vulnerability_creation(self):
        """Test security vulnerability creation"""
        vuln = SecurityVulnerability(
            vulnerability_id="vuln_123",
            vulnerability_type=VulnerabilityType.CODE_INJECTION,
            severity=SecurityLevel.CRITICAL,
            title="SQL Injection vulnerability",
            description="Potential SQL injection in user input",
            affected_components=["web_app", "database"],
            remediation_steps=["Sanitize input", "Use parameterized queries"],
            detected_at=datetime.now(),
            resolved=False
        )
        
        assert vuln.vulnerability_id == "vuln_123"
        assert vuln.vulnerability_type == VulnerabilityType.CODE_INJECTION
        assert vuln.severity == SecurityLevel.CRITICAL
        assert vuln.title == "SQL Injection vulnerability"
        assert len(vuln.affected_components) == 2
        assert len(vuln.remediation_steps) == 2
        assert vuln.resolved is False
        assert vuln.resolved_at is None


class TestAccessToken:
    """Test access token data class"""
    
    def test_access_token_creation(self):
        """Test access token creation"""
        issued_at = datetime.now()
        expires_at = issued_at + timedelta(hours=24)
        
        token = AccessToken(
            token_id="token_123",
            user_id="user_456",
            access_level=AccessLevel.ADMIN,
            permissions=["read", "write", "deploy"],
            issued_at=issued_at,
            expires_at=expires_at,
            revoked=False
        )
        
        assert token.token_id == "token_123"
        assert token.user_id == "user_456"
        assert token.access_level == AccessLevel.ADMIN
        assert token.permissions == ["read", "write", "deploy"]
        assert token.issued_at == issued_at
        assert token.expires_at == expires_at
        assert token.revoked is False
        assert token.last_used is None


class TestSecurityAuditLog:
    """Test security audit log data class"""
    
    def test_security_audit_log_creation(self):
        """Test security audit log creation"""
        timestamp = datetime.now()
        
        log = SecurityAuditLog(
            log_id="log_123",
            event_type="authentication",
            user_id="user_456",
            resource="api_endpoint",
            action="login",
            result="success",
            timestamp=timestamp,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            additional_data={"session_id": "sess_789"}
        )
        
        assert log.log_id == "log_123"
        assert log.event_type == "authentication"
        assert log.user_id == "user_456"
        assert log.resource == "api_endpoint"
        assert log.action == "login"
        assert log.result == "success"
        assert log.timestamp == timestamp
        assert log.ip_address == "192.168.1.100"
        assert log.user_agent == "Mozilla/5.0"
        assert log.additional_data["session_id"] == "sess_789"


class TestEnums:
    """Test enumeration classes"""
    
    def test_security_level_enum(self):
        """Test security level enum"""
        assert SecurityLevel.LOW.value == "low"
        assert SecurityLevel.MEDIUM.value == "medium"
        assert SecurityLevel.HIGH.value == "high"
        assert SecurityLevel.CRITICAL.value == "critical"
    
    def test_access_level_enum(self):
        """Test access level enum"""
        assert AccessLevel.READ.value == "read"
        assert AccessLevel.WRITE.value == "write"
        assert AccessLevel.ADMIN.value == "admin"
        assert AccessLevel.SUPER_ADMIN.value == "super_admin"
    
    def test_vulnerability_type_enum(self):
        """Test vulnerability type enum"""
        assert VulnerabilityType.CREDENTIAL_EXPOSURE.value == "credential_exposure"
        assert VulnerabilityType.WEAK_AUTHENTICATION.value == "weak_authentication"
        assert VulnerabilityType.INSECURE_COMMUNICATION.value == "insecure_communication"
        assert VulnerabilityType.PRIVILEGE_ESCALATION.value == "privilege_escalation"
        assert VulnerabilityType.CODE_INJECTION.value == "code_injection"
        assert VulnerabilityType.PATH_TRAVERSAL.value == "path_traversal"
        assert VulnerabilityType.WEAK_ENCRYPTION.value == "weak_encryption"
        assert VulnerabilityType.OUTDATED_DEPENDENCIES.value == "outdated_dependencies"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])
