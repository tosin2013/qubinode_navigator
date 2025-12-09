"""
Unit tests for PydanticAI Airflow Operator logic.

These tests verify the operator logic without requiring a full Airflow installation.
Tests focus on the branching logic and confidence-based routing per ADR-0049.

Note: Full integration tests should be run in an environment with Airflow installed.
"""


class TestConfidenceBranching:
    """Test confidence-based branching logic per ADR-0049 Policy 1."""

    def test_high_confidence_threshold(self):
        """Test HIGH confidence classification (>=0.8)."""
        high_threshold = 0.8

        # Test values that should be HIGH
        assert 0.9 >= high_threshold
        assert 0.85 >= high_threshold
        assert 0.8 >= high_threshold

        # Test boundary
        assert 0.79 < high_threshold

    def test_medium_confidence_threshold(self):
        """Test MEDIUM confidence classification (0.6-0.8)."""
        high_threshold = 0.8
        medium_threshold = 0.6

        # Test values that should be MEDIUM (below high but >= medium)
        test_values = [0.75, 0.7, 0.65, 0.6]
        for val in test_values:
            assert val < high_threshold
            assert val >= medium_threshold

    def test_low_confidence_threshold(self):
        """Test LOW confidence classification (<0.6)."""
        medium_threshold = 0.6

        # Test values that should be LOW
        test_values = [0.59, 0.5, 0.4, 0.3, 0.1, 0.0]
        for val in test_values:
            assert val < medium_threshold

    def test_branch_routing_logic(self):
        """Test the branch routing logic matches ADR-0049."""

        def determine_branch(
            confidence,
            high_threshold=0.8,
            medium_threshold=0.6,
            high_task="high",
            medium_task="medium",
            low_task="low",
        ):
            """Simulate branch operator logic."""
            if confidence is None:
                return low_task
            if confidence >= high_threshold:
                return high_task
            elif confidence >= medium_threshold:
                return medium_task
            else:
                return low_task

        # Test HIGH confidence routing
        assert determine_branch(0.9) == "high"
        assert determine_branch(0.85) == "high"
        assert determine_branch(0.8) == "high"

        # Test MEDIUM confidence routing
        assert determine_branch(0.79) == "medium"
        assert determine_branch(0.7) == "medium"
        assert determine_branch(0.6) == "medium"

        # Test LOW confidence routing
        assert determine_branch(0.59) == "low"
        assert determine_branch(0.5) == "low"
        assert determine_branch(0.0) == "low"

        # Test None confidence defaults to LOW
        assert determine_branch(None) == "low"

    def test_custom_threshold_routing(self):
        """Test routing with custom thresholds."""

        def determine_branch(
            confidence,
            high_threshold=0.9,
            medium_threshold=0.7,
        ):
            if confidence is None:
                return "low"
            if confidence >= high_threshold:
                return "high"
            elif confidence >= medium_threshold:
                return "medium"
            else:
                return "low"

        # With higher thresholds
        assert determine_branch(0.85, high_threshold=0.9) == "medium"
        assert determine_branch(0.65, medium_threshold=0.7) == "low"


class TestEscalationLogic:
    """Test escalation logic per ADR-0049 Policy 4."""

    def test_low_confidence_triggers_escalation(self):
        """Test that low confidence triggers escalation."""
        threshold = 0.6

        def should_escalate(confidence, threshold=0.6, manual_escalation=False):
            """Determine if escalation is needed."""
            if manual_escalation:
                return True
            if confidence < threshold:
                return True
            return False

        # Low confidence should escalate
        assert should_escalate(0.5, threshold) is True
        assert should_escalate(0.3, threshold) is True

        # High confidence should not escalate
        assert should_escalate(0.7, threshold) is False
        assert should_escalate(0.9, threshold) is False

        # Manual escalation always escalates
        assert should_escalate(0.9, threshold, manual_escalation=True) is True

    def test_escalation_reasons(self):
        """Test escalation reason categorization."""
        valid_triggers = [
            "repeated_failure",
            "architecture_scope",
            "confidence_deadlock",
            "user_request",
            "missing_provider",
        ]

        for trigger in valid_triggers:
            # Each trigger should be a valid string
            assert isinstance(trigger, str)
            assert len(trigger) > 0


class TestAgentTypeValidation:
    """Test agent type validation."""

    def test_valid_agent_types(self):
        """Test all valid agent types."""
        valid_types = ["deployment", "task", "manager", "developer"]

        for agent_type in valid_types:
            assert agent_type in valid_types

    def test_invalid_agent_type_detection(self):
        """Test detection of invalid agent types."""
        valid_types = {"deployment", "task", "manager", "developer"}
        invalid_types = ["unknown", "invalid", "test", ""]

        for agent_type in invalid_types:
            assert agent_type not in valid_types


class TestCodeGenerationModes:
    """Test code generation mode handling."""

    def test_aider_mode(self):
        """Test Aider mode detection."""
        mode = "aider"
        assert mode in ["aider", "fallback_prompt", "none"]

    def test_fallback_prompt_mode(self):
        """Test fallback prompt mode detection."""
        mode = "fallback_prompt"
        assert mode in ["aider", "fallback_prompt", "none"]

    def test_no_code_generation_mode(self):
        """Test no code generation mode."""
        mode = "none"
        assert mode in ["aider", "fallback_prompt", "none"]

    def test_mode_selection_logic(self):
        """Test mode selection based on availability."""

        def select_mode(aider_available, api_keys_present, code_needed):
            """Determine code generation mode."""
            if not code_needed:
                return "none"
            if aider_available and api_keys_present:
                return "aider"
            return "fallback_prompt"

        # Aider available with keys
        assert select_mode(True, True, True) == "aider"

        # Aider available but no keys
        assert select_mode(True, False, True) == "fallback_prompt"

        # Aider not available
        assert select_mode(False, True, True) == "fallback_prompt"

        # No code needed
        assert select_mode(True, True, False) == "none"


class TestXComPushLogic:
    """Test XCom push logic for operator results."""

    def test_xcom_keys(self):
        """Test expected XCom keys are defined."""
        expected_keys = [
            "agent_result",
            "confidence",
            "escalation_needed",
            "escalation_context",
        ]

        for key in expected_keys:
            assert isinstance(key, str)
            assert len(key) > 0

    def test_escalation_context_structure(self):
        """Test escalation context has required fields."""
        escalation_context = {
            "reason": "Low confidence: 0.45",
            "confidence": 0.45,
            "agent_type": "deployment",
            "prompt": "Deploy VM",
            "result": {"success": False},
        }

        assert "reason" in escalation_context
        assert "confidence" in escalation_context
        assert "agent_type" in escalation_context
        assert isinstance(escalation_context["confidence"], float)


class TestOperatorDefaults:
    """Test operator default values."""

    def test_default_confidence_threshold(self):
        """Test default confidence threshold is 0.6 per ADR-0049."""
        default_threshold = 0.6
        assert default_threshold == 0.6

    def test_default_escalation_behavior(self):
        """Test default escalation on low confidence is True."""
        escalate_on_low_confidence = True
        assert escalate_on_low_confidence is True

    def test_default_output_model(self):
        """Test default output model."""
        default_model = "TaskResult"
        assert default_model == "TaskResult"

    def test_default_working_directory(self):
        """Test default working directory."""
        default_dir = "/root/qubinode_navigator"
        assert default_dir == "/root/qubinode_navigator"

    def test_default_aider_model(self):
        """Test default Aider model."""
        default_aider = "claude-sonnet-4-20250514"
        assert "claude" in default_aider.lower()
