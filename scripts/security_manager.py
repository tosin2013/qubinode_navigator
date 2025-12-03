#!/usr/bin/env python3
"""
Qubinode Navigator Security Manager CLI

Command-line interface for security hardening, vulnerability scanning,
access control, and audit logging for deployment operations.
"""

import argparse
import asyncio
import getpass
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.security_manager import AccessLevel, SecurityLevel, SecurityManager


async def main():
    """Main CLI entry point"""

    parser = argparse.ArgumentParser(
        description="Qubinode Navigator Security Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show security status
  python security_manager.py status

  # Scan for vulnerabilities
  python security_manager.py scan --path /path/to/scan

  # Generate access token
  python security_manager.py token --user admin --level admin

  # View vulnerability report
  python security_manager.py vulnerabilities --severity high

  # View audit logs
  python security_manager.py audit --hours 24

  # Resolve vulnerability
  python security_manager.py resolve --vulnerability-id vuln_123
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show security status")
    status_parser.add_argument(
        "--format", choices=["summary", "json"], default="summary", help="Output format"
    )

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan for vulnerabilities")
    scan_parser.add_argument(
        "--path",
        action="append",
        help="Paths to scan (can be specified multiple times)",
    )
    scan_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # Token command
    token_parser = subparsers.add_parser("token", help="Manage access tokens")
    token_parser.add_argument(
        "--action",
        choices=["generate", "validate", "revoke"],
        default="generate",
        help="Token action",
    )
    token_parser.add_argument("--user", required=True, help="User ID")
    token_parser.add_argument(
        "--level",
        choices=["read", "write", "admin", "super_admin"],
        default="read",
        help="Access level",
    )
    token_parser.add_argument("--permissions", nargs="*", help="Additional permissions")
    token_parser.add_argument("--token", help="Token to validate or revoke")

    # Vulnerabilities command
    vuln_parser = subparsers.add_parser(
        "vulnerabilities", help="View vulnerability report"
    )
    vuln_parser.add_argument(
        "--severity",
        choices=["low", "medium", "high", "critical"],
        help="Filter by severity",
    )
    vuln_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )
    vuln_parser.add_argument(
        "--resolved", action="store_true", help="Include resolved vulnerabilities"
    )

    # Resolve command
    resolve_parser = subparsers.add_parser("resolve", help="Resolve vulnerability")
    resolve_parser.add_argument(
        "--vulnerability-id", required=True, help="Vulnerability ID to resolve"
    )
    resolve_parser.add_argument("--notes", help="Resolution notes")

    # Audit command
    audit_parser = subparsers.add_parser("audit", help="View audit logs")
    audit_parser.add_argument(
        "--hours", type=int, default=24, help="Hours of logs to show"
    )
    audit_parser.add_argument("--event-type", help="Filter by event type")
    audit_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # Encrypt command
    encrypt_parser = subparsers.add_parser("encrypt", help="Encrypt sensitive data")
    encrypt_parser.add_argument("--data", help="Data to encrypt (or use stdin)")
    encrypt_parser.add_argument("--file", help="File to encrypt")

    # Decrypt command
    decrypt_parser = subparsers.add_parser("decrypt", help="Decrypt sensitive data")
    decrypt_parser.add_argument("--data", help="Data to decrypt")
    decrypt_parser.add_argument("--file", help="File to decrypt")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test security system")
    test_parser.add_argument(
        "--component",
        choices=["auth", "encryption", "scanning"],
        default="auth",
        help="Component to test",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize security manager
    config = {
        "security_level": "high",
        "vault_integration": True,
        "audit_logging": True,
        "token_expiry_hours": 24,
        "security_storage_path": "data/security",
        "audit_log_path": "data/security/audit.log",
    }

    security_manager = SecurityManager(config)

    # Execute command
    if args.command == "status":
        await handle_status_command(security_manager, args)
    elif args.command == "scan":
        await handle_scan_command(security_manager, args)
    elif args.command == "token":
        await handle_token_command(security_manager, args)
    elif args.command == "vulnerabilities":
        await handle_vulnerabilities_command(security_manager, args)
    elif args.command == "resolve":
        await handle_resolve_command(security_manager, args)
    elif args.command == "audit":
        await handle_audit_command(security_manager, args)
    elif args.command == "encrypt":
        await handle_encrypt_command(security_manager, args)
    elif args.command == "decrypt":
        await handle_decrypt_command(security_manager, args)
    elif args.command == "test":
        await handle_test_command(security_manager, args)


async def handle_status_command(security_manager: SecurityManager, args):
    """Handle status command"""

    try:
        summary = security_manager.get_security_summary()

        if args.format == "json":
            print(json.dumps(summary, indent=2))
        else:
            print("=== Security Manager Status ===")
            print(f"Security Level: {summary['security_level'].title()}")
            print(
                f"Vault Integration: {'Enabled' if summary['vault_integration'] else 'Disabled'}"
            )

            print("\n=== Vulnerabilities ===")
            vulns = summary["vulnerabilities"]
            print(f"Active Vulnerabilities: {vulns['total_active']}")
            print(f"Resolved Vulnerabilities: {vulns['total_resolved']}")

            if vulns["total_active"] > 0:
                print("By Severity:")
                for severity, count in vulns["by_severity"].items():
                    if count > 0:
                        severity_symbol = {
                            "critical": "🔴",
                            "high": "🟠",
                            "medium": "🟡",
                            "low": "🟢",
                        }.get(severity, "•")
                        print(f"  {severity_symbol} {severity.title()}: {count}")

            print("\n=== Authentication ===")
            auth = summary["authentication"]
            print(f"Active Tokens: {auth['active_tokens']}")
            print(f"Expired Tokens: {auth['expired_tokens']}")

            print("\n=== Audit Logging ===")
            audit = summary["audit"]
            print(
                f"Audit Logging: {'Enabled' if audit['audit_logging_enabled'] else 'Disabled'}"
            )
            print(f"Total Events: {audit['total_events']}")
            print(f"Recent Events (24h): {audit['recent_events_24h']}")

            print("\n=== Encryption ===")
            encryption = summary["encryption"]
            print(
                f"Encryption: {'Enabled' if encryption['encryption_enabled'] else 'Disabled'}"
            )

    except Exception as e:
        print(f"Error getting security status: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_scan_command(security_manager: SecurityManager, args):
    """Handle scan command"""

    try:
        scan_paths = args.path or ["."]

        print(f"Scanning for vulnerabilities in: {', '.join(scan_paths)}")
        vulnerabilities = await security_manager.scan_for_vulnerabilities(scan_paths)

        if args.format == "json":
            vuln_data = []
            for vuln in vulnerabilities:
                vuln_dict = {
                    "vulnerability_id": vuln.vulnerability_id,
                    "vulnerability_type": vuln.vulnerability_type.value,
                    "severity": vuln.severity.value,
                    "title": vuln.title,
                    "description": vuln.description,
                    "affected_components": vuln.affected_components,
                    "remediation_steps": vuln.remediation_steps,
                    "detected_at": vuln.detected_at.isoformat(),
                }
                vuln_data.append(vuln_dict)
            print(json.dumps(vuln_data, indent=2))
        else:
            if not vulnerabilities:
                print("✓ No new vulnerabilities found")
                return

            print(
                f"\n=== Vulnerability Scan Results ({len(vulnerabilities)} found) ==="
            )
            print(f"{'Severity':<10} {'Type':<20} {'Title':<40} {'Components':<20}")
            print("-" * 95)

            for vuln in vulnerabilities:
                severity_symbol = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢",
                }.get(vuln.severity.value, "•")
                components = ", ".join(vuln.affected_components[:2])  # Show first 2
                if len(vuln.affected_components) > 2:
                    components += f" (+{len(vuln.affected_components) - 2})"

                print(
                    f"{severity_symbol} {vuln.severity.value:<9} {vuln.vulnerability_type.value:<20} {vuln.title[:39]:<40} {components[:19]:<20}"
                )

            # Show details for critical/high vulnerabilities
            critical_high = [
                v for v in vulnerabilities if v.severity.value in ["critical", "high"]
            ]
            if critical_high:
                print(f"\n=== High Priority Vulnerabilities ===")
                for vuln in critical_high[:3]:  # Show first 3
                    print(f"\n{vuln.title}")
                    print(f"  Severity: {vuln.severity.value.title()}")
                    print(f"  Description: {vuln.description}")
                    print("  Remediation:")
                    for step in vuln.remediation_steps[:2]:  # Show first 2 steps
                        print(f"    • {step}")

    except Exception as e:
        print(f"Error during vulnerability scan: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_token_command(security_manager: SecurityManager, args):
    """Handle token command"""

    try:
        if args.action == "generate":
            access_level = AccessLevel(args.level)
            permissions = args.permissions or []

            token, jwt_token = security_manager.generate_access_token(
                user_id=args.user, access_level=access_level, permissions=permissions
            )

            print("=== Access Token Generated ===")
            print(f"User ID: {token.user_id}")
            print(f"Access Level: {token.access_level.value}")
            print(
                f"Permissions: {', '.join(token.permissions) if token.permissions else 'None'}"
            )
            print(f"Expires: {token.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"JWT Token: {jwt_token}")

        elif args.action == "validate":
            if not args.token:
                print("Error: --token required for validation", file=sys.stderr)
                sys.exit(1)

            token = security_manager.validate_access_token(args.token)

            if token:
                print("✓ Token is valid")
                print(f"User ID: {token.user_id}")
                print(f"Access Level: {token.access_level.value}")
                print(f"Expires: {token.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(
                    f"Last Used: {token.last_used.strftime('%Y-%m-%d %H:%M:%S') if token.last_used else 'Never'}"
                )
            else:
                print("✗ Token is invalid or expired")
                sys.exit(1)

        elif args.action == "revoke":
            if not args.token:
                print("Error: --token required for revocation", file=sys.stderr)
                sys.exit(1)

            # Extract token ID from JWT (simplified)
            import jwt

            try:
                payload = jwt.decode(args.token, options={"verify_signature": False})
                token_id = payload["token_id"]

                success = security_manager.revoke_access_token(token_id, args.user)

                if success:
                    print("✓ Token revoked successfully")
                else:
                    print("✗ Token not found or already revoked")
                    sys.exit(1)
            except Exception:
                print("✗ Invalid token format", file=sys.stderr)
                sys.exit(1)

    except Exception as e:
        print(f"Error managing token: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_vulnerabilities_command(security_manager: SecurityManager, args):
    """Handle vulnerabilities command"""

    try:
        severity_filter = SecurityLevel(args.severity) if args.severity else None
        vulnerabilities = security_manager.get_vulnerability_report(severity_filter)

        # Filter resolved if not requested
        if not args.resolved:
            vulnerabilities = [v for v in vulnerabilities if not v.resolved]

        if args.format == "json":
            vuln_data = []
            for vuln in vulnerabilities:
                vuln_dict = {
                    "vulnerability_id": vuln.vulnerability_id,
                    "vulnerability_type": vuln.vulnerability_type.value,
                    "severity": vuln.severity.value,
                    "title": vuln.title,
                    "description": vuln.description,
                    "affected_components": vuln.affected_components,
                    "remediation_steps": vuln.remediation_steps,
                    "detected_at": vuln.detected_at.isoformat(),
                    "resolved": vuln.resolved,
                    "resolved_at": (
                        vuln.resolved_at.isoformat() if vuln.resolved_at else None
                    ),
                }
                vuln_data.append(vuln_dict)
            print(json.dumps(vuln_data, indent=2))
        else:
            if not vulnerabilities:
                status = (
                    "resolved vulnerabilities"
                    if args.resolved
                    else "active vulnerabilities"
                )
                print(f"No {status} found")
                return

            print(
                f"=== Vulnerability Report ({len(vulnerabilities)} vulnerabilities) ==="
            )
            print(
                f"{'ID':<25} {'Severity':<10} {'Type':<20} {'Status':<10} {'Detected':<12}"
            )
            print("-" * 85)

            for vuln in vulnerabilities:
                severity_symbol = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢",
                }.get(vuln.severity.value, "•")
                status = "Resolved" if vuln.resolved else "Active"
                detected = vuln.detected_at.strftime("%Y-%m-%d")

                print(
                    f"{vuln.vulnerability_id[:24]:<25} {severity_symbol} {vuln.severity.value:<9} {vuln.vulnerability_type.value:<20} {status:<10} {detected:<12}"
                )

    except Exception as e:
        print(f"Error getting vulnerability report: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_resolve_command(security_manager: SecurityManager, args):
    """Handle resolve command"""

    try:
        success = security_manager.resolve_vulnerability(
            vulnerability_id=args.vulnerability_id, resolution_notes=args.notes
        )

        if success:
            print(f"✓ Vulnerability {args.vulnerability_id} marked as resolved")
        else:
            print(f"✗ Vulnerability {args.vulnerability_id} not found")
            sys.exit(1)

    except Exception as e:
        print(f"Error resolving vulnerability: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_audit_command(security_manager: SecurityManager, args):
    """Handle audit command"""

    try:
        logs = security_manager.get_audit_logs(
            hours=args.hours, event_type=args.event_type
        )

        if args.format == "json":
            log_data = []
            for log in logs:
                log_dict = {
                    "log_id": log.log_id,
                    "event_type": log.event_type,
                    "user_id": log.user_id,
                    "resource": log.resource,
                    "action": log.action,
                    "result": log.result,
                    "timestamp": log.timestamp.isoformat(),
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "additional_data": log.additional_data,
                }
                log_data.append(log_dict)
            print(json.dumps(log_data, indent=2))
        else:
            if not logs:
                print(f"No audit logs found for the last {args.hours} hours")
                return

            print(f"=== Audit Logs (Last {args.hours} hours, {len(logs)} entries) ===")
            print(
                f"{'Timestamp':<20} {'Event Type':<20} {'User':<15} {'Action':<20} {'Result':<10}"
            )
            print("-" * 90)

            for log in logs[:50]:  # Show first 50
                timestamp = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                user = log.user_id[:14] if log.user_id else "system"
                result_symbol = {"success": "✓", "failure": "✗", "denied": "⚠"}.get(
                    log.result, "•"
                )

                print(
                    f"{timestamp:<20} {log.event_type:<20} {user:<15} {log.action:<20} {result_symbol} {log.result:<9}"
                )

            if len(logs) > 50:
                print(f"\n... and {len(logs) - 50} more entries")

    except Exception as e:
        print(f"Error getting audit logs: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_encrypt_command(security_manager: SecurityManager, args):
    """Handle encrypt command"""

    try:
        if args.file:
            # Encrypt file
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"Error: File {args.file} not found", file=sys.stderr)
                sys.exit(1)

            with open(file_path, "r") as f:
                data = f.read()

            encrypted = security_manager.encrypt_sensitive_data(data)

            # Save encrypted file
            encrypted_path = file_path.with_suffix(file_path.suffix + ".encrypted")
            with open(encrypted_path, "w") as f:
                f.write(encrypted)

            print(f"✓ File encrypted and saved as {encrypted_path}")

        else:
            # Encrypt data
            data = args.data
            if not data:
                print("Enter data to encrypt (Ctrl+D to finish):")
                data = sys.stdin.read().strip()

            encrypted = security_manager.encrypt_sensitive_data(data)
            print(f"Encrypted data: {encrypted}")

    except Exception as e:
        print(f"Error encrypting data: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_decrypt_command(security_manager: SecurityManager, args):
    """Handle decrypt command"""

    try:
        if args.file:
            # Decrypt file
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"Error: File {args.file} not found", file=sys.stderr)
                sys.exit(1)

            with open(file_path, "r") as f:
                encrypted_data = f.read()

            decrypted = security_manager.decrypt_sensitive_data(encrypted_data)

            # Save decrypted file
            if file_path.suffix == ".encrypted":
                decrypted_path = file_path.with_suffix("")
            else:
                decrypted_path = file_path.with_suffix(".decrypted")

            with open(decrypted_path, "w") as f:
                f.write(decrypted)

            print(f"✓ File decrypted and saved as {decrypted_path}")

        else:
            # Decrypt data
            encrypted_data = args.data
            if not encrypted_data:
                print("Error: --data required for decryption", file=sys.stderr)
                sys.exit(1)

            decrypted = security_manager.decrypt_sensitive_data(encrypted_data)
            print(f"Decrypted data: {decrypted}")

    except Exception as e:
        print(f"Error decrypting data: {e}", file=sys.stderr)
        sys.exit(1)


async def handle_test_command(security_manager: SecurityManager, args):
    """Handle test command"""

    try:
        print(f"Testing security system component: {args.component}")

        if args.component == "auth":
            print("✓ Testing authentication system...")

            # Test token generation
            token, jwt_token = security_manager.generate_access_token(
                user_id="test_user",
                access_level=AccessLevel.READ,
                permissions=["test_permission"],
            )
            print(f"  Generated token for user: {token.user_id}")

            # Test token validation
            validated_token = security_manager.validate_access_token(jwt_token)
            if validated_token:
                print(f"  Token validation: Success")
            else:
                print(f"  Token validation: Failed")

            # Test permission check
            has_permission = security_manager.check_permission(token, "test_permission")
            print(f"  Permission check: {'Success' if has_permission else 'Failed'}")

        elif args.component == "encryption":
            print("✓ Testing encryption system...")

            # Test data encryption/decryption
            test_data = "This is sensitive test data"
            encrypted = security_manager.encrypt_sensitive_data(test_data)
            decrypted = security_manager.decrypt_sensitive_data(encrypted)

            if decrypted == test_data:
                print(f"  Encryption/Decryption: Success")
            else:
                print(f"  Encryption/Decryption: Failed")

            # Test password hashing
            password = "test_password"
            hashed = security_manager.hash_password(password)
            verified = security_manager.verify_password(password, hashed)

            print(f"  Password hashing: {'Success' if verified else 'Failed'}")

        elif args.component == "scanning":
            print("✓ Testing vulnerability scanning...")

            # Test vulnerability scanning
            vulnerabilities = await security_manager.scan_for_vulnerabilities(["."])
            print(f"  Vulnerability scan: Found {len(vulnerabilities)} issues")

        print("✓ All tests completed")

    except Exception as e:
        print(f"Error running tests: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
