"""Tool use tracking and instrumentation for agent observability"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, asdict
from enum import Enum

TRACES_DIR = Path.home() / ".memory-mcp" / "traces"
TRACES_DIR.mkdir(exist_ok=True, parents=True)


class SpanStatus(Enum):
    """Span status"""
    PENDING = "PENDING"
    OK = "OK"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"


@dataclass
class ToolCall:
    """Represents a single tool invocation"""
    tool_id: str
    tool_name: str
    agent_id: str
    input_args: Dict[str, Any]
    output: Optional[Any] = None
    error: Optional[str] = None
    status: SpanStatus = SpanStatus.PENDING
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    tokens_used: int = 0
    retry_count: int = 0
    parent_span_id: Optional[str] = None
    trace_id: str = ""

    def to_dict(self) -> Dict:
        """Serialize to dict"""
        return {
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "agent_id": self.agent_id,
            "input_args": self.input_args,
            "output": self.output,
            "error": self.error,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "retry_count": self.retry_count,
            "parent_span_id": self.parent_span_id,
            "trace_id": self.trace_id,
        }


class Trace:
    """Represents a complete agent execution trace"""

    def __init__(self, trace_id: str, agent_id: str, user_intent: str = ""):
        self.trace_id = trace_id
        self.agent_id = agent_id
        self.user_intent = user_intent
        self.spans: List[ToolCall] = []
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.metadata: Dict = {}
        self.decisions: List[str] = []  # Track agent decisions
        self.final_output: Optional[str] = None

    def add_span(self, span: ToolCall) -> str:
        """Add tool call span to trace"""
        span.trace_id = self.trace_id
        if not span.tool_id:
            span.tool_id = f"{self.agent_id}_span_{len(self.spans)}"
        self.spans.append(span)
        return span.tool_id

    def add_decision(self, decision: str):
        """Record an agent decision"""
        self.decisions.append(decision)

    def set_final_output(self, output: str):
        """Set final output of trace"""
        self.final_output = output

    def close(self):
        """Close the trace"""
        self.end_time = time.time()

    def get_total_duration(self) -> float:
        """Get total trace duration in ms"""
        if not self.end_time:
            self.close()
        return (self.end_time - self.start_time) * 1000

    def get_tool_latencies(self) -> Dict[str, List[float]]:
        """Get latencies grouped by tool"""
        latencies = {}
        for span in self.spans:
            if span.tool_name not in latencies:
                latencies[span.tool_name] = []
            latencies[span.tool_name].append(span.duration_ms)
        return latencies

    def get_error_rate(self) -> float:
        """Get error rate as percentage"""
        if not self.spans:
            return 0.0
        errors = sum(1 for s in self.spans if s.status == SpanStatus.ERROR)
        return (errors / len(self.spans)) * 100

    def to_dict(self) -> Dict:
        """Serialize trace"""
        return {
            "trace_id": self.trace_id,
            "agent_id": self.agent_id,
            "user_intent": self.user_intent,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.get_total_duration(),
            "spans": [span.to_dict() for span in self.spans],
            "decisions": self.decisions,
            "final_output": self.final_output,
            "error_rate": self.get_error_rate(),
            "metadata": self.metadata,
        }


class TraceCollector:
    """Collect and manage traces"""

    def __init__(self):
        self.traces: Dict[str, Trace] = {}
        self.current_trace: Optional[Trace] = None

    def start_trace(self, trace_id: str, agent_id: str, user_intent: str = "") -> Trace:
        """Start new trace"""
        trace = Trace(trace_id, agent_id, user_intent)
        self.traces[trace_id] = trace
        self.current_trace = trace
        return trace

    def end_trace(self, trace_id: str):
        """End trace"""
        if trace_id in self.traces:
            self.traces[trace_id].close()
            self.current_trace = None

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get trace by ID"""
        return self.traces.get(trace_id)

    def save_trace(self, trace_id: str) -> str:
        """Save trace to file"""
        trace = self.traces.get(trace_id)
        if not trace:
            return ""

        filepath = TRACES_DIR / f"{trace_id}.json"
        with open(filepath, "w") as f:
            json.dump(trace.to_dict(), f, indent=2)

        return str(filepath)

    def load_trace(self, trace_id: str) -> Optional[Trace]:
        """Load trace from file"""
        filepath = TRACES_DIR / f"{trace_id}.json"
        if not filepath.exists():
            return None

        with open(filepath) as f:
            data = json.load(f)

        trace = Trace(data["trace_id"], data["agent_id"], data.get("user_intent", ""))
        trace.start_time = data.get("start_time", 0)
        trace.end_time = data.get("end_time")
        trace.decisions = data.get("decisions", [])
        trace.final_output = data.get("final_output")

        # Reconstruct spans
        for span_data in data.get("spans", []):
            span = ToolCall(
                tool_id=span_data["tool_id"],
                tool_name=span_data["tool_name"],
                agent_id=span_data["agent_id"],
                input_args=span_data["input_args"],
                output=span_data.get("output"),
                error=span_data.get("error"),
                status=SpanStatus(span_data["status"]),
                start_time=span_data["start_time"],
                end_time=span_data["end_time"],
                duration_ms=span_data["duration_ms"],
                tokens_used=span_data.get("tokens_used", 0),
                retry_count=span_data.get("retry_count", 0),
            )
            trace.add_span(span)

        return trace

    def list_traces(self, agent_id: str, limit: int = 10) -> List[Dict]:
        """List traces for agent"""
        agent_traces = [
            t.to_dict()
            for t in self.traces.values()
            if t.agent_id == agent_id
        ]
        return sorted(
            agent_traces,
            key=lambda x: x["start_time"],
            reverse=True,
        )[:limit]


class ToolCallInterceptor:
    """Intercept and wrap tool calls with instrumentation"""

    def __init__(self, collector: TraceCollector):
        self.collector = collector

    def wrap_tool(
        self,
        tool_name: str,
        tool_fn: Callable,
    ) -> Callable:
        """Wrap a tool function with tracing"""

        def wrapped(*args, **kwargs) -> Any:
            trace = self.collector.current_trace
            if not trace:
                return tool_fn(*args, **kwargs)

            # Create span
            span = ToolCall(
                tool_id="",
                tool_name=tool_name,
                agent_id=trace.agent_id,
                input_args={"args": str(args)[:100], "kwargs": kwargs},
                start_time=time.time(),
            )

            try:
                span.start_time = time.time()
                result = tool_fn(*args, **kwargs)
                span.output = result
                span.status = SpanStatus.OK
                span.end_time = time.time()
                span.duration_ms = (span.end_time - span.start_time) * 1000
                return result
            except Exception as e:
                span.error = str(e)
                span.status = SpanStatus.ERROR
                span.end_time = time.time()
                span.duration_ms = (span.end_time - span.start_time) * 1000
                raise
            finally:
                self.collector.current_trace.add_span(span)

        return wrapped


class ToolMetrics:
    """Aggregate metrics from traces"""

    @staticmethod
    def calculate_tool_stats(traces: List[Trace]) -> Dict[str, Dict]:
        """Calculate stats for each tool"""
        stats = {}

        for trace in traces:
            for span in trace.spans:
                if span.tool_name not in stats:
                    stats[span.tool_name] = {
                        "call_count": 0,
                        "error_count": 0,
                        "total_duration_ms": 0.0,
                        "latencies": [],
                        "avg_latency_ms": 0.0,
                        "p95_latency_ms": 0.0,
                        "p99_latency_ms": 0.0,
                    }

                tool_stats = stats[span.tool_name]
                tool_stats["call_count"] += 1
                if span.status == SpanStatus.ERROR:
                    tool_stats["error_count"] += 1
                tool_stats["total_duration_ms"] += span.duration_ms
                tool_stats["latencies"].append(span.duration_ms)

        # Calculate percentiles
        for tool_name, tool_stat in stats.items():
            latencies = sorted(tool_stat["latencies"])
            if latencies:
                tool_stat["avg_latency_ms"] = sum(latencies) / len(latencies)
                p95_idx = int(len(latencies) * 0.95)
                p99_idx = int(len(latencies) * 0.99)
                tool_stat["p95_latency_ms"] = latencies[p95_idx]
                tool_stat["p99_latency_ms"] = latencies[p99_idx]

            # Remove raw latencies from output
            del tool_stat["latencies"]

        return stats

    @staticmethod
    def generate_report(collector: TraceCollector, agent_id: str) -> Dict:
        """Generate observability report"""
        traces = []
        for trace in collector.traces.values():
            if trace.agent_id == agent_id:
                traces.append(trace)

        return {
            "agent_id": agent_id,
            "trace_count": len(traces),
            "total_duration_ms": sum(t.get_total_duration() for t in traces),
            "avg_duration_ms": (
                sum(t.get_total_duration() for t in traces) / len(traces)
                if traces
                else 0
            ),
            "tool_stats": ToolMetrics.calculate_tool_stats(traces),
            "avg_error_rate": (
                sum(t.get_error_rate() for t in traces) / len(traces)
                if traces
                else 0
            ),
        }


# Global instances
collector = TraceCollector()
interceptor = ToolCallInterceptor(collector)


# MCP Tools (add to memory_server.py)

def start_trace(trace_id: str, agent_id: str, user_intent: str = "") -> dict:
    """Start a new execution trace"""
    trace = collector.start_trace(trace_id, agent_id, user_intent)
    return {"trace_id": trace.trace_id, "status": "started"}


def end_trace(trace_id: str) -> dict:
    """End trace and save to file"""
    collector.end_trace(trace_id)
    filepath = collector.save_trace(trace_id)
    return {"trace_id": trace_id, "filepath": filepath}


def add_tool_call(
    trace_id: str,
    tool_name: str,
    input_args: dict,
    output: dict = None,
    error: str = None,
    duration_ms: float = 0,
) -> dict:
    """Manually add tool call span to trace"""
    trace = collector.get_trace(trace_id)
    if not trace:
        return {"error": "Trace not found"}

    span = ToolCall(
        tool_id="",
        tool_name=tool_name,
        agent_id=trace.agent_id,
        input_args=input_args,
        output=output,
        error=error,
        status=SpanStatus.ERROR if error else SpanStatus.OK,
        duration_ms=duration_ms,
    )

    span_id = trace.add_span(span)
    return span.to_dict()


def get_tool_stats(agent_id: str) -> dict:
    """Get tool statistics and metrics"""
    report = ToolMetrics.generate_report(collector, agent_id)
    return report


def get_trace(trace_id: str) -> dict:
    """Get trace details"""
    trace = collector.get_trace(trace_id) or collector.load_trace(trace_id)
    if not trace:
        return {"error": "Trace not found"}
    return trace.to_dict()


def list_traces(agent_id: str, limit: int = 10) -> list:
    """List recent traces for agent"""
    return collector.list_traces(agent_id, limit)


if __name__ == "__main__":
    # Test tracing
    coll = TraceCollector()
    trace = coll.start_trace("test_trace", "agent_1", "Test query")

    # Simulate tool calls
    span1 = ToolCall(
        tool_id="",
        tool_name="search",
        agent_id="agent_1",
        input_args={"query": "test"},
        output={"results": ["result1", "result2"]},
    )
    span1.start_time = time.time()
    time.sleep(0.1)
    span1.end_time = time.time()
    span1.duration_ms = (span1.end_time - span1.start_time) * 1000
    span1.status = SpanStatus.OK
    trace.add_span(span1)

    span2 = ToolCall(
        tool_id="",
        tool_name="analyze",
        agent_id="agent_1",
        input_args={"data": "result1"},
        error="Timeout",
    )
    span2.start_time = time.time()
    span2.end_time = time.time()
    span2.duration_ms = 5000
    span2.status = SpanStatus.TIMEOUT
    trace.add_span(span2)

    trace.set_final_output("Analysis complete")
    coll.end_trace(trace.trace_id)

    # Print stats
    print("Trace:", json.dumps(trace.to_dict(), indent=2))
    print("Error rate:", trace.get_error_rate(), "%")
    print("Tool latencies:", trace.get_tool_latencies())
