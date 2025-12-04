"""
Qubinode Navigator AI-Powered Update Management Integration

This module integrates the AI Assistant with update management, providing
intelligent analysis, risk assessment, and automated decision-making for
update planning and execution.

Based on ADR-0030: Software and OS Update Strategy
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import requests
from enum import Enum

from core.update_manager import UpdateDetector, UpdateInfo, UpdateBatch
from core.compatibility_manager import CompatibilityManager, CompatibilityLevel
from core.update_validator import UpdateValidator


class RiskLevel(Enum):
    """AI-assessed risk levels for updates"""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UpdateRecommendation(Enum):
    """AI update recommendations"""

    APPLY_IMMEDIATELY = "apply_immediately"
    APPLY_WITH_TESTING = "apply_with_testing"
    SCHEDULE_MAINTENANCE = "schedule_maintenance"
    DEFER_UPDATE = "defer_update"
    BLOCK_UPDATE = "block_update"


@dataclass
class AIAnalysis:
    """AI analysis result for an update or batch"""

    analysis_id: str
    component_name: str
    component_version: str
    risk_level: RiskLevel
    recommendation: UpdateRecommendation
    confidence_score: float  # 0.0 to 1.0
    reasoning: str
    security_impact: str
    compatibility_concerns: List[str]
    testing_recommendations: List[str]
    rollback_strategy: str
    estimated_downtime: Optional[str] = None
    dependencies_impact: List[str] = None
    business_impact: str = ""
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.dependencies_impact is None:
            self.dependencies_impact = []


@dataclass
class UpdatePlan:
    """AI-generated update execution plan"""

    plan_id: str
    batch_id: str
    execution_strategy: str  # immediate, staged, maintenance_window
    total_estimated_time: str
    phases: List[Dict[str, Any]]
    risk_mitigation_steps: List[str]
    rollback_plan: Dict[str, Any]
    monitoring_points: List[str]
    approval_required: bool
    created_at: datetime
    ai_confidence: float


class AIUpdateManager:
    """
    AI-Powered Update Management Integration

    Integrates AI Assistant with update management to provide intelligent
    analysis, risk assessment, and automated decision-making for updates.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Configuration
        self.ai_assistant_url = self.config.get("ai_assistant_url", "http://localhost:8080")
        self.ai_timeout = self.config.get("ai_timeout", 30)
        self.enable_ai_analysis = self.config.get("enable_ai_analysis", True)
        self.risk_threshold = self.config.get("risk_threshold", "medium")
        self.auto_approval_threshold = self.config.get("auto_approval_threshold", 0.8)

        # State
        self.ai_analyses: Dict[str, AIAnalysis] = {}
        self.update_plans: Dict[str, UpdatePlan] = {}

        # Initialize components
        self.update_detector = UpdateDetector(config)
        self.compatibility_manager = CompatibilityManager(config)
        self.update_validator = UpdateValidator(config)

        # AI analysis cache
        self.analysis_cache = {}
        self.cache_ttl = 3600  # 1 hour

    async def analyze_update_with_ai(self, update_info: UpdateInfo) -> AIAnalysis:
        """Analyze a single update using AI Assistant"""
        analysis_id = f"ai_analysis_{update_info.component_name}_{update_info.available_version}_{int(time.time())}"

        # Check cache first
        cache_key = f"{update_info.component_name}_{update_info.available_version}"
        if cache_key in self.analysis_cache:
            cached_analysis, timestamp = self.analysis_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                self.logger.info(f"Using cached AI analysis for {update_info.component_name}")
                return cached_analysis

        if not self.enable_ai_analysis:
            return self._create_fallback_analysis(analysis_id, update_info)

        try:
            # Get compatibility information
            (
                compatibility_level,
                compatibility_reason,
            ) = await self.compatibility_manager.validate_compatibility(
                update_info.component_name,
                update_info.available_version,
                "10",  # Default OS version
            )

            # Prepare AI prompt
            prompt = self._create_analysis_prompt(update_info, compatibility_level, compatibility_reason)

            # Call AI Assistant
            ai_response = await self._call_ai_assistant(prompt)

            # Parse AI response
            analysis = self._parse_ai_analysis(analysis_id, update_info, ai_response)

            # Cache the analysis
            self.analysis_cache[cache_key] = (analysis, time.time())

            # Store analysis
            self.ai_analyses[analysis_id] = analysis

            self.logger.info(f"AI analysis completed for {update_info.component_name}: {analysis.risk_level.value}")
            return analysis

        except Exception as e:
            self.logger.error(f"AI analysis failed for {update_info.component_name}: {e}")
            return self._create_fallback_analysis(analysis_id, update_info)

    def _create_analysis_prompt(
        self,
        update_info: UpdateInfo,
        compatibility_level: CompatibilityLevel,
        compatibility_reason: str,
    ) -> str:
        """Create AI analysis prompt"""
        prompt = f"""
Analyze this software update for risk assessment and provide recommendations:

COMPONENT INFORMATION:
- Component: {update_info.component_name}
- Type: {update_info.component_type}
- Current Version: {update_info.current_version}
- Available Version: {update_info.available_version}
- Severity: {update_info.severity}
- Description: {update_info.description}
- Release Date: {update_info.release_date}

COMPATIBILITY ASSESSMENT:
- Compatibility Level: {compatibility_level.value}
- Compatibility Reason: {compatibility_reason}

SECURITY INFORMATION:
- Security Advisories: {', '.join(update_info.security_advisories) if update_info.security_advisories else 'None'}

Please provide a comprehensive analysis including:

1. RISK LEVEL (very_low, low, medium, high, critical)
2. RECOMMENDATION (apply_immediately, apply_with_testing, schedule_maintenance, defer_update, block_update)
3. CONFIDENCE SCORE (0.0 to 1.0)
4. REASONING (detailed explanation of the assessment)
5. SECURITY IMPACT (potential security implications)
6. COMPATIBILITY CONCERNS (potential compatibility issues)
7. TESTING RECOMMENDATIONS (specific tests to perform)
8. ROLLBACK STRATEGY (how to rollback if needed)
9. ESTIMATED DOWNTIME (if any)
10. DEPENDENCIES IMPACT (impact on other components)
11. BUSINESS IMPACT (operational impact)

Focus on infrastructure automation, container orchestration, and system reliability.
Consider the component's role in the Qubinode Navigator ecosystem.

Respond in JSON format with these exact field names:
{{
    "risk_level": "medium",
    "recommendation": "apply_with_testing",
    "confidence_score": 0.85,
    "reasoning": "...",
    "security_impact": "...",
    "compatibility_concerns": ["...", "..."],
    "testing_recommendations": ["...", "..."],
    "rollback_strategy": "...",
    "estimated_downtime": "...",
    "dependencies_impact": ["...", "..."],
    "business_impact": "..."
}}
"""
        return prompt

    async def _call_ai_assistant(self, prompt: str) -> Dict[str, Any]:
        """Call AI Assistant for analysis"""
        try:
            payload = {
                "message": prompt,
                "context": {
                    "type": "update_analysis",
                    "timestamp": datetime.now().isoformat(),
                },
            }

            response = requests.post(
                f"{self.ai_assistant_url}/chat",
                json=payload,
                timeout=self.ai_timeout,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                return result
            else:
                raise Exception(f"AI Assistant returned status {response.status_code}")

        except requests.exceptions.Timeout:
            raise Exception("AI Assistant request timed out")
        except requests.exceptions.ConnectionError:
            raise Exception("Could not connect to AI Assistant")
        except Exception as e:
            raise Exception(f"AI Assistant call failed: {e}")

    def _parse_ai_analysis(self, analysis_id: str, update_info: UpdateInfo, ai_response: Dict[str, Any]) -> AIAnalysis:
        """Parse AI response into AIAnalysis object"""
        try:
            # Extract AI response text
            ai_text = ai_response.get("text", "")

            # Try to extract JSON from the response
            json_start = ai_text.find("{")
            json_end = ai_text.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_text = ai_text[json_start:json_end]
                ai_data = json.loads(json_text)
            else:
                # Fallback parsing if no JSON found
                ai_data = self._extract_analysis_from_text(ai_text)

            return AIAnalysis(
                analysis_id=analysis_id,
                component_name=update_info.component_name,
                component_version=update_info.available_version,
                risk_level=RiskLevel(ai_data.get("risk_level", "medium")),
                recommendation=UpdateRecommendation(ai_data.get("recommendation", "apply_with_testing")),
                confidence_score=float(ai_data.get("confidence_score", 0.7)),
                reasoning=ai_data.get("reasoning", "AI analysis completed"),
                security_impact=ai_data.get("security_impact", "No specific security impact identified"),
                compatibility_concerns=ai_data.get("compatibility_concerns", []),
                testing_recommendations=ai_data.get("testing_recommendations", []),
                rollback_strategy=ai_data.get("rollback_strategy", "Standard rollback procedure"),
                estimated_downtime=ai_data.get("estimated_downtime"),
                dependencies_impact=ai_data.get("dependencies_impact", []),
                business_impact=ai_data.get("business_impact", "Minimal business impact expected"),
            )

        except Exception as e:
            self.logger.error(f"Failed to parse AI analysis: {e}")
            return self._create_fallback_analysis(analysis_id, update_info)

    def _extract_analysis_from_text(self, text: str) -> Dict[str, Any]:
        """Extract analysis data from unstructured text"""
        # Simple text parsing fallback
        analysis = {
            "risk_level": "medium",
            "recommendation": "apply_with_testing",
            "confidence_score": 0.6,
            "reasoning": "Text-based analysis performed",
            "security_impact": "Standard security considerations apply",
            "compatibility_concerns": [],
            "testing_recommendations": ["Perform standard validation tests"],
            "rollback_strategy": "Use system rollback mechanisms",
            "estimated_downtime": "Minimal downtime expected",
            "dependencies_impact": [],
            "business_impact": "Standard update impact",
        }

        # Extract risk level from text
        text_lower = text.lower()
        if any(word in text_lower for word in ["critical", "severe", "major"]):
            analysis["risk_level"] = "high"
        elif any(word in text_lower for word in ["security", "vulnerability", "patch"]):
            analysis["risk_level"] = "medium"
            analysis["recommendation"] = "apply_immediately"
        elif any(word in text_lower for word in ["minor", "safe", "low risk"]):
            analysis["risk_level"] = "low"

        return analysis

    def _create_fallback_analysis(self, analysis_id: str, update_info: UpdateInfo) -> AIAnalysis:
        """Create fallback analysis when AI is unavailable"""
        # Determine risk level based on update severity
        risk_mapping = {
            "critical": RiskLevel.HIGH,
            "security": RiskLevel.MEDIUM,
            "important": RiskLevel.MEDIUM,
            "moderate": RiskLevel.LOW,
            "low": RiskLevel.VERY_LOW,
        }

        risk_level = risk_mapping.get(update_info.severity.lower(), RiskLevel.MEDIUM)

        # Determine recommendation based on risk and security advisories
        if update_info.security_advisories:
            recommendation = UpdateRecommendation.APPLY_WITH_TESTING
        elif risk_level in [RiskLevel.VERY_LOW, RiskLevel.LOW]:
            recommendation = UpdateRecommendation.SCHEDULE_MAINTENANCE
        else:
            recommendation = UpdateRecommendation.APPLY_WITH_TESTING

        return AIAnalysis(
            analysis_id=analysis_id,
            component_name=update_info.component_name,
            component_version=update_info.available_version,
            risk_level=risk_level,
            recommendation=recommendation,
            confidence_score=0.6,  # Lower confidence for fallback
            reasoning=f"Fallback analysis based on severity: {update_info.severity}",
            security_impact="Security impact assessed based on advisories" if update_info.security_advisories else "No security advisories",
            compatibility_concerns=["Compatibility not verified by AI"],
            testing_recommendations=[
                "Perform standard validation tests",
                "Monitor system after update",
            ],
            rollback_strategy="Use system package manager rollback",
            estimated_downtime="5-15 minutes",
            dependencies_impact=[],
            business_impact="Standard update impact expected",
        )

    async def analyze_update_batch(self, batch: UpdateBatch) -> Dict[str, AIAnalysis]:
        """Analyze an entire update batch with AI"""
        batch_analyses = {}

        self.logger.info(f"Starting AI analysis for batch {batch.batch_id} with {len(batch.updates)} updates")

        # Analyze each update in the batch
        for update in batch.updates:
            try:
                analysis = await self.analyze_update_with_ai(update)
                batch_analyses[update.component_name] = analysis

                # Add small delay to avoid overwhelming AI Assistant
                await asyncio.sleep(0.5)

            except Exception as e:
                self.logger.error(f"Failed to analyze {update.component_name}: {e}")
                # Create fallback analysis
                fallback = self._create_fallback_analysis(f"fallback_{update.component_name}_{int(time.time())}", update)
                batch_analyses[update.component_name] = fallback

        self.logger.info(f"Completed AI analysis for batch {batch.batch_id}")
        return batch_analyses

    async def create_update_plan(self, batch: UpdateBatch, analyses: Dict[str, AIAnalysis]) -> UpdatePlan:
        """Create AI-guided update execution plan"""
        plan_id = f"plan_{batch.batch_id}_{int(time.time())}"

        # Analyze overall risk and determine strategy
        risk_levels = [analysis.risk_level for analysis in analyses.values()]
        max_risk = max(risk_levels, key=lambda x: list(RiskLevel).index(x))

        # Determine execution strategy
        if max_risk in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            execution_strategy = "maintenance_window"
            approval_required = True
        elif max_risk == RiskLevel.MEDIUM:
            execution_strategy = "staged"
            approval_required = True
        else:
            execution_strategy = "immediate"
            approval_required = False

        # Calculate confidence score
        confidence_scores = [analysis.confidence_score for analysis in analyses.values()]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5

        # Create execution phases
        phases = self._create_execution_phases(batch, analyses, execution_strategy)

        # Generate risk mitigation steps
        risk_mitigation = self._generate_risk_mitigation_steps(analyses)

        # Create rollback plan
        rollback_plan = self._create_rollback_plan(batch, analyses)

        # Define monitoring points
        monitoring_points = self._define_monitoring_points(batch, analyses)

        # Estimate total time
        total_time = self._estimate_total_execution_time(phases)

        plan = UpdatePlan(
            plan_id=plan_id,
            batch_id=batch.batch_id,
            execution_strategy=execution_strategy,
            total_estimated_time=total_time,
            phases=phases,
            risk_mitigation_steps=risk_mitigation,
            rollback_plan=rollback_plan,
            monitoring_points=monitoring_points,
            approval_required=approval_required,
            created_at=datetime.now(),
            ai_confidence=avg_confidence,
        )

        self.update_plans[plan_id] = plan
        self.logger.info(f"Created update plan {plan_id} with strategy: {execution_strategy}")

        return plan

    def _create_execution_phases(self, batch: UpdateBatch, analyses: Dict[str, AIAnalysis], strategy: str) -> List[Dict[str, Any]]:
        """Create execution phases based on strategy and risk analysis"""
        phases = []

        if strategy == "immediate":
            # Single phase for low-risk updates
            phases.append(
                {
                    "phase_id": "immediate_execution",
                    "name": "Immediate Update Execution",
                    "updates": [update.component_name for update in batch.updates],
                    "estimated_duration": "15-30 minutes",
                    "parallel_execution": True,
                    "validation_required": True,
                }
            )

        elif strategy == "staged":
            # Multiple phases for medium-risk updates
            # Phase 1: Low-risk updates
            low_risk_updates = [update.component_name for update in batch.updates if analyses[update.component_name].risk_level in [RiskLevel.VERY_LOW, RiskLevel.LOW]]

            if low_risk_updates:
                phases.append(
                    {
                        "phase_id": "stage_1_low_risk",
                        "name": "Stage 1: Low Risk Updates",
                        "updates": low_risk_updates,
                        "estimated_duration": "20-40 minutes",
                        "parallel_execution": True,
                        "validation_required": True,
                        "wait_period": "30 minutes",
                    }
                )

            # Phase 2: Medium and high-risk updates
            higher_risk_updates = [update.component_name for update in batch.updates if analyses[update.component_name].risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]]

            if higher_risk_updates:
                phases.append(
                    {
                        "phase_id": "stage_2_higher_risk",
                        "name": "Stage 2: Higher Risk Updates",
                        "updates": higher_risk_updates,
                        "estimated_duration": "30-60 minutes",
                        "parallel_execution": False,
                        "validation_required": True,
                        "approval_required": True,
                    }
                )

        elif strategy == "maintenance_window":
            # Careful sequential execution for high-risk updates
            phases.append(
                {
                    "phase_id": "maintenance_preparation",
                    "name": "Maintenance Window Preparation",
                    "updates": [],
                    "estimated_duration": "15 minutes",
                    "tasks": [
                        "System backup",
                        "Service status check",
                        "Notification sent",
                    ],
                }
            )

            phases.append(
                {
                    "phase_id": "maintenance_execution",
                    "name": "Maintenance Window Execution",
                    "updates": [update.component_name for update in batch.updates],
                    "estimated_duration": "45-90 minutes",
                    "parallel_execution": False,
                    "validation_required": True,
                    "approval_required": True,
                }
            )

            phases.append(
                {
                    "phase_id": "maintenance_verification",
                    "name": "Post-Maintenance Verification",
                    "updates": [],
                    "estimated_duration": "30 minutes",
                    "tasks": [
                        "System validation",
                        "Service verification",
                        "Performance check",
                    ],
                }
            )

        return phases

    def _generate_risk_mitigation_steps(self, analyses: Dict[str, AIAnalysis]) -> List[str]:
        """Generate risk mitigation steps based on analyses"""
        mitigation_steps = [
            "Create system backup before starting updates",
            "Verify all services are running normally",
            "Ensure rollback procedures are ready",
        ]

        # Add component-specific mitigations
        for component_name, analysis in analyses.items():
            if analysis.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                mitigation_steps.append(f"Extra validation for {component_name} due to high risk")

            if analysis.compatibility_concerns:
                mitigation_steps.append(f"Address compatibility concerns for {component_name}")

            if analysis.dependencies_impact:
                mitigation_steps.append(f"Monitor dependencies for {component_name}")

        return mitigation_steps

    def _create_rollback_plan(self, batch: UpdateBatch, analyses: Dict[str, AIAnalysis]) -> Dict[str, Any]:
        """Create comprehensive rollback plan"""
        return {
            "rollback_strategy": "Sequential rollback in reverse order of application",
            "rollback_triggers": [
                "Critical service failure",
                "System performance degradation > 20%",
                "User-reported issues > threshold",
                "Monitoring alerts triggered",
            ],
            "rollback_steps": [
                "Stop affected services",
                "Rollback packages using package manager",
                "Restore configuration files from backup",
                "Restart services in correct order",
                "Verify system functionality",
            ],
            "rollback_time_estimate": "20-45 minutes",
            "verification_steps": [
                "Check service status",
                "Verify system performance",
                "Confirm user access",
                "Validate monitoring metrics",
            ],
        }

    def _define_monitoring_points(self, batch: UpdateBatch, analyses: Dict[str, AIAnalysis]) -> List[str]:
        """Define monitoring points for update execution"""
        monitoring_points = [
            "System resource utilization (CPU, memory, disk)",
            "Service availability and response times",
            "Error rates and log anomalies",
            "Network connectivity and performance",
        ]

        # Add component-specific monitoring
        for update in batch.updates:
            if update.component_name == "podman":
                monitoring_points.append("Container runtime functionality")
            elif update.component_name == "ansible":
                monitoring_points.append("Ansible automation capabilities")
            elif update.component_name in ["kernel", "systemd"]:
                monitoring_points.append("Core system stability")

        return monitoring_points

    def _estimate_total_execution_time(self, phases: List[Dict[str, Any]]) -> str:
        """Estimate total execution time for all phases"""
        total_minutes = 0

        for phase in phases:
            duration_str = phase.get("estimated_duration", "30 minutes")
            # Extract maximum time estimate
            if "-" in duration_str:
                max_time = duration_str.split("-")[1]
            else:
                max_time = duration_str

            # Extract number
            time_parts = max_time.split()
            if time_parts and time_parts[0].isdigit():
                total_minutes += int(time_parts[0])

            # Add wait period if specified
            if "wait_period" in phase:
                wait_str = phase["wait_period"]
                wait_parts = wait_str.split()
                if wait_parts and wait_parts[0].isdigit():
                    total_minutes += int(wait_parts[0])

        if total_minutes < 60:
            return f"{total_minutes} minutes"
        else:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            return f"{hours}h {minutes}m"

    async def get_update_recommendations(self, updates: List[UpdateInfo]) -> Dict[str, Dict[str, Any]]:
        """Get AI recommendations for a list of updates"""
        recommendations = {}

        for update in updates:
            try:
                analysis = await self.analyze_update_with_ai(update)

                recommendations[update.component_name] = {
                    "recommendation": analysis.recommendation.value,
                    "risk_level": analysis.risk_level.value,
                    "confidence": analysis.confidence_score,
                    "reasoning": analysis.reasoning,
                    "should_auto_approve": (
                        analysis.confidence_score >= self.auto_approval_threshold
                        and analysis.risk_level in [RiskLevel.VERY_LOW, RiskLevel.LOW]
                        and analysis.recommendation
                        in [
                            UpdateRecommendation.APPLY_IMMEDIATELY,
                            UpdateRecommendation.APPLY_WITH_TESTING,
                        ]
                    ),
                }

            except Exception as e:
                self.logger.error(f"Failed to get recommendation for {update.component_name}: {e}")
                recommendations[update.component_name] = {
                    "recommendation": "apply_with_testing",
                    "risk_level": "medium",
                    "confidence": 0.5,
                    "reasoning": "Fallback recommendation due to analysis failure",
                    "should_auto_approve": False,
                }

        return recommendations

    async def generate_update_report(self, batch_id: str) -> Dict[str, Any]:
        """Generate comprehensive AI-powered update report"""
        if batch_id not in self.update_plans:
            raise ValueError(f"Update plan {batch_id} not found")

        plan = self.update_plans[batch_id]

        # Get analyses for this batch
        batch_analyses = {analysis.component_name: analysis for analysis in self.ai_analyses.values() if analysis.analysis_id.startswith("ai_analysis_") and batch_id in analysis.analysis_id}

        report = {
            "report_id": f"report_{batch_id}_{int(time.time())}",
            "batch_id": batch_id,
            "generated_at": datetime.now().isoformat(),
            "plan_summary": {
                "execution_strategy": plan.execution_strategy,
                "total_estimated_time": plan.total_estimated_time,
                "approval_required": plan.approval_required,
                "ai_confidence": plan.ai_confidence,
            },
            "risk_assessment": {
                "overall_risk": self._calculate_overall_risk(batch_analyses),
                "high_risk_components": [name for name, analysis in batch_analyses.items() if analysis.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]],
                "security_updates": [name for name, analysis in batch_analyses.items() if "security" in analysis.security_impact.lower()],
            },
            "recommendations": {
                name: {
                    "recommendation": analysis.recommendation.value,
                    "reasoning": analysis.reasoning,
                    "testing_recommendations": analysis.testing_recommendations,
                }
                for name, analysis in batch_analyses.items()
            },
            "execution_plan": {
                "phases": plan.phases,
                "risk_mitigation": plan.risk_mitigation_steps,
                "monitoring_points": plan.monitoring_points,
            },
            "rollback_plan": plan.rollback_plan,
        }

        return report

    def _calculate_overall_risk(self, analyses: Dict[str, AIAnalysis]) -> str:
        """Calculate overall risk level for a batch"""
        if not analyses:
            return "unknown"

        risk_levels = [analysis.risk_level for analysis in analyses.values()]

        if RiskLevel.CRITICAL in risk_levels:
            return "critical"
        elif RiskLevel.HIGH in risk_levels:
            return "high"
        elif RiskLevel.MEDIUM in risk_levels:
            return "medium"
        elif RiskLevel.LOW in risk_levels:
            return "low"
        else:
            return "very_low"
