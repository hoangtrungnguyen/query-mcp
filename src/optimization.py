"""Conversation optimization through pattern mining, heuristic learning, and A/B testing"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, Counter
import hashlib

OPTIMIZATION_DIR = Path.home() / ".memory-mcp" / "optimization"
OPTIMIZATION_DIR.mkdir(exist_ok=True, parents=True)


class PatternType(Enum):
    """Types of extractable patterns"""
    CONVERSATION_FLOW = "conversation_flow"  # Turn sequence patterns
    QUESTION_TYPE = "question_type"  # What questions succeed?
    RESPONSE_STYLE = "response_style"  # Effective response patterns
    TOOL_SEQUENCE = "tool_sequence"  # Tool usage patterns
    RECOVERY_PATTERN = "recovery_pattern"  # How to recover from errors
    ESCALATION_TRIGGER = "escalation_trigger"  # When to escalate


class ExperimentStatus(Enum):
    """A/B test lifecycle"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ConversationPattern:
    """Discovered conversation pattern"""
    pattern_id: str
    pattern_type: PatternType
    description: str
    occurrence_count: int
    success_rate: float
    confidence: float  # 0.0-1.0
    supporting_examples: List[str]  # Conversation IDs
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict:
        """Serialize pattern"""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.value,
            "description": self.description,
            "occurrence_count": self.occurrence_count,
            "success_rate": self.success_rate,
            "confidence": self.confidence,
            "supporting_examples": self.supporting_examples,
            "metadata": self.metadata,
        }


@dataclass
class Heuristic:
    """Learned heuristic from patterns"""
    heuristic_id: str
    title: str
    description: str
    condition: str  # When to apply
    action: str  # What to do
    expected_improvement: float  # % improvement
    derivation: str  # Which patterns led to this
    tested: bool = False

    def to_dict(self) -> Dict:
        """Serialize heuristic"""
        return {
            "heuristic_id": self.heuristic_id,
            "title": self.title,
            "description": self.description,
            "condition": self.condition,
            "action": self.action,
            "expected_improvement": self.expected_improvement,
            "derivation": self.derivation,
            "tested": self.tested,
        }


@dataclass
class ABExperiment:
    """A/B test for conversation improvements"""
    experiment_id: str
    name: str
    description: str
    control_variant: Dict[str, Any]  # Baseline
    test_variant: Dict[str, Any]  # Variant to test
    status: ExperimentStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    control_metrics: Dict[str, float] = None
    test_metrics: Dict[str, float] = None
    sample_size: int = 100

    def __post_init__(self):
        if self.control_metrics is None:
            self.control_metrics = {}
        if self.test_metrics is None:
            self.test_metrics = {}
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    @property
    def improvement(self) -> Optional[float]:
        """Calculate improvement percentage"""
        if not self.control_metrics or not self.test_metrics:
            return None

        control_score = self.control_metrics.get("success_rate", 0)
        test_score = self.test_metrics.get("success_rate", 0)

        if control_score == 0:
            return None

        return ((test_score - control_score) / control_score) * 100

    def to_dict(self) -> Dict:
        """Serialize experiment"""
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "control_metrics": self.control_metrics,
            "test_metrics": self.test_metrics,
            "improvement_percent": self.improvement,
            "sample_size": self.sample_size,
        }


class PatternMiner:
    """Extract patterns from conversation data"""

    @staticmethod
    def extract_turn_patterns(
        conversations: List[Dict],
        min_support: int = 3,
    ) -> List[ConversationPattern]:
        """Extract common conversation flow patterns"""
        patterns = []
        flow_sequences = defaultdict(list)

        for conv in conversations:
            messages = conv.get("messages", [])
            if len(messages) < 2:
                continue

            # Extract speaker sequence
            speakers = [m.get("speaker_id", "unknown") for m in messages]
            flow_key = tuple(speakers[:5])  # First 5 turns

            success = conv.get("success", True)
            flow_sequences[flow_key].append(success)

        for flow, outcomes in flow_sequences.items():
            if len(outcomes) >= min_support:
                success_rate = sum(outcomes) / len(outcomes)
                pattern = ConversationPattern(
                    pattern_id=f"flow_{hashlib.md5(str(flow).encode()).hexdigest()[:8]}",
                    pattern_type=PatternType.CONVERSATION_FLOW,
                    description=f"Conversation flow: {' → '.join(flow)}",
                    occurrence_count=len(outcomes),
                    success_rate=success_rate,
                    confidence=min(0.95, len(outcomes) / 100),
                    supporting_examples=[],
                    metadata={"flow": list(flow)},
                )
                patterns.append(pattern)

        return patterns

    @staticmethod
    def extract_tool_patterns(
        conversations: List[Dict],
        min_support: int = 3,
    ) -> List[ConversationPattern]:
        """Extract common tool usage sequences"""
        patterns = []
        tool_sequences = defaultdict(list)

        for conv in conversations:
            tools = conv.get("tools_used", [])
            if len(tools) < 2:
                continue

            tool_key = tuple(tools[:5])
            success = conv.get("success", True)
            tool_sequences[tool_key].append(success)

        for tools, outcomes in tool_sequences.items():
            if len(outcomes) >= min_support:
                success_rate = sum(outcomes) / len(outcomes)
                pattern = ConversationPattern(
                    pattern_id=f"tools_{hashlib.md5(str(tools).encode()).hexdigest()[:8]}",
                    pattern_type=PatternType.TOOL_SEQUENCE,
                    description=f"Tool sequence: {' → '.join(tools)}",
                    occurrence_count=len(outcomes),
                    success_rate=success_rate,
                    confidence=min(0.95, len(outcomes) / 100),
                    supporting_examples=[],
                    metadata={"tools": list(tools)},
                )
                patterns.append(pattern)

        return patterns


class HeuristicExtractor:
    """Derive actionable heuristics from patterns"""

    @staticmethod
    def extract_heuristics(patterns: List[ConversationPattern]) -> List[Heuristic]:
        """Generate heuristics from high-confidence patterns"""
        heuristics = []

        for pattern in patterns:
            if pattern.success_rate < 0.7:
                continue

            if pattern.pattern_type == PatternType.CONVERSATION_FLOW:
                heuristic = Heuristic(
                    heuristic_id=f"heur_{pattern.pattern_id}",
                    title=f"Use flow: {pattern.description[:50]}",
                    description=f"Following this conversation flow leads to {pattern.success_rate:.0%} success",
                    condition=f"When conversation pattern matches {pattern.pattern_id}",
                    action=f"Use conversation flow: {pattern.metadata.get('flow', [])}",
                    expected_improvement=pattern.success_rate * 100,
                    derivation=pattern.pattern_id,
                )
                heuristics.append(heuristic)

            elif pattern.pattern_type == PatternType.TOOL_SEQUENCE:
                heuristic = Heuristic(
                    heuristic_id=f"heur_{pattern.pattern_id}",
                    title=f"Try tool sequence: {pattern.description[:50]}",
                    description=f"This tool sequence succeeds {pattern.success_rate:.0%} of the time",
                    condition=f"When multiple tools needed for task",
                    action=f"Use tools in order: {pattern.metadata.get('tools', [])}",
                    expected_improvement=pattern.success_rate * 100,
                    derivation=pattern.pattern_id,
                )
                heuristics.append(heuristic)

        return heuristics


class OptimizationSystem:
    """Complete optimization and learning system"""

    def __init__(self):
        self.patterns: Dict[str, ConversationPattern] = {}
        self.heuristics: Dict[str, Heuristic] = {}
        self.experiments: Dict[str, ABExperiment] = {}
        self.miner = PatternMiner()
        self.extractor = HeuristicExtractor()

    def mine_patterns(self, conversations: List[Dict]) -> List[ConversationPattern]:
        """Discover patterns from conversation corpus"""
        all_patterns = []

        # Extract different pattern types
        flow_patterns = self.miner.extract_turn_patterns(conversations)
        all_patterns.extend(flow_patterns)

        tool_patterns = self.miner.extract_tool_patterns(conversations)
        all_patterns.extend(tool_patterns)

        # Store patterns
        for pattern in all_patterns:
            self.patterns[pattern.pattern_id] = pattern

        return all_patterns

    def extract_heuristics(self) -> List[Heuristic]:
        """Derive heuristics from discovered patterns"""
        patterns = list(self.patterns.values())
        heuristics = self.extractor.extract_heuristics(patterns)

        for heuristic in heuristics:
            self.heuristics[heuristic.heuristic_id] = heuristic

        return heuristics

    def create_ab_experiment(
        self,
        experiment_id: str,
        name: str,
        description: str,
        control: Dict[str, Any],
        variant: Dict[str, Any],
    ) -> ABExperiment:
        """Create A/B test for optimization"""
        experiment = ABExperiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            control_variant=control,
            test_variant=variant,
            status=ExperimentStatus.DRAFT,
            created_at=datetime.now().isoformat(),
        )
        self.experiments[experiment_id] = experiment
        return experiment

    def start_experiment(self, experiment_id: str) -> bool:
        """Start A/B test"""
        if experiment_id not in self.experiments:
            return False

        experiment = self.experiments[experiment_id]
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.now().isoformat()
        return True

    def record_experiment_result(
        self,
        experiment_id: str,
        variant: str,
        metric_name: str,
        value: float,
    ) -> bool:
        """Record metric for experiment variant"""
        if experiment_id not in self.experiments:
            return False

        experiment = self.experiments[experiment_id]

        if variant == "control":
            experiment.control_metrics[metric_name] = value
        elif variant == "test":
            experiment.test_metrics[metric_name] = value
        else:
            return False

        return True

    def complete_experiment(
        self,
        experiment_id: str,
        winner: Optional[str] = None,
    ) -> Optional[ABExperiment]:
        """Complete experiment and determine winner"""
        if experiment_id not in self.experiments:
            return None

        experiment = self.experiments[experiment_id]
        experiment.status = ExperimentStatus.COMPLETED
        experiment.completed_at = datetime.now().isoformat()

        if winner and experiment.improvement and experiment.improvement > 5:
            # Improvement significant, heuristic validated
            if f"exp_{experiment_id}" in self.heuristics:
                self.heuristics[f"exp_{experiment_id}"].tested = True

        return experiment

    def get_optimization_recommendations(self) -> List[Dict]:
        """Get optimization recommendations"""
        recommendations = []

        # Recommend high-confidence patterns
        for pattern in sorted(
            self.patterns.values(),
            key=lambda p: (p.success_rate, p.confidence),
            reverse=True,
        )[:5]:
            if pattern.success_rate > 0.8:
                recommendations.append({
                    "type": "pattern",
                    "pattern_id": pattern.pattern_id,
                    "description": pattern.description,
                    "expected_impact": f"+{pattern.success_rate * 100:.0f}% success rate",
                })

        # Recommend untested heuristics
        for heuristic in sorted(
            self.heuristics.values(),
            key=lambda h: h.expected_improvement,
            reverse=True,
        )[:5]:
            if not heuristic.tested:
                recommendations.append({
                    "type": "heuristic",
                    "heuristic_id": heuristic.heuristic_id,
                    "title": heuristic.title,
                    "expected_improvement": f"+{heuristic.expected_improvement:.0f}%",
                })

        return recommendations

    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate optimization report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "patterns_discovered": len(self.patterns),
            "heuristics_extracted": len(self.heuristics),
            "experiments_running": sum(
                1 for e in self.experiments.values()
                if e.status == ExperimentStatus.RUNNING
            ),
            "experiments_completed": sum(
                1 for e in self.experiments.values()
                if e.status == ExperimentStatus.COMPLETED
            ),
            "high_value_patterns": [
                p.to_dict() for p in sorted(
                    self.patterns.values(),
                    key=lambda x: x.success_rate,
                    reverse=True,
                )[:5]
            ],
            "recommendations": self.get_optimization_recommendations(),
        }


# Global system
optimization_system = OptimizationSystem()


# MCP Tools (add to memory_server.py)

def mine_conversation_patterns(conversations: list) -> dict:
    """Discover patterns from conversation data"""
    patterns = optimization_system.mine_patterns(conversations)
    return {
        "patterns_found": len(patterns),
        "patterns": [p.to_dict() for p in patterns[:10]],
    }


def extract_heuristics_from_patterns() -> dict:
    """Derive heuristics from patterns"""
    heuristics = optimization_system.extract_heuristics()
    return {
        "heuristics_extracted": len(heuristics),
        "heuristics": [h.to_dict() for h in heuristics[:10]],
    }


def create_ab_test(
    experiment_id: str,
    name: str,
    description: str,
    control: dict,
    variant: dict,
) -> dict:
    """Create A/B test experiment"""
    experiment = optimization_system.create_ab_experiment(
        experiment_id,
        name,
        description,
        control,
        variant,
    )
    return experiment.to_dict()


def start_ab_test(experiment_id: str) -> dict:
    """Start A/B test"""
    success = optimization_system.start_experiment(experiment_id)
    return {"experiment_id": experiment_id, "started": success}


def record_experiment_metric(
    experiment_id: str,
    variant: str,
    metric: str,
    value: float,
) -> dict:
    """Record experiment metric"""
    success = optimization_system.record_experiment_result(
        experiment_id,
        variant,
        metric,
        value,
    )
    return {"recorded": success, "metric": metric}


def complete_ab_test(experiment_id: str) -> dict:
    """Complete A/B test"""
    experiment = optimization_system.complete_experiment(experiment_id)
    return (
        experiment.to_dict()
        if experiment
        else {"error": "Experiment not found"}
    )


def get_optimization_recommendations() -> dict:
    """Get optimization recommendations"""
    recommendations = optimization_system.get_optimization_recommendations()
    return {"recommendations": recommendations}


if __name__ == "__main__":
    # Test optimization
    system = OptimizationSystem()

    # Sample conversations
    conversations = [
        {"messages": [{"speaker_id": "user"}, {"speaker_id": "agent"}], "success": True, "tools_used": ["search", "analyze"]},
        {"messages": [{"speaker_id": "user"}, {"speaker_id": "agent"}], "success": True, "tools_used": ["search", "analyze"]},
    ]

    # Mine patterns
    patterns = system.mine_patterns(conversations)
    print(f"Patterns found: {len(patterns)}")

    # Extract heuristics
    heuristics = system.extract_heuristics()
    print(f"Heuristics: {len(heuristics)}")

    # Get report
    report = system.get_optimization_report()
    print(f"Report: {json.dumps(report, indent=2)}")
