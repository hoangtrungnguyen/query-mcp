"""Cost and performance optimization for agent conversations"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

COST_DIR = Path.home() / ".memory-mcp" / "cost-optimization"
COST_DIR.mkdir(exist_ok=True, parents=True)


class OptimizationStrategy(Enum):
    """Token optimization approaches"""
    CACHING = "caching"  # Cache responses
    SUMMARIZATION = "summarization"  # Compress context
    PRUNING = "pruning"  # Remove unnecessary details
    BATCHING = "batching"  # Batch multiple queries
    MODEL_SELECTION = "model_selection"  # Use cheaper models


@dataclass
class TokenBudget:
    """Token allocation for conversation"""
    budget_id: str
    total_tokens: int
    allocated_for_context: int
    allocated_for_response: int
    reserved_for_safety: int = 500
    usage: int = 0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    @property
    def remaining_tokens(self) -> int:
        return self.total_tokens - self.usage

    @property
    def budget_utilization(self) -> float:
        if self.total_tokens == 0:
            return 0.0
        return (self.usage / self.total_tokens) * 100

    def to_dict(self) -> Dict:
        """Serialize budget"""
        return {
            "budget_id": self.budget_id,
            "total_tokens": self.total_tokens,
            "allocated_for_context": self.allocated_for_context,
            "allocated_for_response": self.allocated_for_response,
            "reserved_for_safety": self.reserved_for_safety,
            "usage": self.usage,
            "remaining_tokens": self.remaining_tokens,
            "utilization_percent": self.budget_utilization,
            "created_at": self.created_at,
        }


@dataclass
class PerformanceMetric:
    """Performance measurement"""
    metric_id: str
    metric_type: str  # "latency", "throughput", "error_rate"
    value: float
    unit: str
    timestamp: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize metric"""
        return {
            "metric_id": self.metric_id,
            "metric_type": self.metric_type,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "context": self.context,
        }


@dataclass
class OptimizationRecommendation:
    """Suggested optimization"""
    recommendation_id: str
    strategy: OptimizationStrategy
    title: str
    description: str
    estimated_savings: Dict[str, float]  # token_count, latency_ms, cost_usd
    implementation_effort: str  # "low", "medium", "high"
    priority: int  # 1-10, higher = more important

    def to_dict(self) -> Dict:
        """Serialize recommendation"""
        return {
            "recommendation_id": self.recommendation_id,
            "strategy": self.strategy.value,
            "title": self.title,
            "description": self.description,
            "estimated_savings": self.estimated_savings,
            "implementation_effort": self.implementation_effort,
            "priority": self.priority,
        }


class TokenCounter:
    """Estimate token usage"""

    # Approximate tokens per word
    TOKENS_PER_WORD = 1.3
    TOKENS_PER_CHAR = 0.25

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate tokens in text"""
        # Simple heuristic
        words = len(text.split())
        return int(words * TokenCounter.TOKENS_PER_WORD)

    @staticmethod
    def estimate_context_tokens(messages: List[Dict]) -> int:
        """Estimate tokens in conversation context"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += TokenCounter.estimate_tokens(content)
        return total

    @staticmethod
    def estimate_response_tokens(response_length: str = "medium") -> int:
        """Estimate tokens in response"""
        estimates = {
            "short": 100,
            "medium": 300,
            "long": 500,
            "very_long": 1000,
        }
        return estimates.get(response_length, 300)


class CachingStrategy:
    """Cache frequently used responses"""

    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        self.cache_hits: int = 0
        self.cache_misses: int = 0

    def cache_key(self, prompt: str, context_hash: str) -> str:
        """Generate cache key"""
        import hashlib
        key = f"{hashlib.md5((prompt + context_hash).encode()).hexdigest()}"
        return key

    def get(self, key: str) -> Optional[Dict]:
        """Retrieve cached response"""
        if key in self.cache:
            self.cache_hits += 1
            self.cache[key]["last_accessed"] = datetime.now().isoformat()
            return self.cache[key]["response"]
        self.cache_misses += 1
        return None

    def set(self, key: str, response: str, tokens_saved: int = 0):
        """Cache response"""
        self.cache[key] = {
            "response": response,
            "tokens_saved": tokens_saved,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "access_count": 0,
        }

    def clear_old_entries(self, hours: int = 24):
        """Remove old cache entries"""
        cutoff = datetime.now() - timedelta(hours=hours)
        to_remove = [
            k for k, v in self.cache.items()
            if datetime.fromisoformat(v["last_accessed"]) < cutoff
        ]
        for k in to_remove:
            del self.cache[k]

    def get_cache_stats(self) -> Dict:
        """Get caching statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (
            (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        )

        total_tokens_saved = sum(
            v.get("tokens_saved", 0) for v in self.cache.values()
        )

        return {
            "cache_size": len(self.cache),
            "hit_rate": hit_rate,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_tokens_saved": total_tokens_saved,
        }


class CostOptimizationEngine:
    """Manage cost and performance optimization"""

    def __init__(self):
        self.budgets: Dict[str, TokenBudget] = {}
        self.metrics: List[PerformanceMetric] = []
        self.caching_strategy = CachingStrategy()
        self.token_counter = TokenCounter()
        self.recommendations: Dict[str, OptimizationRecommendation] = {}

    def create_budget(
        self,
        budget_id: str,
        total_tokens: int,
        context_ratio: float = 0.6,
    ) -> TokenBudget:
        """Create token budget for conversation"""
        budget = TokenBudget(
            budget_id=budget_id,
            total_tokens=total_tokens,
            allocated_for_context=int(total_tokens * context_ratio),
            allocated_for_response=int(total_tokens * (1 - context_ratio)) - 500,
        )
        self.budgets[budget_id] = budget
        return budget

    def check_budget(
        self,
        budget_id: str,
        required_tokens: int,
    ) -> Tuple[bool, Optional[str]]:
        """Check if budget allows operation"""
        if budget_id not in self.budgets:
            return False, "Budget not found"

        budget = self.budgets[budget_id]

        if required_tokens > budget.remaining_tokens:
            return (
                False,
                f"Insufficient budget: need {required_tokens}, have {budget.remaining_tokens}",
            )

        if budget.budget_utilization > 90:
            return (
                False,
                f"Budget nearly exhausted: {budget.budget_utilization:.0f}% used",
            )

        return True, None

    def record_metric(
        self,
        metric_type: str,
        value: float,
        unit: str,
        context: Optional[Dict] = None,
    ) -> PerformanceMetric:
        """Record performance metric"""
        metric = PerformanceMetric(
            metric_id=f"metric_{len(self.metrics)}",
            metric_type=metric_type,
            value=value,
            unit=unit,
            context=context or {},
        )
        self.metrics.append(metric)
        return metric

    def analyze_performance(self, window_minutes: int = 60) -> Dict[str, Any]:
        """Analyze performance over time window"""
        cutoff = datetime.now() - timedelta(minutes=window_minutes)

        recent_metrics = [
            m for m in self.metrics
            if datetime.fromisoformat(m.timestamp) >= cutoff
        ]

        latencies = [
            m.value for m in recent_metrics
            if m.metric_type == "latency"
        ]

        error_counts = [
            m.value for m in recent_metrics
            if m.metric_type == "error_rate"
        ]

        analysis = {
            "window_minutes": window_minutes,
            "metrics_count": len(recent_metrics),
            "avg_latency_ms": (
                sum(latencies) / len(latencies) if latencies else 0
            ),
            "max_latency_ms": max(latencies) if latencies else 0,
            "min_latency_ms": min(latencies) if latencies else 0,
            "error_rate": (
                sum(error_counts) / len(error_counts) if error_counts else 0
            ),
        }

        return analysis

    def generate_recommendations(self) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations"""
        recommendations = []

        # Analyze caching effectiveness
        cache_stats = self.caching_strategy.get_cache_stats()
        if cache_stats["cache_size"] == 0:
            recommendations.append(
                OptimizationRecommendation(
                    recommendation_id="rec_cache_001",
                    strategy=OptimizationStrategy.CACHING,
                    title="Enable Response Caching",
                    description="Cache frequently requested responses to reduce latency and token usage",
                    estimated_savings={
                        "token_count": 1000,
                        "latency_ms": 500,
                        "cost_usd": 0.02,
                    },
                    implementation_effort="low",
                    priority=8,
                )
            )

        # Analyze context size
        if self.metrics:
            recent_analysis = self.analyze_performance()
            if recent_analysis["avg_latency_ms"] > 2000:
                recommendations.append(
                    OptimizationRecommendation(
                        recommendation_id="rec_summarize_001",
                        strategy=OptimizationStrategy.SUMMARIZATION,
                        title="Summarize Context",
                        description="Compress conversation history to reduce token usage",
                        estimated_savings={
                            "token_count": 2000,
                            "latency_ms": 300,
                            "cost_usd": 0.05,
                        },
                        implementation_effort="medium",
                        priority=7,
                    )
                )

        return recommendations

    def get_cost_forecast(
        self,
        days_ahead: int = 7,
        avg_tokens_per_conversation: int = 2000,
        conversations_per_day: int = 100,
        cost_per_1k_tokens: float = 0.10,
    ) -> Dict[str, Any]:
        """Forecast costs"""
        total_tokens = days_ahead * conversations_per_day * avg_tokens_per_conversation
        total_cost = (total_tokens / 1000) * cost_per_1k_tokens

        return {
            "forecast_days": days_ahead,
            "estimated_conversations": days_ahead * conversations_per_day,
            "estimated_total_tokens": total_tokens,
            "cost_per_1k_tokens": cost_per_1k_tokens,
            "estimated_total_cost": total_cost,
            "estimated_daily_cost": total_cost / days_ahead,
        }

    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate optimization report"""
        cache_stats = self.caching_strategy.get_cache_stats()
        performance = self.analyze_performance()
        recommendations = self.generate_recommendations()

        return {
            "timestamp": datetime.now().isoformat(),
            "cache_statistics": cache_stats,
            "performance_analysis": performance,
            "recommendations": [r.to_dict() for r in recommendations],
            "active_budgets": len(self.budgets),
        }


# Global engine
cost_engine = CostOptimizationEngine()


# MCP Tools (add to memory_server.py)

def create_token_budget(
    budget_id: str,
    total_tokens: int,
    context_ratio: float = 0.6,
) -> dict:
    """Create token budget"""
    budget = cost_engine.create_budget(budget_id, total_tokens, context_ratio)
    return budget.to_dict()


def check_token_budget(budget_id: str, required_tokens: int) -> dict:
    """Check if budget available"""
    allowed, reason = cost_engine.check_budget(budget_id, required_tokens)
    return {"allowed": allowed, "reason": reason}


def record_performance_metric(
    metric_type: str,
    value: float,
    unit: str,
) -> dict:
    """Record performance metric"""
    metric = cost_engine.record_metric(metric_type, value, unit)
    return metric.to_dict()


def analyze_performance(window_minutes: int = 60) -> dict:
    """Analyze performance"""
    return cost_engine.analyze_performance(window_minutes)


def get_optimization_recommendations() -> dict:
    """Get optimization recommendations"""
    recommendations = cost_engine.generate_recommendations()
    return {
        "recommendations": [r.to_dict() for r in recommendations],
        "count": len(recommendations),
    }


def forecast_costs(
    days_ahead: int = 7,
    conversations_per_day: int = 100,
) -> dict:
    """Forecast conversation costs"""
    return cost_engine.get_cost_forecast(days_ahead=days_ahead, conversations_per_day=conversations_per_day)


def get_cost_optimization_report() -> dict:
    """Get cost optimization report"""
    return cost_engine.get_optimization_report()


if __name__ == "__main__":
    # Test cost optimization
    engine = CostOptimizationEngine()

    # Create budget
    budget = engine.create_budget("conv_001", 4000)
    print(f"Budget created: {budget.total_tokens} tokens")

    # Check budget
    allowed, reason = engine.check_budget("conv_001", 1000)
    print(f"Budget check: {allowed}")

    # Record metrics
    engine.record_metric("latency", 1500, "ms")
    engine.record_metric("error_rate", 0.02, "percent")

    # Analyze
    analysis = engine.analyze_performance()
    print(f"Performance: {json.dumps(analysis, indent=2)}")

    # Recommendations
    recs = engine.generate_recommendations()
    print(f"Recommendations: {len(recs)}")

    # Forecast
    forecast = engine.get_cost_forecast()
    print(f"7-day forecast: ${forecast['estimated_total_cost']:.2f}")
