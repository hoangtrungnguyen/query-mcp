"""Agent debugging and introspection for troubleshooting and transparency"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

DEBUG_DIR = Path.home() / ".memory-mcp" / "debugging"
DEBUG_DIR.mkdir(exist_ok=True, parents=True)


class ExecutionPhase(Enum):
    """Phases of agent execution"""
    INPUT_PROCESSING = "input_processing"
    INTENT_DETECTION = "intent_detection"
    PLANNING = "planning"
    TOOL_SELECTION = "tool_selection"
    TOOL_EXECUTION = "tool_execution"
    RESPONSE_GENERATION = "response_generation"
    OUTPUT = "output"


class DecisionType(Enum):
    """Types of decisions made"""
    TOOL_CHOICE = "tool_choice"
    PARAMETER_SELECTION = "parameter_selection"
    ROUTING = "routing"
    ESCALATION = "escalation"
    FORMATTING = "formatting"


@dataclass
class ExecutionTrace:
    """Trace of single execution step"""
    step_id: str
    phase: ExecutionPhase
    timestamp: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Serialize trace"""
        return {
            "step_id": self.step_id,
            "phase": self.phase.value,
            "timestamp": self.timestamp,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class Decision:
    """Decision made during execution"""
    decision_id: str
    decision_type: DecisionType
    options: List[Dict[str, Any]]  # Available choices
    selected: str  # Selected choice
    confidence: float
    reasoning: str
    phase: ExecutionPhase
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize decision"""
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type.value,
            "option_count": len(self.options),
            "selected": self.selected,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "phase": self.phase.value,
            "timestamp": self.timestamp,
        }


@dataclass
class AttentionVector:
    """Attention weights over inputs/tokens"""
    attention_id: str
    layer: int  # Which layer
    focus_area: str  # What was attended to
    weights: Dict[str, float]  # Token/concept -> attention weight
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def get_top_attention(self, top_k: int = 5) -> List[Tuple[str, float]]:
        """Get most attended elements"""
        return sorted(self.weights.items(), key=lambda x: x[1], reverse=True)[:top_k]

    def to_dict(self) -> Dict:
        """Serialize attention"""
        return {
            "attention_id": self.attention_id,
            "layer": self.layer,
            "focus_area": self.focus_area,
            "top_attention": self.get_top_attention(5),
            "timestamp": self.timestamp,
        }


class ExecutionDebugger:
    """Debug agent execution"""

    def __init__(self):
        self.traces: Dict[str, List[ExecutionTrace]] = {}  # execution_id -> traces
        self.decisions: Dict[str, List[Decision]] = {}  # execution_id -> decisions
        self.attention: Dict[str, List[AttentionVector]] = {}  # execution_id -> attention

    def record_trace(
        self,
        execution_id: str,
        phase: ExecutionPhase,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        duration_ms: float = 0.0,
        success: bool = True,
        error: Optional[str] = None,
    ) -> ExecutionTrace:
        """Record execution step"""
        trace = ExecutionTrace(
            step_id=f"trace_{len(self.traces.get(execution_id, []))}",
            phase=phase,
            timestamp=datetime.now().isoformat(),
            inputs=inputs,
            outputs=outputs,
            duration_ms=duration_ms,
            success=success,
            error=error,
        )

        if execution_id not in self.traces:
            self.traces[execution_id] = []

        self.traces[execution_id].append(trace)
        return trace

    def record_decision(
        self,
        execution_id: str,
        decision_type: DecisionType,
        options: List[Dict],
        selected: str,
        confidence: float,
        reasoning: str,
        phase: ExecutionPhase,
    ) -> Decision:
        """Record decision point"""
        decision = Decision(
            decision_id=f"dec_{len(self.decisions.get(execution_id, []))}",
            decision_type=decision_type,
            options=options,
            selected=selected,
            confidence=confidence,
            reasoning=reasoning,
            phase=phase,
        )

        if execution_id not in self.decisions:
            self.decisions[execution_id] = []

        self.decisions[execution_id].append(decision)
        return decision

    def record_attention(
        self,
        execution_id: str,
        layer: int,
        focus_area: str,
        weights: Dict[str, float],
    ) -> AttentionVector:
        """Record attention weights"""
        attention = AttentionVector(
            attention_id=f"attn_{len(self.attention.get(execution_id, []))}",
            layer=layer,
            focus_area=focus_area,
            weights=weights,
        )

        if execution_id not in self.attention:
            self.attention[execution_id] = []

        self.attention[execution_id].append(attention)
        return attention

    def get_execution_trace(self, execution_id: str) -> Optional[List[ExecutionTrace]]:
        """Get full execution trace"""
        return self.traces.get(execution_id)

    def identify_failure_point(self, execution_id: str) -> Optional[ExecutionTrace]:
        """Find where execution failed"""
        traces = self.traces.get(execution_id, [])

        for trace in traces:
            if not trace.success:
                return trace

        return None

    def get_decision_tree(self, execution_id: str) -> Dict[str, Any]:
        """Visualize decision tree"""
        decisions = self.decisions.get(execution_id, [])

        tree = {
            "execution_id": execution_id,
            "decision_count": len(decisions),
            "decisions": [d.to_dict() for d in decisions],
            "high_confidence": sum(1 for d in decisions if d.confidence > 0.8),
            "low_confidence": sum(1 for d in decisions if d.confidence < 0.5),
        }

        return tree

    def get_attention_visualization(self, execution_id: str) -> Dict[str, Any]:
        """Get attention data for visualization"""
        attention_vectors = self.attention.get(execution_id, [])

        visualization = {
            "execution_id": execution_id,
            "layer_count": len(set(a.layer for a in attention_vectors)),
            "focus_areas": list(set(a.focus_area for a in attention_vectors)),
            "attention_patterns": [a.to_dict() for a in attention_vectors[:5]],
        }

        return visualization

    def analyze_performance(self, execution_id: str) -> Dict[str, Any]:
        """Analyze execution performance"""
        traces = self.traces.get(execution_id, [])

        if not traces:
            return {}

        total_duration = sum(t.duration_ms for t in traces)
        phase_durations = {}

        for trace in traces:
            phase = trace.phase.value
            if phase not in phase_durations:
                phase_durations[phase] = 0.0
            phase_durations[phase] += trace.duration_ms

        slowest_phase = max(phase_durations.items(), key=lambda x: x[1])[0] if phase_durations else None

        return {
            "total_duration_ms": total_duration,
            "phase_count": len(phase_durations),
            "phase_breakdown": phase_durations,
            "slowest_phase": slowest_phase,
            "success_rate": sum(1 for t in traces if t.success) / len(traces) if traces else 0.0,
        }


class DebugReport:
    """Comprehensive debug report"""

    def __init__(self, execution_id: str, debugger: ExecutionDebugger):
        self.execution_id = execution_id
        self.debugger = debugger
        self.generated_at = datetime.now().isoformat()

    def generate(self) -> Dict[str, Any]:
        """Generate full debug report"""
        failure_point = self.debugger.identify_failure_point(self.execution_id)
        decision_tree = self.debugger.get_decision_tree(self.execution_id)
        attention = self.debugger.get_attention_visualization(self.execution_id)
        performance = self.debugger.analyze_performance(self.execution_id)

        return {
            "execution_id": self.execution_id,
            "generated_at": self.generated_at,
            "failure_point": failure_point.to_dict() if failure_point else None,
            "decision_analysis": decision_tree,
            "attention_analysis": attention,
            "performance_analysis": performance,
            "recommendations": self._generate_recommendations(failure_point, performance),
        }

    def _generate_recommendations(
        self,
        failure_point: Optional[ExecutionTrace],
        performance: Dict,
    ) -> List[str]:
        """Generate debugging recommendations"""
        recommendations = []

        if failure_point:
            recommendations.append(f"Fix {failure_point.phase.value} phase: {failure_point.error}")

        slowest = performance.get("slowest_phase")
        if slowest:
            recommendations.append(f"Optimize {slowest} phase (bottleneck)")

        success_rate = performance.get("success_rate", 1.0)
        if success_rate < 0.95:
            recommendations.append(f"Investigate {(1-success_rate)*100:.0f}% failure rate")

        return recommendations

    def save(self) -> str:
        """Save report to file"""
        report = self.generate()
        filepath = DEBUG_DIR / f"{self.execution_id}_debug.json"

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)

        return str(filepath)


# Global debugger
debugger = ExecutionDebugger()


# MCP Tools (add to memory_server.py)

def record_execution_trace(
    execution_id: str,
    phase: str,
    inputs: dict,
    outputs: dict,
    duration_ms: float = 0.0,
) -> dict:
    """Record execution step"""
    trace = debugger.record_trace(
        execution_id,
        ExecutionPhase(phase),
        inputs,
        outputs,
        duration_ms,
    )
    return trace.to_dict()


def record_decision_point(
    execution_id: str,
    decision_type: str,
    options: list,
    selected: str,
    confidence: float,
    reasoning: str,
    phase: str,
) -> dict:
    """Record decision"""
    decision = debugger.record_decision(
        execution_id,
        DecisionType(decision_type),
        options,
        selected,
        confidence,
        reasoning,
        ExecutionPhase(phase),
    )
    return decision.to_dict()


def get_execution_trace(execution_id: str) -> dict:
    """Get execution trace"""
    traces = debugger.get_execution_trace(execution_id)
    return {
        "execution_id": execution_id,
        "steps": [t.to_dict() for t in traces] if traces else [],
        "count": len(traces) if traces else 0,
    }


def identify_failure_point(execution_id: str) -> dict:
    """Find failure point"""
    failure = debugger.identify_failure_point(execution_id)
    return (
        {"found": True, "failure": failure.to_dict()}
        if failure else
        {"found": False}
    )


def get_debug_report(execution_id: str) -> dict:
    """Generate debug report"""
    report = DebugReport(execution_id, debugger)
    return report.generate()


if __name__ == "__main__":
    # Test debugging
    debug = ExecutionDebugger()

    # Record traces
    trace1 = debug.record_trace(
        "exec_1",
        ExecutionPhase.INPUT_PROCESSING,
        {"input": "user query"},
        {"parsed": "query intent"},
        duration_ms=50,
    )
    print(f"Trace: {trace1.step_id}")

    # Record decision
    decision = debug.record_decision(
        "exec_1",
        DecisionType.TOOL_CHOICE,
        [{"name": "search"}, {"name": "analyze"}],
        "search",
        0.85,
        "Query matches search pattern",
        ExecutionPhase.TOOL_SELECTION,
    )
    print(f"Decision: {decision.decision_id}")

    # Analyze
    analysis = debug.analyze_performance("exec_1")
    print(f"Performance: {json.dumps(analysis, indent=2)}")

    # Report
    report = DebugReport("exec_1", debug)
    full_report = report.generate()
    print(f"Report: {json.dumps(full_report, indent=2)}")
