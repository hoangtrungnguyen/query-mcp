"""Evaluation and benchmarking framework for conversation quality"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

EVALUATION_DIR = Path.home() / ".memory-mcp" / "evaluation"
EVALUATION_DIR.mkdir(exist_ok=True, parents=True)


class MetricType(Enum):
    """Types of evaluation metrics"""
    CORRECTNESS = "correctness"  # Is answer right?
    RELEVANCE = "relevance"  # Is answer on-topic?
    COMPLETENESS = "completeness"  # Does it fully address question?
    CLARITY = "clarity"  # Is it understandable?
    COHERENCE = "coherence"  # Does it flow logically?
    HELPFULNESS = "helpfulness"  # Would user find it useful?
    SAFETY = "safety"  # Does it avoid harms?
    EFFICIENCY = "efficiency"  # Tokens vs quality ratio


@dataclass
class EvaluationMetric:
    """Single metric in benchmark"""
    metric_id: str
    metric_type: MetricType
    name: str
    description: str
    scoring_fn: Callable[[str, str], float]  # (response, reference) -> score
    weight: float = 1.0  # Importance in overall score
    threshold: float = 0.7  # Minimum acceptable score

    def to_dict(self) -> Dict:
        """Serialize (without callable)"""
        return {
            "metric_id": self.metric_id,
            "metric_type": self.metric_type.value,
            "name": self.name,
            "description": self.description,
            "weight": self.weight,
            "threshold": self.threshold,
        }


@dataclass
class BenchmarkTest:
    """Single test case in benchmark suite"""
    test_id: str
    prompt: str
    reference_response: str
    category: str
    difficulty: str  # "easy", "medium", "hard"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Serialize test"""
        return {
            "test_id": self.test_id,
            "prompt": self.prompt,
            "reference_response": self.reference_response,
            "category": self.category,
            "difficulty": self.difficulty,
            "metadata": self.metadata,
        }


@dataclass
class EvaluationResult:
    """Results of evaluating a response"""
    result_id: str
    test_id: str
    agent_response: str
    metric_scores: Dict[str, float]  # metric_id -> score
    overall_score: float
    passed: bool  # overall_score >= threshold
    feedback: List[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize result"""
        return {
            "result_id": self.result_id,
            "test_id": self.test_id,
            "agent_response": self.agent_response,
            "metric_scores": self.metric_scores,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "feedback": self.feedback,
            "timestamp": self.timestamp,
        }


@dataclass
class BenchmarkRun:
    """Complete benchmark execution"""
    run_id: str
    benchmark_id: str
    results: List[EvaluationResult] = field(default_factory=list)
    created_at: str = ""
    completed_at: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    @property
    def pass_rate(self) -> float:
        """Percentage of tests passed"""
        if not self.results:
            return 0.0
        passed = sum(1 for r in self.results if r.passed)
        return (passed / len(self.results)) * 100

    @property
    def avg_score(self) -> float:
        """Average metric score"""
        if not self.results:
            return 0.0
        return sum(r.overall_score for r in self.results) / len(self.results)

    def to_dict(self) -> Dict:
        """Serialize run"""
        return {
            "run_id": self.run_id,
            "benchmark_id": self.benchmark_id,
            "test_count": len(self.results),
            "pass_rate": self.pass_rate,
            "avg_score": self.avg_score,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "results": [r.to_dict() for r in self.results],
        }


class BenchmarkSuite:
    """Collection of tests for evaluation"""

    def __init__(self, benchmark_id: str, name: str, description: str):
        self.benchmark_id = benchmark_id
        self.name = name
        self.description = description
        self.tests: Dict[str, BenchmarkTest] = {}
        self.metrics: Dict[str, EvaluationMetric] = {}
        self.created_at = datetime.now().isoformat()

    def add_test(self, test: BenchmarkTest) -> bool:
        """Add test to suite"""
        self.tests[test.test_id] = test
        return True

    def add_metric(self, metric: EvaluationMetric) -> bool:
        """Add evaluation metric"""
        self.metrics[metric.metric_id] = metric
        return True

    def to_dict(self) -> Dict:
        """Serialize suite"""
        return {
            "benchmark_id": self.benchmark_id,
            "name": self.name,
            "description": self.description,
            "test_count": len(self.tests),
            "metric_count": len(self.metrics),
            "created_at": self.created_at,
            "tests": [t.to_dict() for t in self.tests.values()],
            "metrics": [m.to_dict() for m in self.metrics.values()],
        }


class EvaluationEngine:
    """Execute evaluations and benchmarks"""

    def __init__(self):
        self.benchmarks: Dict[str, BenchmarkSuite] = {}
        self.runs: Dict[str, BenchmarkRun] = {}
        self.history: List[BenchmarkRun] = []

    def create_benchmark(
        self,
        benchmark_id: str,
        name: str,
        description: str,
    ) -> BenchmarkSuite:
        """Create benchmark suite"""
        suite = BenchmarkSuite(benchmark_id, name, description)
        self.benchmarks[benchmark_id] = suite
        return suite

    def evaluate_response(
        self,
        result_id: str,
        test_id: str,
        agent_response: str,
        benchmark_id: str,
    ) -> Optional[EvaluationResult]:
        """Evaluate single response"""
        if benchmark_id not in self.benchmarks:
            return None

        benchmark = self.benchmarks[benchmark_id]
        test = benchmark.tests.get(test_id)

        if not test:
            return None

        # Calculate metric scores
        metric_scores = {}
        for metric_id, metric in benchmark.metrics.items():
            try:
                score = metric.scoring_fn(agent_response, test.reference_response)
                metric_scores[metric_id] = max(0.0, min(1.0, score))
            except Exception:
                metric_scores[metric_id] = 0.0

        # Calculate weighted overall score
        total_weight = sum(m.weight for m in benchmark.metrics.values())
        overall_score = (
            sum(
                metric_scores[mid] * benchmark.metrics[mid].weight
                for mid in metric_scores
            )
            / total_weight
            if total_weight > 0
            else 0.0
        )

        # Determine pass/fail
        passed = all(
            metric_scores.get(mid, 0) >= benchmark.metrics[mid].threshold
            for mid in benchmark.metrics
        )

        result = EvaluationResult(
            result_id=result_id,
            test_id=test_id,
            agent_response=agent_response,
            metric_scores=metric_scores,
            overall_score=overall_score,
            passed=passed,
        )

        return result

    def run_benchmark(
        self,
        run_id: str,
        benchmark_id: str,
        evaluation_fn: Callable[[str], str],
    ) -> BenchmarkRun:
        """Run complete benchmark"""
        if benchmark_id not in self.benchmarks:
            return None

        benchmark = self.benchmarks[benchmark_id]
        run = BenchmarkRun(run_id, benchmark_id)

        for test in benchmark.tests.values():
            # Get response
            agent_response = evaluation_fn(test.prompt)

            # Evaluate
            result = self.evaluate_response(
                f"result_{run_id}_{test.test_id}",
                test.test_id,
                agent_response,
                benchmark_id,
            )

            if result:
                run.results.append(result)

        run.completed_at = datetime.now().isoformat()
        self.runs[run_id] = run
        self.history.append(run)

        return run

    def compare_runs(self, run_id_1: str, run_id_2: str) -> Dict[str, Any]:
        """Compare two benchmark runs"""
        run1 = self.runs.get(run_id_1)
        run2 = self.runs.get(run_id_2)

        if not run1 or not run2:
            return {}

        return {
            "run_1": {
                "run_id": run_id_1,
                "pass_rate": run1.pass_rate,
                "avg_score": run1.avg_score,
            },
            "run_2": {
                "run_id": run_id_2,
                "pass_rate": run2.pass_rate,
                "avg_score": run2.avg_score,
            },
            "improvement": {
                "pass_rate_change": run2.pass_rate - run1.pass_rate,
                "score_change": run2.avg_score - run1.avg_score,
                "better": run2.avg_score > run1.avg_score,
            },
        }

    def detect_regressions(self, benchmark_id: str) -> List[Dict]:
        """Detect performance regressions"""
        if benchmark_id not in self.benchmarks:
            return []

        benchmark_runs = [r for r in self.history if r.benchmark_id == benchmark_id]
        if len(benchmark_runs) < 2:
            return []

        regressions = []
        baseline = benchmark_runs[-2]
        latest = benchmark_runs[-1]

        if latest.avg_score < baseline.avg_score * 0.95:  # >5% drop
            regressions.append({
                "type": "score_regression",
                "severity": "high" if latest.avg_score < baseline.avg_score * 0.9 else "medium",
                "baseline_score": baseline.avg_score,
                "current_score": latest.avg_score,
            })

        if latest.pass_rate < baseline.pass_rate * 0.95:
            regressions.append({
                "type": "pass_rate_regression",
                "severity": "high",
                "baseline_pass_rate": baseline.pass_rate,
                "current_pass_rate": latest.pass_rate,
            })

        return regressions

    def get_evaluation_report(self, run_id: str) -> Optional[Dict]:
        """Get detailed evaluation report"""
        if run_id not in self.runs:
            return None

        run = self.runs[run_id]
        benchmark = self.benchmarks[run.benchmark_id]

        # Group results by category
        by_category = defaultdict(list)
        for result in run.results:
            test = benchmark.tests[result.test_id]
            by_category[test.category].append(result)

        category_summary = {}
        for category, results in by_category.items():
            passed = sum(1 for r in results if r.passed)
            category_summary[category] = {
                "total": len(results),
                "passed": passed,
                "pass_rate": (passed / len(results) * 100) if results else 0,
                "avg_score": sum(r.overall_score for r in results) / len(results) if results else 0,
            }

        return {
            "run_id": run_id,
            "benchmark_id": run.benchmark_id,
            "overall_pass_rate": run.pass_rate,
            "overall_score": run.avg_score,
            "test_count": len(run.results),
            "by_category": category_summary,
            "timestamp": run.created_at,
        }


# Global engine
evaluation_engine = EvaluationEngine()


# MCP Tools (add to memory_server.py)

def create_benchmark(
    benchmark_id: str,
    name: str,
    description: str,
) -> dict:
    """Create benchmark suite"""
    suite = evaluation_engine.create_benchmark(benchmark_id, name, description)
    return {
        "benchmark_id": suite.benchmark_id,
        "name": suite.name,
        "created": True,
    }


def add_benchmark_test(
    benchmark_id: str,
    test_id: str,
    prompt: str,
    reference_response: str,
    category: str,
    difficulty: str = "medium",
) -> dict:
    """Add test to benchmark"""
    if benchmark_id not in evaluation_engine.benchmarks:
        return {"error": "Benchmark not found"}

    test = BenchmarkTest(
        test_id=test_id,
        prompt=prompt,
        reference_response=reference_response,
        category=category,
        difficulty=difficulty,
    )
    success = evaluation_engine.benchmarks[benchmark_id].add_test(test)
    return {"test_id": test_id, "added": success}


def evaluate_response(
    benchmark_id: str,
    test_id: str,
    agent_response: str,
) -> dict:
    """Evaluate single response"""
    result = evaluation_engine.evaluate_response(
        f"result_{test_id}",
        test_id,
        agent_response,
        benchmark_id,
    )
    return result.to_dict() if result else {"error": "Test not found"}


def get_evaluation_report(run_id: str) -> dict:
    """Get evaluation report"""
    report = evaluation_engine.get_evaluation_report(run_id)
    return report or {"error": "Run not found"}


def compare_benchmark_runs(run_id_1: str, run_id_2: str) -> dict:
    """Compare two benchmark runs"""
    return evaluation_engine.compare_runs(run_id_1, run_id_2)


def detect_benchmark_regressions(benchmark_id: str) -> dict:
    """Detect performance regressions"""
    regressions = evaluation_engine.detect_regressions(benchmark_id)
    return {"regressions": regressions, "count": len(regressions)}


if __name__ == "__main__":
    # Test evaluation
    engine = EvaluationEngine()

    # Create benchmark
    suite = engine.create_benchmark(
        "qa_benchmark",
        "QA Benchmark",
        "Question answering quality",
    )

    # Add test
    test = BenchmarkTest(
        test_id="test_1",
        prompt="What is Python?",
        reference_response="Python is a programming language",
        category="definitions",
        difficulty="easy",
    )
    suite.add_test(test)

    # Add metric
    metric = EvaluationMetric(
        metric_id="m_relevance",
        metric_type=MetricType.RELEVANCE,
        name="Relevance",
        description="Is response relevant?",
        scoring_fn=lambda r, ref: 0.9,  # Dummy
        weight=1.0,
    )
    suite.add_metric(metric)

    # Evaluate
    result = engine.evaluate_response(
        "result_1",
        "test_1",
        "Python is a programming language",
        "qa_benchmark",
    )
    print(f"Evaluation: {result.overall_score:.2f}")
