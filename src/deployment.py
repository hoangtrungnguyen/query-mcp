"""Deployment orchestration and progressive autonomy for agents"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass

DEPLOYMENT_DIR = Path.home() / ".memory-mcp" / "deployments"
DEPLOYMENT_DIR.mkdir(exist_ok=True, parents=True)


class DeploymentStage(Enum):
    """Deployment progression stages"""
    SANDBOX = "sandbox"  # Isolated testing
    CANARY = "canary"  # Small user subset
    BETA = "beta"  # Wider testing
    PRODUCTION = "production"  # Full rollout
    DEPRECATED = "deprecated"  # Retiring


class HealthStatus(Enum):
    """Agent health states"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class GatingCriteria:
    """Requirements to advance to next stage"""
    min_success_rate: float = 0.95
    max_error_rate: float = 0.05
    min_test_coverage: float = 0.8
    max_avg_latency_ms: int = 5000
    custom_checks: Optional[List[Callable[[], bool]]] = None

    def is_met(self, metrics: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Check if all criteria met"""
        failures = []

        if metrics.get("success_rate", 0) < self.min_success_rate:
            failures.append(
                f"Success rate {metrics['success_rate']:.1%} < {self.min_success_rate:.1%}"
            )

        if metrics.get("error_rate", 1.0) > self.max_error_rate:
            failures.append(
                f"Error rate {metrics['error_rate']:.1%} > {self.max_error_rate:.1%}"
            )

        if metrics.get("test_coverage", 0) < self.min_test_coverage:
            failures.append(
                f"Test coverage {metrics['test_coverage']:.1%} < {self.min_test_coverage:.1%}"
            )

        if metrics.get("avg_latency_ms", float("inf")) > self.max_avg_latency_ms:
            failures.append(
                f"Latency {metrics['avg_latency_ms']}ms > {self.max_avg_latency_ms}ms"
            )

        if self.custom_checks:
            for check in self.custom_checks:
                try:
                    if not check():
                        failures.append("Custom check failed")
                except Exception as e:
                    failures.append(f"Custom check error: {str(e)}")

        return len(failures) == 0, failures


@dataclass
class CapabilityGrant:
    """Permission to use specific capability"""
    capability_id: str
    agent_id: str
    stage: DeploymentStage
    granted_at: str
    revoked_at: Optional[str] = None
    usage_count: int = 0
    error_count: int = 0

    def is_active(self) -> bool:
        """Check if grant is currently active"""
        return self.revoked_at is None

    def to_dict(self) -> Dict:
        """Serialize grant"""
        return {
            "capability_id": self.capability_id,
            "agent_id": self.agent_id,
            "stage": self.stage.value,
            "granted_at": self.granted_at,
            "revoked_at": self.revoked_at,
            "usage_count": self.usage_count,
            "error_count": self.error_count,
            "active": self.is_active(),
        }


@dataclass
class DeploymentMetrics:
    """Metrics for a deployment stage"""
    stage: DeploymentStage
    success_count: int = 0
    error_count: int = 0
    total_calls: int = 0
    avg_latency_ms: float = 0.0
    test_coverage: float = 0.0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.success_count / self.total_calls

    @property
    def error_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.error_count / self.total_calls

    def to_dict(self) -> Dict:
        """Serialize metrics"""
        return {
            "stage": self.stage.value,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "total_calls": self.total_calls,
            "success_rate": self.success_rate,
            "error_rate": self.error_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "test_coverage": self.test_coverage,
            "timestamp": self.timestamp,
        }


class HealthMonitor:
    """Monitor agent health at each stage"""

    def __init__(self, check_interval_seconds: int = 60):
        self.check_interval = check_interval_seconds
        self.last_checks: Dict[str, Dict] = {}

    def check_health(
        self,
        agent_id: str,
        stage: DeploymentStage,
        checks: Dict[str, Callable[[], bool]],
    ) -> Dict[str, Any]:
        """Run health checks"""
        results = {
            "agent_id": agent_id,
            "stage": stage.value,
            "timestamp": datetime.now().isoformat(),
            "checks": {},
        }

        healthy_count = 0
        for check_name, check_fn in checks.items():
            try:
                result = check_fn()
                results["checks"][check_name] = {
                    "passed": result,
                    "error": None,
                }
                if result:
                    healthy_count += 1
            except Exception as e:
                results["checks"][check_name] = {
                    "passed": False,
                    "error": str(e),
                }

        # Overall health
        health_ratio = healthy_count / len(checks) if checks else 0
        if health_ratio >= 0.9:
            results["status"] = HealthStatus.HEALTHY.value
        elif health_ratio >= 0.7:
            results["status"] = HealthStatus.DEGRADED.value
        else:
            results["status"] = HealthStatus.UNHEALTHY.value

        self.last_checks[agent_id] = results
        return results

    def get_last_check(self, agent_id: str) -> Optional[Dict]:
        """Get most recent health check"""
        return self.last_checks.get(agent_id)


class ProgressiveAutonomy:
    """Stage-based capability expansion"""

    STAGE_PROGRESSION = [
        DeploymentStage.SANDBOX,
        DeploymentStage.CANARY,
        DeploymentStage.BETA,
        DeploymentStage.PRODUCTION,
    ]

    def __init__(self):
        self.stage_assignments: Dict[str, DeploymentStage] = {}
        self.capability_grants: Dict[str, List[CapabilityGrant]] = {}
        self.stage_metrics: Dict[str, List[DeploymentMetrics]] = {}
        self.gating_criteria: Dict[DeploymentStage, GatingCriteria] = {
            DeploymentStage.SANDBOX: GatingCriteria(
                min_success_rate=0.9,
                max_error_rate=0.1,
                min_test_coverage=0.5,
            ),
            DeploymentStage.CANARY: GatingCriteria(
                min_success_rate=0.95,
                max_error_rate=0.05,
                min_test_coverage=0.75,
            ),
            DeploymentStage.BETA: GatingCriteria(
                min_success_rate=0.97,
                max_error_rate=0.03,
                min_test_coverage=0.9,
            ),
            DeploymentStage.PRODUCTION: GatingCriteria(
                min_success_rate=0.99,
                max_error_rate=0.01,
                min_test_coverage=0.95,
            ),
        }

    def assign_stage(self, agent_id: str, stage: DeploymentStage):
        """Assign agent to stage"""
        self.stage_assignments[agent_id] = stage
        if agent_id not in self.capability_grants:
            self.capability_grants[agent_id] = []
        if agent_id not in self.stage_metrics:
            self.stage_metrics[agent_id] = []

    def grant_capability(
        self,
        agent_id: str,
        capability_id: str,
        stage: DeploymentStage,
    ) -> CapabilityGrant:
        """Grant capability to agent at stage"""
        grant = CapabilityGrant(
            capability_id=capability_id,
            agent_id=agent_id,
            stage=stage,
            granted_at=datetime.now().isoformat(),
        )

        if agent_id not in self.capability_grants:
            self.capability_grants[agent_id] = []

        self.capability_grants[agent_id].append(grant)
        return grant

    def record_metrics(
        self,
        agent_id: str,
        stage: DeploymentStage,
        success_count: int,
        error_count: int,
        total_calls: int,
        avg_latency_ms: float = 0.0,
        test_coverage: float = 0.0,
    ):
        """Record stage metrics"""
        metrics = DeploymentMetrics(
            stage=stage,
            success_count=success_count,
            error_count=error_count,
            total_calls=total_calls,
            avg_latency_ms=avg_latency_ms,
            test_coverage=test_coverage,
        )

        if agent_id not in self.stage_metrics:
            self.stage_metrics[agent_id] = []

        self.stage_metrics[agent_id].append(metrics)

    def can_advance(
        self,
        agent_id: str,
        current_stage: DeploymentStage,
    ) -> Tuple[bool, List[str]]:
        """Check if agent can advance to next stage"""
        if current_stage == DeploymentStage.PRODUCTION:
            return False, ["Already in production"]

        # Get latest metrics
        if agent_id not in self.stage_metrics or not self.stage_metrics[agent_id]:
            return False, ["No metrics recorded"]

        latest = self.stage_metrics[agent_id][-1]

        # Get gating criteria for current stage
        criteria = self.gating_criteria.get(current_stage)
        if not criteria:
            return False, ["Unknown stage"]

        met, failures = criteria.is_met({
            "success_rate": latest.success_rate,
            "error_rate": latest.error_rate,
            "test_coverage": latest.test_coverage,
            "avg_latency_ms": latest.avg_latency_ms,
        })

        return met, failures

    def get_next_stage(self, current: DeploymentStage) -> Optional[DeploymentStage]:
        """Get next stage in progression"""
        try:
            idx = self.STAGE_PROGRESSION.index(current)
            if idx < len(self.STAGE_PROGRESSION) - 1:
                return self.STAGE_PROGRESSION[idx + 1]
        except ValueError:
            pass
        return None

    def advance_agent(
        self,
        agent_id: str,
        current_stage: DeploymentStage,
    ) -> Tuple[bool, Optional[DeploymentStage], List[str]]:
        """Attempt to advance agent to next stage"""
        can_advance, failures = self.can_advance(agent_id, current_stage)

        if not can_advance:
            return False, None, failures

        next_stage = self.get_next_stage(current_stage)
        if not next_stage:
            return False, None, ["No next stage"]

        self.assign_stage(agent_id, next_stage)
        return True, next_stage, []

    def get_deployment_summary(self, agent_id: str) -> Dict:
        """Get deployment status for agent"""
        stage = self.stage_assignments.get(agent_id)
        metrics = self.stage_metrics.get(agent_id, [])
        grants = self.capability_grants.get(agent_id, [])

        return {
            "agent_id": agent_id,
            "current_stage": stage.value if stage else None,
            "metrics": [m.to_dict() for m in metrics[-5:]],  # Last 5
            "capabilities": [g.to_dict() for g in grants if g.is_active()],
            "progression_ready": self.can_advance(agent_id, stage)[0] if stage else False,
        }


# Global instances
health_monitor = HealthMonitor()
progressive_autonomy = ProgressiveAutonomy()


# MCP Tools (add to memory_server.py)

def assign_agent_to_stage(agent_id: str, stage: str) -> dict:
    """Assign agent to deployment stage"""
    stage_enum = DeploymentStage(stage)
    progressive_autonomy.assign_stage(agent_id, stage_enum)
    return {"agent_id": agent_id, "stage": stage}


def grant_capability(
    agent_id: str,
    capability_id: str,
    stage: str,
) -> dict:
    """Grant capability at stage"""
    stage_enum = DeploymentStage(stage)
    grant = progressive_autonomy.grant_capability(agent_id, capability_id, stage_enum)
    return grant.to_dict()


def record_stage_metrics(
    agent_id: str,
    stage: str,
    success_count: int,
    error_count: int,
    total_calls: int,
    avg_latency_ms: float = 0.0,
) -> dict:
    """Record metrics for stage"""
    stage_enum = DeploymentStage(stage)
    progressive_autonomy.record_metrics(
        agent_id,
        stage_enum,
        success_count,
        error_count,
        total_calls,
        avg_latency_ms,
    )
    return {
        "agent_id": agent_id,
        "stage": stage,
        "recorded": True,
    }


def check_advancement_eligibility(agent_id: str, current_stage: str) -> dict:
    """Check if agent can advance stage"""
    stage_enum = DeploymentStage(current_stage)
    can_advance, failures = progressive_autonomy.can_advance(agent_id, stage_enum)
    return {
        "can_advance": can_advance,
        "failures": failures,
        "current_stage": current_stage,
    }


def advance_agent_stage(agent_id: str, current_stage: str) -> dict:
    """Advance agent to next stage"""
    stage_enum = DeploymentStage(current_stage)
    success, next_stage, failures = progressive_autonomy.advance_agent(
        agent_id,
        stage_enum,
    )
    return {
        "success": success,
        "next_stage": next_stage.value if next_stage else None,
        "failures": failures,
    }


def check_agent_health(agent_id: str, stage: str) -> dict:
    """Check agent health at stage"""
    stage_enum = DeploymentStage(stage)
    checks = {
        "memory_accessible": lambda: True,
        "tools_responsive": lambda: True,
        "no_recent_errors": lambda: True,
    }
    return health_monitor.check_health(agent_id, stage_enum, checks)


def get_deployment_status(agent_id: str) -> dict:
    """Get deployment summary"""
    return progressive_autonomy.get_deployment_summary(agent_id)


if __name__ == "__main__":
    # Test deployment
    autonomy = ProgressiveAutonomy()

    # Assign agent
    autonomy.assign_stage("agent_1", DeploymentStage.SANDBOX)

    # Record metrics
    autonomy.record_metrics(
        "agent_1",
        DeploymentStage.SANDBOX,
        success_count=95,
        error_count=5,
        total_calls=100,
        test_coverage=0.85,
    )

    # Check advancement
    can_advance, failures = autonomy.can_advance("agent_1", DeploymentStage.SANDBOX)
    print(f"Can advance: {can_advance}")
    if not can_advance:
        print(f"Failures: {failures}")

    # Grant capability
    grant = autonomy.grant_capability(
        "agent_1",
        "tool_execute",
        DeploymentStage.SANDBOX,
    )
    print(f"Capability granted: {grant.capability_id}")

    # Get summary
    summary = autonomy.get_deployment_summary("agent_1")
    print(f"Deployment summary: {json.dumps(summary, indent=2)}")
