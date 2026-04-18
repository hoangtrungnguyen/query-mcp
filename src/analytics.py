"""Analytics and observability for agent conversations"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from collections import defaultdict
from enum import Enum

ANALYTICS_DIR = Path.home() / ".memory-mcp" / "analytics"
ANALYTICS_DIR.mkdir(exist_ok=True, parents=True)


class MetricType(Enum):
    """Types of metrics"""
    LATENCY = "latency"
    TOKEN_USAGE = "token_usage"
    COST = "cost"
    ERROR_RATE = "error_rate"
    HALLUCINATION_RATE = "hallucination_rate"
    TOOL_SUCCESS_RATE = "tool_success_rate"
    DECISION_DISTRIBUTION = "decision_distribution"


class AgentAnalytics:
    """Aggregate analytics for a single agent"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.events: List[Dict] = []
        self.decision_tree: Dict = {}
        self.tool_usage: Dict[str, int] = defaultdict(int)
        self.error_log: List[Dict] = []

    def record_metric(self, metric_type: MetricType, value: float, metadata: Optional[Dict] = None):
        """Record a metric"""
        self.metrics[metric_type.value].append(value)
        self.events.append({
            "timestamp": datetime.now().isoformat(),
            "metric": metric_type.value,
            "value": value,
            "metadata": metadata or {},
        })

    def record_tool_use(self, tool_name: str, success: bool):
        """Record tool usage"""
        self.tool_usage[tool_name] += 1
        if not success:
            self.error_log.append({
                "timestamp": datetime.now().isoformat(),
                "tool": tool_name,
                "error": "tool_failed",
            })

    def record_decision(self, decision_path: List[str]):
        """Record decision path"""
        # Build decision tree from paths
        current = self.decision_tree
        for decision in decision_path:
            if decision not in current:
                current[decision] = {"count": 0, "children": {}}
            current[decision]["count"] += 1
            current = current[decision]["children"]

    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregated statistics"""
        stats = {
            "agent_id": self.agent_id,
            "event_count": len(self.events),
            "metrics": {},
            "tool_usage": dict(self.tool_usage),
            "error_count": len(self.error_log),
        }

        # Calculate metric statistics
        for metric_type, values in self.metrics.items():
            if values:
                stats["metrics"][metric_type] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "p50": self._percentile(values, 50),
                    "p95": self._percentile(values, 95),
                    "p99": self._percentile(values, 99),
                }

        # Tool success rate
        if self.tool_usage:
            total_uses = sum(self.tool_usage.values())
            failed_tools = {t for t, _ in [(e["tool"], 1) for e in self.error_log]}
            failed_count = sum(self.tool_usage[t] for t in failed_tools)
            stats["tool_success_rate"] = (total_uses - failed_count) / total_uses

        return stats

    @staticmethod
    def _percentile(values: List[float], p: int) -> float:
        """Calculate percentile"""
        sorted_vals = sorted(values)
        idx = int(len(sorted_vals) * p / 100)
        return sorted_vals[idx] if idx < len(sorted_vals) else sorted_vals[-1]

    def to_dict(self) -> Dict:
        """Serialize analytics"""
        return {
            "agent_id": self.agent_id,
            "statistics": self.get_statistics(),
            "decision_tree": self.decision_tree,
            "events_sample": self.events[-100:],  # Last 100 events
        }


class ConversationAnalytics:
    """Analytics for conversation patterns"""

    def __init__(self):
        self.conversations: Dict[str, List[Dict]] = defaultdict(list)
        self.agent_analytics: Dict[str, AgentAnalytics] = {}

    def add_conversation(self, conversation_id: str, agent_id: str, messages: List[Dict]):
        """Add conversation to analytics"""
        if agent_id not in self.agent_analytics:
            self.agent_analytics[agent_id] = AgentAnalytics(agent_id)

        self.conversations[conversation_id] = {
            "agent_id": agent_id,
            "message_count": len(messages),
            "timestamp": datetime.now().isoformat(),
            "duration": self._estimate_duration(messages),
        }

    def get_agent_analytics(self, agent_id: str) -> Optional[Dict]:
        """Get analytics for agent"""
        if agent_id not in self.agent_analytics:
            return None
        return self.agent_analytics[agent_id].to_dict()

    def get_trend_analysis(self, agent_id: str, days: int = 7) -> Dict:
        """Get performance trends over time"""
        if agent_id not in self.agent_analytics:
            return {}

        analytics = self.agent_analytics[agent_id]
        stats = analytics.get_statistics()

        return {
            "agent_id": agent_id,
            "period_days": days,
            "trend": {
                "latency": self._calculate_trend(
                    analytics.metrics.get("latency", [])
                ),
                "token_usage": self._calculate_trend(
                    analytics.metrics.get("token_usage", [])
                ),
                "error_rate": self._calculate_trend(
                    [1 if e else 0 for e in analytics.error_log]
                ),
            },
            "current_stats": stats,
        }

    @staticmethod
    def _estimate_duration(messages: List[Dict]) -> float:
        """Estimate conversation duration in minutes"""
        if len(messages) < 2:
            return 0.0
        # Rough estimate: 5 seconds per message
        return (len(messages) * 5) / 60

    @staticmethod
    def _calculate_trend(values: List[float]) -> Dict:
        """Calculate trend (increasing/decreasing)"""
        if len(values) < 2:
            return {"trend": "unknown", "direction": None}

        recent = values[-10:] if len(values) >= 10 else values
        early = values[:10] if len(values) >= 10 else values

        if not early or not recent:
            return {"trend": "unknown", "direction": None}

        early_avg = sum(early) / len(early)
        recent_avg = sum(recent) / len(recent)
        change_pct = ((recent_avg - early_avg) / early_avg * 100) if early_avg else 0

        direction = "increasing" if change_pct > 5 else "decreasing" if change_pct < -5 else "stable"

        return {
            "trend": "up" if change_pct > 0 else "down",
            "change_percent": round(change_pct, 2),
            "direction": direction,
        }


class DashboardGenerator:
    """Generate observability dashboards"""

    def __init__(self, analytics: ConversationAnalytics):
        self.analytics = analytics

    def generate_agent_dashboard(self, agent_id: str) -> Dict:
        """Generate dashboard for agent"""
        agent_analytics = self.analytics.get_agent_analytics(agent_id)
        if not agent_analytics:
            return {}

        stats = agent_analytics["statistics"]

        return {
            "agent_id": agent_id,
            "title": f"Agent {agent_id} Dashboard",
            "generated_at": datetime.now().isoformat(),
            "key_metrics": {
                "latency": stats.get("metrics", {}).get("latency", {}),
                "token_usage": stats.get("metrics", {}).get("token_usage", {}),
                "error_rate": stats.get("error_count", 0) / max(1, stats.get("event_count", 1)),
                "tool_success_rate": stats.get("tool_success_rate", 1.0),
            },
            "tools": stats.get("tool_usage", {}),
            "decision_tree": agent_analytics.get("decision_tree", {}),
            "error_log_sample": stats.get("error_count", 0),
            "recommendations": self._generate_recommendations(agent_id),
        }

    def generate_system_dashboard(self) -> Dict:
        """Generate system-wide dashboard"""
        agents = list(self.analytics.agent_analytics.keys())

        return {
            "title": "System Overview Dashboard",
            "generated_at": datetime.now().isoformat(),
            "agent_count": len(agents),
            "conversation_count": len(self.analytics.conversations),
            "agents": {
                agent_id: {
                    "metrics_count": len(
                        self.analytics.agent_analytics[agent_id].metrics
                    ),
                    "error_count": len(
                        self.analytics.agent_analytics[agent_id].error_log
                    ),
                }
                for agent_id in agents
            },
            "top_tools": self._get_top_tools(),
            "system_health": self._calculate_system_health(),
        }

    def _generate_recommendations(self, agent_id: str) -> List[str]:
        """Generate optimization recommendations"""
        analytics = self.analytics.agent_analytics.get(agent_id)
        if not analytics:
            return []

        recommendations = []
        stats = analytics.get_statistics()

        # Latency recommendations
        if stats.get("metrics", {}).get("latency", {}).get("p99", 0) > 5000:
            recommendations.append("High P99 latency detected - consider optimizing tool calls")

        # Token usage recommendations
        if stats.get("metrics", {}).get("token_usage", {}).get("avg", 0) > 10000:
            recommendations.append("High token usage - consider summarization or caching")

        # Error rate recommendations
        error_rate = stats.get("error_count", 0) / max(1, stats.get("event_count", 1))
        if error_rate > 0.1:
            recommendations.append(f"Error rate {error_rate:.1%} is high - review error logs")

        # Tool success recommendations
        tool_success = stats.get("tool_success_rate", 1.0)
        if tool_success < 0.95:
            recommendations.append(f"Tool success rate {tool_success:.1%} - debug failing tools")

        return recommendations

    def _get_top_tools(self) -> Dict[str, int]:
        """Get most used tools across all agents"""
        tool_counts = defaultdict(int)
        for analytics in self.analytics.agent_analytics.values():
            for tool, count in analytics.tool_usage.items():
                tool_counts[tool] += count

        return dict(sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:5])

    def _calculate_system_health(self) -> Dict:
        """Calculate overall system health"""
        if not self.analytics.agent_analytics:
            return {"health_score": 0.5, "status": "unknown"}

        total_errors = sum(
            len(a.error_log) for a in self.analytics.agent_analytics.values()
        )
        total_events = sum(
            len(a.events) for a in self.analytics.agent_analytics.values()
        )

        error_rate = total_errors / max(1, total_events)
        health_score = 1.0 - error_rate

        status = "healthy" if health_score > 0.9 else "degraded" if health_score > 0.7 else "critical"

        return {
            "health_score": health_score,
            "status": status,
            "total_errors": total_errors,
            "total_events": total_events,
        }


# Global analytics instance
analytics = ConversationAnalytics()
dashboard_gen = DashboardGenerator(analytics)


# MCP Tools (add to memory_server.py)

def add_conversation_to_analytics(
    conversation_id: str,
    agent_id: str,
    messages: list,
) -> dict:
    """Add conversation to analytics system"""
    analytics.add_conversation(conversation_id, agent_id, messages)
    return {"conversation_id": conversation_id, "agent_id": agent_id, "indexed": True}


def get_agent_dashboard(agent_id: str) -> dict:
    """Get analytics dashboard for agent"""
    return dashboard_gen.generate_agent_dashboard(agent_id)


def get_system_dashboard() -> dict:
    """Get system-wide analytics dashboard"""
    return dashboard_gen.generate_system_dashboard()


def get_agent_analytics(agent_id: str) -> dict:
    """Get detailed analytics for agent"""
    return analytics.get_agent_analytics(agent_id) or {"error": "Agent not found"}


def get_trend_analysis(agent_id: str, days: int = 7) -> dict:
    """Get performance trends for agent"""
    return analytics.get_trend_analysis(agent_id, days)


def record_agent_metric(
    agent_id: str,
    metric_type: str,
    value: float,
    metadata: dict = None,
) -> dict:
    """Record metric for agent"""
    if agent_id not in analytics.agent_analytics:
        analytics.agent_analytics[agent_id] = AgentAnalytics(agent_id)

    analytics.agent_analytics[agent_id].record_metric(
        MetricType(metric_type),
        value,
        metadata,
    )
    return {"agent_id": agent_id, "metric": metric_type, "value": value}


def export_dashboard(agent_id: str = None) -> str:
    """Export dashboard to file"""
    if agent_id:
        dashboard = dashboard_gen.generate_agent_dashboard(agent_id)
        filename = f"{agent_id}_dashboard"
    else:
        dashboard = dashboard_gen.generate_system_dashboard()
        filename = "system_dashboard"

    filepath = ANALYTICS_DIR / f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filepath, "w") as f:
        json.dump(dashboard, f, indent=2, default=str)

    return str(filepath)


if __name__ == "__main__":
    # Test analytics
    conv_analytics = ConversationAnalytics()

    # Create analytics
    agent_analytics = AgentAnalytics("test_agent")
    agent_analytics.record_metric(MetricType.LATENCY, 150.5)
    agent_analytics.record_metric(MetricType.TOKEN_USAGE, 5000)
    agent_analytics.record_tool_use("search", True)
    agent_analytics.record_tool_use("analyze", False)
    agent_analytics.record_decision(["intent_detection", "tool_selection", "search"])

    conv_analytics.agent_analytics["test_agent"] = agent_analytics

    # Generate dashboard
    dashboard = DashboardGenerator(conv_analytics).generate_agent_dashboard("test_agent")
    print(json.dumps(dashboard, indent=2))
