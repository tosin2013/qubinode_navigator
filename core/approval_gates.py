"""
Qubinode Navigator Approval Gates System

Manages approval workflows, automated approvals, and gate progression
for staged rollout pipelines.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from core.rollout_pipeline import ApprovalGate, ApprovalStatus


class ApprovalType(Enum):
    """Types of approval requirements"""

    MANUAL = "manual"
    AUTOMATED = "automated"
    CONDITIONAL = "conditional"
    TIME_BASED = "time_based"


@dataclass
class ApprovalRequest:
    """Individual approval request"""

    request_id: str
    gate_id: str
    pipeline_id: str
    approver: str
    request_type: ApprovalType
    message: str
    created_at: datetime
    responded_at: Optional[datetime] = None
    response: Optional[str] = None  # approved, rejected
    comments: Optional[str] = None


class ApprovalGateManager:
    """
    Approval Gate Management System

    Handles approval workflows, automated approvals, notifications,
    and gate progression logic for rollout pipelines.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Configuration
        self.auto_approval_enabled = self.config.get("auto_approval_enabled", True)
        self.approval_timeout_buffer = self.config.get("approval_timeout_buffer", 30)  # minutes
        self.notification_channels = self.config.get("notification_channels", ["email", "slack"])

        # State
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        self.approval_history: List[ApprovalRequest] = []

        # Auto-approval rules
        self.auto_approval_rules = self._load_auto_approval_rules()

    def _load_auto_approval_rules(self) -> Dict[str, Any]:
        """Load auto-approval rules configuration"""
        return {
            "low_risk_threshold": 0.8,  # Confidence threshold for auto-approval
            "security_update_auto_approve": False,  # Never auto-approve security updates
            "max_update_count": 5,  # Max updates for auto-approval
            "allowed_components": [
                "git",
                "python",
                "nodejs",
            ],  # Components safe for auto-approval
            "business_hours_only": True,  # Only auto-approve during business hours
            "weekend_approval": False,  # Require manual approval on weekends
            "maintenance_window_auto": True,  # Auto-approve during maintenance windows
        }

    async def create_approval_gate(
        self,
        pipeline_id: str,
        stage: str,
        gate_name: str,
        required_approvers: List[str],
        approval_timeout: int = 240,
        auto_approve_conditions: Dict[str, Any] = None,
    ) -> ApprovalGate:
        """Create new approval gate"""

        gate_id = f"gate_{pipeline_id}_{stage}_{int(time.time())}"

        gate = ApprovalGate(
            gate_id=gate_id,
            gate_name=gate_name,
            stage=stage,
            required_approvers=required_approvers,
            approval_timeout=approval_timeout,
            auto_approve_conditions=auto_approve_conditions or {},
            status=ApprovalStatus.PENDING,
            approvals=[],
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=approval_timeout),
        )

        self.logger.info(f"Created approval gate {gate_id} for pipeline {pipeline_id}")

        # Check for auto-approval
        if self.auto_approval_enabled:
            auto_approved = await self._check_auto_approval(gate, pipeline_id)
            if auto_approved:
                gate.status = ApprovalStatus.AUTO_APPROVED
                gate.approved_at = datetime.now()
                gate.approved_by = "system"
                self.logger.info(f"Auto-approved gate {gate_id}")

        return gate

    async def _check_auto_approval(self, gate: ApprovalGate, pipeline_id: str) -> bool:
        """Check if gate qualifies for auto-approval"""
        try:
            conditions = gate.auto_approve_conditions

            # Check confidence threshold
            if "ai_confidence" in conditions:
                if conditions["ai_confidence"] < self.auto_approval_rules["low_risk_threshold"]:
                    return False

            # Check risk level
            if "risk_level" in conditions:
                if conditions["risk_level"] in ["high", "critical"]:
                    return False

            # Check security updates
            if "has_security_updates" in conditions:
                if conditions["has_security_updates"] and not self.auto_approval_rules["security_update_auto_approve"]:
                    return False

            # Check update count
            if "update_count" in conditions:
                if conditions["update_count"] > self.auto_approval_rules["max_update_count"]:
                    return False

            # Check component types
            if "components" in conditions:
                allowed_components = self.auto_approval_rules["allowed_components"]
                if not all(comp in allowed_components for comp in conditions["components"]):
                    return False

            # Check business hours
            if self.auto_approval_rules["business_hours_only"]:
                now = datetime.now()
                if now.weekday() >= 5:  # Weekend
                    if not self.auto_approval_rules["weekend_approval"]:
                        return False
                elif now.hour < 9 or now.hour > 17:  # Outside business hours
                    return False

            # Check maintenance window
            if "maintenance_window" in conditions:
                if conditions["maintenance_window"] and self.auto_approval_rules["maintenance_window_auto"]:
                    return True

            # All conditions passed
            return True

        except Exception as e:
            self.logger.error(f"Auto-approval check failed for gate {gate.gate_id}: {e}")
            return False

    async def request_approval(self, gate: ApprovalGate, pipeline_id: str, message: str = None) -> List[ApprovalRequest]:
        """Send approval requests to required approvers"""

        requests = []

        for approver in gate.required_approvers:
            request_id = f"req_{gate.gate_id}_{approver}_{int(time.time())}"

            request = ApprovalRequest(
                request_id=request_id,
                gate_id=gate.gate_id,
                pipeline_id=pipeline_id,
                approver=approver,
                request_type=ApprovalType.MANUAL,
                message=message or f"Approval required for {gate.gate_name}",
                created_at=datetime.now(),
            )

            requests.append(request)
            self.pending_approvals[request_id] = request

            # Send notification
            await self._send_approval_notification(request, gate)

        self.logger.info(f"Sent {len(requests)} approval requests for gate {gate.gate_id}")
        return requests

    async def _send_approval_notification(self, request: ApprovalRequest, gate: ApprovalGate):
        """Send approval notification to approver"""
        try:
            notification_data = {
                "request_id": request.request_id,
                "gate_name": gate.gate_name,
                "pipeline_id": request.pipeline_id,
                "approver": request.approver,
                "message": request.message,
                "expires_at": gate.expires_at.isoformat(),
                "approval_url": f"/approval/{request.request_id}",
            }

            # Send via configured channels
            for channel in self.notification_channels:
                if channel == "email":
                    await self._send_email_notification(notification_data)
                elif channel == "slack":
                    await self._send_slack_notification(notification_data)

            self.logger.debug(f"Sent approval notification for request {request.request_id}")

        except Exception as e:
            self.logger.error(f"Failed to send approval notification: {e}")

    async def _send_email_notification(self, data: Dict[str, Any]):
        """Send email approval notification"""
        # Placeholder for email integration
        self.logger.info(f"Email notification sent to {data['approver']} for {data['gate_name']}")

    async def _send_slack_notification(self, data: Dict[str, Any]):
        """Send Slack approval notification"""
        # Placeholder for Slack integration
        self.logger.info(f"Slack notification sent to {data['approver']} for {data['gate_name']}")

    async def process_approval_response(self, request_id: str, response: str, approver: str, comments: str = None) -> bool:
        """Process approval response from approver"""

        if request_id not in self.pending_approvals:
            raise ValueError(f"Approval request {request_id} not found")

        request = self.pending_approvals[request_id]

        # Validate approver
        if request.approver != approver:
            raise ValueError(f"Invalid approver {approver} for request {request_id}")

        # Validate response
        if response not in ["approved", "rejected"]:
            raise ValueError(f"Invalid response {response}. Must be 'approved' or 'rejected'")

        # Update request
        request.responded_at = datetime.now()
        request.response = response
        request.comments = comments

        # Move to history
        self.approval_history.append(request)
        del self.pending_approvals[request_id]

        self.logger.info(f"Processed approval response: {response} from {approver} for request {request_id}")

        return response == "approved"

    async def check_gate_approval_status(self, gate: ApprovalGate) -> Tuple[ApprovalStatus, str]:
        """Check overall approval status for a gate"""

        # Check if already approved/rejected
        if gate.status in [
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.AUTO_APPROVED,
        ]:
            return gate.status, "Gate already processed"

        # Check expiration
        if datetime.now() > gate.expires_at:
            gate.status = ApprovalStatus.EXPIRED
            return ApprovalStatus.EXPIRED, "Approval gate expired"

        # Count approvals and rejections
        approvals = 0
        rejections = 0

        for approval_data in gate.approvals:
            if approval_data.get("response") == "approved":
                approvals += 1
            elif approval_data.get("response") == "rejected":
                rejections += 1

        # Check if any rejection (fail-fast)
        if rejections > 0:
            gate.status = ApprovalStatus.REJECTED
            return ApprovalStatus.REJECTED, f"Gate rejected by {rejections} approver(s)"

        # Check if all required approvals received
        required_count = len(gate.required_approvers)
        if approvals >= required_count:
            gate.status = ApprovalStatus.APPROVED
            gate.approved_at = datetime.now()
            return (
                ApprovalStatus.APPROVED,
                f"Gate approved by {approvals}/{required_count} approvers",
            )

        # Still pending
        return (
            ApprovalStatus.PENDING,
            f"Waiting for {required_count - approvals} more approval(s)",
        )

    async def update_gate_approvals(self, gate: ApprovalGate, request_id: str, response: str, approver: str):
        """Update gate with approval response"""

        approval_data = {
            "request_id": request_id,
            "approver": approver,
            "response": response,
            "timestamp": datetime.now().isoformat(),
        }

        gate.approvals.append(approval_data)

        # Update gate status
        status, message = await self.check_gate_approval_status(gate)

        self.logger.info(f"Updated gate {gate.gate_id}: {message}")

        return status

    async def cleanup_expired_gates(self):
        """Clean up expired approval gates"""

        expired_count = 0
        current_time = datetime.now()

        # Clean up pending requests
        expired_requests = []
        for request_id, request in self.pending_approvals.items():
            # Find corresponding gate expiration (simplified lookup)
            if current_time > (request.created_at + timedelta(hours=24)):  # 24-hour cleanup
                expired_requests.append(request_id)

        for request_id in expired_requests:
            request = self.pending_approvals[request_id]
            self.approval_history.append(request)
            del self.pending_approvals[request_id]
            expired_count += 1

        if expired_count > 0:
            self.logger.info(f"Cleaned up {expired_count} expired approval requests")

        return expired_count

    def get_pending_approvals_for_user(self, approver: str) -> List[ApprovalRequest]:
        """Get pending approval requests for a specific user"""

        user_approvals = []
        for request in self.pending_approvals.values():
            if request.approver == approver and request.responded_at is None:
                user_approvals.append(request)

        return user_approvals

    def get_approval_statistics(self) -> Dict[str, Any]:
        """Get approval system statistics"""

        total_requests = len(self.pending_approvals) + len(self.approval_history)
        approved_count = len([r for r in self.approval_history if r.response == "approved"])
        rejected_count = len([r for r in self.approval_history if r.response == "rejected"])
        pending_count = len(self.pending_approvals)

        # Calculate average response time
        response_times = []
        for request in self.approval_history:
            if request.responded_at and request.created_at:
                response_time = (request.responded_at - request.created_at).total_seconds() / 60  # minutes
                response_times.append(response_time)

        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        return {
            "total_requests": total_requests,
            "approved": approved_count,
            "rejected": rejected_count,
            "pending": pending_count,
            "approval_rate": (approved_count / total_requests * 100) if total_requests > 0 else 0,
            "average_response_time_minutes": round(avg_response_time, 2),
            "auto_approval_rules": self.auto_approval_rules,
        }
