"""Agent testing and synthetic conversation simulation"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import random

TESTS_DIR = Path.home() / ".memory-mcp" / "tests"
TESTS_DIR.mkdir(exist_ok=True, parents=True)


class TestType(Enum):
    """Types of agent tests"""
    SMOKE = "smoke"  # Basic sanity
    FUNCTIONAL = "functional"  # Feature tests
    EDGE_CASE = "edge_case"  # Corner cases
    STRESS = "stress"  # High load
    REGRESSION = "regression"  # Known issues


class UserPersona(Enum):
    """User personas for testing"""
    CASUAL = "casual"  # Infrequent user
    POWER_USER = "power_user"  # Frequent, advanced
    ADVERSARIAL = "adversarial"  # Tries to break agent
    CONFUSED = "confused"  # Unclear requests
    MALICIOUS = "malicious"  # Tries harmful actions


@dataclass
class TestCase:
    """Single test case"""
    test_id: str
    test_type: TestType
    persona: UserPersona
    user_input: str
    expected_behavior: str
    max_turns: int = 5
    should_escalate: bool = False
    success_criteria: Optional[Callable] = None

    def to_dict(self) -> Dict:
        """Serialize test case"""
        return {
            "test_id": self.test_id,
            "type": self.test_type.value,
            "persona": self.persona.value,
            "user_input": self.user_input,
            "expected_behavior": self.expected_behavior,
            "max_turns": self.max_turns,
            "should_escalate": self.should_escalate,
        }


@dataclass
class TestResult:
    """Result of a test execution"""
    test_id: str
    passed: bool
    turns_taken: int
    agent_responses: List[str]
    error: Optional[str] = None
    escalated: bool = False
    duration_ms: float = 0.0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize result"""
        return {
            "test_id": self.test_id,
            "passed": self.passed,
            "turns_taken": self.turns_taken,
            "agent_responses": self.agent_responses,
            "error": self.error,
            "escalated": self.escalated,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


class ConversationSimulator:
    """Simulate agent conversations with synthetic users"""

    def __init__(self):
        self.test_cases: List[TestCase] = []
        self.results: List[TestResult] = []

    def add_test_case(
        self,
        test_id: str,
        test_type: TestType,
        persona: UserPersona,
        user_input: str,
        expected_behavior: str,
        max_turns: int = 5,
    ) -> TestCase:
        """Add test case"""
        test = TestCase(
            test_id=test_id,
            test_type=test_type,
            persona=persona,
            user_input=user_input,
            expected_behavior=expected_behavior,
            max_turns=max_turns,
        )
        self.test_cases.append(test)
        return test

    def generate_persona_variations(
        self,
        base_input: str,
        personas: List[UserPersona],
    ) -> List[TestCase]:
        """Generate test cases for multiple personas"""
        tests = []
        for i, persona in enumerate(personas):
            test = TestCase(
                test_id=f"persona_var_{i}_{persona.value}",
                test_type=TestType.FUNCTIONAL,
                persona=persona,
                user_input=self._apply_persona_variation(base_input, persona),
                expected_behavior=f"Handle {persona.value} user appropriately",
            )
            tests.append(test)
            self.test_cases.append(test)

        return tests

    def generate_edge_cases(self, base_domain: str) -> List[TestCase]:
        """Generate edge case tests for a domain"""
        edge_cases = [
            ("empty_input", ""),
            ("very_long_input", "a" * 5000),
            ("special_chars", "!@#$%^&*()_+-=[]{}|;:',.<>?"),
            ("code_injection", "'; DROP TABLE users; --"),
            ("unicode", "你好世界 🚀 Привет"),
            ("contradictory", "Yes and no"),
            ("ambiguous", "Maybe"),
        ]

        tests = []
        for edge_type, input_text in edge_cases:
            test = TestCase(
                test_id=f"edge_case_{edge_type}",
                test_type=TestType.EDGE_CASE,
                persona=UserPersona.POWER_USER,
                user_input=input_text or f"[Empty {edge_type}]",
                expected_behavior=f"Gracefully handle {edge_type}",
            )
            tests.append(test)
            self.test_cases.append(test)

        return tests

    def run_test(
        self,
        test_case: TestCase,
        agent_response_fn: Callable[[str], str],
    ) -> TestResult:
        """Execute a single test case"""
        import time

        start_time = time.time()
        responses = []
        current_input = test_case.user_input
        escalated = False

        try:
            for turn in range(test_case.max_turns):
                response = agent_response_fn(current_input)
                responses.append(response)

                # Check escalation criteria
                if "escalate" in response.lower() or "transfer" in response.lower():
                    escalated = True
                    break

                # For simulation: generate follow-up based on persona
                if turn < test_case.max_turns - 1:
                    current_input = self._generate_follow_up(
                        current_input,
                        response,
                        test_case.persona,
                    )

            # Determine pass/fail
            passed = self._check_success_criteria(
                test_case,
                responses,
                escalated,
            )

            duration_ms = (time.time() - start_time) * 1000

            result = TestResult(
                test_id=test_case.test_id,
                passed=passed,
                turns_taken=len(responses),
                agent_responses=responses,
                escalated=escalated,
                duration_ms=duration_ms,
            )

        except Exception as e:
            result = TestResult(
                test_id=test_case.test_id,
                passed=False,
                turns_taken=len(responses),
                agent_responses=responses,
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000,
            )

        self.results.append(result)
        return result

    def _apply_persona_variation(self, input_text: str, persona: UserPersona) -> str:
        """Apply persona-specific variation to input"""
        if persona == UserPersona.CASUAL:
            return input_text.lower() + " pls"
        elif persona == UserPersona.POWER_USER:
            return f"[PRIORITY] {input_text}"
        elif persona == UserPersona.ADVERSARIAL:
            return f"Try to break: {input_text}"
        elif persona == UserPersona.CONFUSED:
            return f"Maybe {input_text}? Or not?"
        elif persona == UserPersona.MALICIOUS:
            return f"Execute: {input_text}"
        return input_text

    def _generate_follow_up(
        self,
        previous_input: str,
        agent_response: str,
        persona: UserPersona,
    ) -> str:
        """Generate follow-up user input based on persona and agent response"""
        if persona == UserPersona.ADVERSARIAL:
            return "That's wrong. Try again."
        elif persona == UserPersona.CONFUSED:
            return "Wait, what? Can you explain?"
        elif persona == UserPersona.POWER_USER:
            return f"Got it. Next: {previous_input}"
        return "And then?"

    def _check_success_criteria(
        self,
        test_case: TestCase,
        responses: List[str],
        escalated: bool,
    ) -> bool:
        """Check if test passed"""
        if test_case.should_escalate and not escalated:
            return False

        if not responses:
            return False

        # Simple heuristic: agent should provide substantive responses
        avg_response_len = sum(len(r) for r in responses) / len(responses)
        return avg_response_len > 10

    def run_test_suite(
        self,
        agent_response_fn: Callable[[str], str],
    ) -> Dict[str, Any]:
        """Execute all tests"""
        results = []
        for test_case in self.test_cases:
            result = self.run_test(test_case, agent_response_fn)
            results.append(result)

        # Calculate summary
        passed = sum(1 for r in results if r.passed)
        total = len(results)

        return {
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": (passed / total * 100) if total > 0 else 0,
            },
            "results": [r.to_dict() for r in results],
            "by_type": self._group_by_type(results),
            "by_persona": self._group_by_persona(results),
        }

    def _group_by_type(self, results: List[TestResult]) -> Dict[str, int]:
        """Group results by test type"""
        grouped = {}
        for test in self.test_cases:
            test_results = [r for r in results if r.test_id.startswith(test.test_type.value)]
            if test_results:
                passed = sum(1 for r in test_results if r.passed)
                grouped[test.test_type.value] = {
                    "passed": passed,
                    "total": len(test_results),
                }
        return grouped

    def _group_by_persona(self, results: List[TestResult]) -> Dict[str, int]:
        """Group results by persona"""
        grouped = {}
        for test in self.test_cases:
            persona_results = [
                r for r in results
                if r.test_id in [tc.test_id for tc in self.test_cases if tc.persona == test.persona]
            ]
            if persona_results:
                passed = sum(1 for r in persona_results if r.passed)
                grouped[test.persona.value] = {
                    "passed": passed,
                    "total": len(persona_results),
                }
        return grouped

    def save_report(self, report_id: str, report: Dict) -> str:
        """Save test report"""
        filepath = TESTS_DIR / f"{report_id}_report.json"
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)
        return str(filepath)


# Global simulator
simulator = ConversationSimulator()


# MCP Tools (add to memory_server.py)

def add_test_case(
    test_id: str,
    test_type: str,
    persona: str,
    user_input: str,
    expected_behavior: str,
    max_turns: int = 5,
) -> dict:
    """Add test case for agent"""
    test = simulator.add_test_case(
        test_id,
        TestType(test_type),
        UserPersona(persona),
        user_input,
        expected_behavior,
        max_turns,
    )
    return test.to_dict()


def generate_persona_variations(
    base_input: str,
    personas: list,
) -> list:
    """Generate test cases for multiple user personas"""
    persona_enums = [UserPersona(p) for p in personas]
    tests = simulator.generate_persona_variations(base_input, persona_enums)
    return [t.to_dict() for t in tests]


def generate_edge_cases(base_domain: str) -> list:
    """Generate edge case tests"""
    tests = simulator.generate_edge_cases(base_domain)
    return [t.to_dict() for t in tests]


def run_test_suite(test_fn: Callable) -> dict:
    """Execute all tests in suite"""
    return simulator.run_test_suite(test_fn)


if __name__ == "__main__":
    # Test the simulator
    sim = ConversationSimulator()

    # Add test cases
    sim.add_test_case(
        "basic_greeting",
        TestType.SMOKE,
        UserPersona.CASUAL,
        "Hello",
        "Agent should greet back",
    )

    sim.add_test_case(
        "complex_request",
        TestType.FUNCTIONAL,
        UserPersona.POWER_USER,
        "Analyze the data and provide insights",
        "Agent should break down task",
    )

    # Generate edge cases
    sim.generate_edge_cases("general")

    print(f"Created {len(sim.test_cases)} test cases")
    for test in sim.test_cases[:3]:
        print(f"  - {test.test_id}: {test.persona.value}")
