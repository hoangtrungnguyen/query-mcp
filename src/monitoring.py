"""Production monitoring, SLO tracking, and incident response for agent systems"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

MONITORING_DIR = Path.home() / ".memory-mcp" / "monitoring"
MONITORING_DIR.mkdir(exist_ok=True, parents=True)


class SeverityLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class HealthCheck(Enum):
    """Types of health checks"""
    AVAILABILITY = "availability"  # Is service up?
    LATENCY = "latency"  # Response time acceptable?
    ERROR_RATE = "error_rate"  # Errors within SLO?
    TOKEN_USAGE = "token_usage"  # Token consumption
    MEMORY = "memory"  # Memory usage
    CONTEXT_WINDOW = "context_window"  # Context coherence
    TOOL_HEALTH = "tool_health"  # Tool availability
    DEPENDENCY_HEALTH = "dependency_health"  # External deps


@dataclass
class SLOTarget:
    """Service Level Objective definition"""
    metric_name: str
    target_value: float
    comparison: str  # "less_than", "greater_than", "equal_to"
    time_window_minutes: int
    alert_threshold: float  # % of SLO violation before alerting

    def to_dict(self) -> Dict:
        """Serialize SLO"""
        return {
            "metric_name": self.metric_name,
            "target_value": self.target_value,
            "comparison": self.comparison,
            "time_window_minutes": self.time_window_minutes,
            "alert_threshold": self.alert_threshold,
        }


@dataclass
class AlertRule:
    """Condition triggering alert"""
    rule_id: str
    name: str
    condition_fn: Callable[[], bool]
    severity: SeverityLevel
    notification_channels: List[str]
    cooldown_minutes: int = 5

    def to_dict(self) -> Dict:
        """Serialize rule (without callable)"""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "severity": self.severity.value,
            "notification_channels": self.notification_channels,
            "cooldown_minutes": self.cooldown_minutes,
        }


@dataclass
class Alert:
    """Triggered alert instance"""
    alert_id: str
    rule_id: str
    severity: SeverityLevel
    title: str
    description: str
    triggered_at: str
    resolved_at: Optional[str] = None
    context: Dict[str, Any] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}

    def to_dict(self) -> Dict:
        """Serialize alert"""
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "triggered_at": self.triggered_at,
            "resolved_at": self.resolved_at,
            "context": self.context,
            "is_active": self.resolved_at is None,
        }


@dataclass
class HealthCheckResult:
    """Result of health check"""
    check_type: HealthCheck
    passed: bool
    message: str
    timestamp: str = ""
    metrics: Dict[str, float] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if self.metrics is None:
            self.metrics = {}

    def to_dict(self) -> Dict:
        """Serialize result"""
        return {
            "check_type": self.check_type.value,
            "passed": self.passed,
            "message": self.message,
            "timestamp": self.timestamp,
            "metrics": self.metrics,
        }


class IncidentManager:
    """Track and manage incidents"""

    def __init__(self):
        self.incidents: Dict[str, Dict] = {}
        self.incident_timeline: List[Dict] = []

    def open_incident(
        self,
        incident_id: str,
        severity: SeverityLevel,
        title: str,
        description: str,
        triggered_by: Optional[str] = None,
    ) -> Dict:
        """Open new incident"""
        incident = {
            "incident_id": incident_id,
            "severity": severity.value,
            "title": title,
            "description": description,
            "triggered_by": triggered_by,
            "opened_at": datetime.now().isoformat(),
            "closed_at": None,
            "status": "open",
            "resolution": None,
            "root_cause": None,
        }

        self.incidents[incident_id] = incident
        self.incident_timeline.append({
            "action": "open",
            "incident_id": incident_id,
            "timestamp": datetime.now().isoformat(),
        })

        return incident

    def update_incident(
        self,
        incident_id: str,
        status: Optional[str] = None,
        resolution: Optional[str] = None,
        root_cause: Optional[str] = None,
    ) -> Optional[Dict]:
        """Update incident status"""
        if incident_id not in self.incidents:
            return None

        incident = self.incidents[incident_id]
        if status:
            incident["status"] = status
        if resolution:
            incident["resolution"] = resolution
        if root_cause:
            incident["root_cause"] = root_cause

        if status == "closed":
            incident["closed_at"] = datetime.now().isoformat()

        self.incident_timeline.append({
            "action": "update",
            "incident_id": incident_id,
            "changes": {"status": status, "resolution": resolution},
            "timestamp": datetime.now().isoformat(),
        })

        return incident

    def get_incident(self, incident_id: str) -> Optional[Dict]:
        """Get incident details"""
        return self.incidents.get(incident_id)

    def get_open_incidents(self) -> List[Dict]:
        """Get all open incidents"""
        return [
            i for i in self.incidents.values()
            if i["status"] == "open"
        ]

    def get_incident_summary(self) -> Dict:
        """Get incident statistics"""
        all_incidents = list(self.incidents.values())

        return {
            "total_incidents": len(all_incidents),
            "open_incidents": sum(1 for i in all_incidents if i["status"] == "open"),
            "closed_incidents": sum(1 for i in all_incidents if i["status"] == "closed"),
            "by_severity": {
                severity.value: sum(1 for i in all_incidents if i["severity"] == severity.value)
                for severity in SeverityLevel
            },
        }


class MonitoringSystem:
    """Complete monitoring and alerting system"""

    def __init__(self):
        self.slo_targets: Dict[str, SLOTarget] = {}
        self.alert_rules: Dict[str, AlertRule] = {}
        self.alerts: List[Alert] = []
        self.alert_history: Dict[str, datetime] = {}  # Last alert time per rule
        self.health_checks: List[HealthCheckResult] = []
        self.incident_manager = IncidentManager()
        self.metrics_store: Dict[str, List[float]] = defaultdict(list)

    def define_slo(self, slo_id: str, target: SLOTarget):
        """Define Service Level Objective"""
        self.slo_targets[slo_id] = target

    def create_alert_rule(
        self,
        rule_id: str,
        name: str,
        condition_fn: Callable[[], bool],
        severity: SeverityLevel,
        notification_channels: List[str],
    ) -> AlertRule:
        """Create alert rule"""
        rule = AlertRule(
            rule_id=rule_id,
            name=name,
            condition_fn=condition_fn,
            severity=severity,
            notification_channels=notification_channels,
        )
        self.alert_rules[rule_id] = rule
        return rule

    def check_slo(
        self,
        slo_id: str,
        current_value: float,
    ) -> Tuple[bool, str]:
        """Check if SLO target is met"""
        if slo_id not in self.slo_targets:
            return False, f"SLO {slo_id} not found"

        slo = self.slo_targets[slo_id]
        self.metrics_store[slo_id].append(current_value)

        # Keep last 1000 values
        if len(self.metrics_store[slo_id]) > 1000:
            self.metrics_store[slo_id] = self.metrics_store[slo_id][-1000:]

        if slo.comparison == "less_than":
            met = current_value < slo.target_value
        elif slo.comparison == "greater_than":
            met = current_value > slo.target_value
        else:
            met = current_value == slo.target_value

        message = f"{slo.metric_name}: {current_value} {'meets' if met else 'violates'} {slo.comparison} {slo.target_value}"
        return met, message

    def record_metric(self, metric_name: str, value: float):
        """Record metric value"""
        self.metrics_store[metric_name].append(value)
        if len(self.metrics_store[metric_name]) > 1000:
            self.metrics_store[metric_name] = self.metrics_store[metric_name][-1000:]

    def perform_health_check(
        self,
        check_type: HealthCheck,
        check_fn: Callable[[], bool],
    ) -> HealthCheckResult:
        """Perform health check"""
        try:
            passed = check_fn()
            message = f"{check_type.value} check {'passed' if passed else 'failed'}"
        except Exception as e:
            passed = False
            message = f"{check_type.value} check error: {str(e)}"

        result = HealthCheckResult(
            check_type=check_type,
            passed=passed,
            message=message,
        )

        self.health_checks.append(result)
        return result

    def evaluate_alerts(self) -> List[Alert]:
        """Evaluate all alert rules and trigger if needed"""
        triggered = []
        now = datetime.now()

        for rule_id, rule in self.alert_rules.items():
            try:
                if rule.condition_fn():
                    # Check cooldown
                    last_alert = self.alert_history.get(rule_id)
                    if last_alert and (now - last_alert).total_seconds() < rule.cooldown_minutes * 60:
                        continue

                    # Trigger alert
                    alert = Alert(
                        alert_id=f"alert_{rule_id}_{int(now.timestamp())}",
                        rule_id=rule_id,
                        severity=rule.severity,
                        title=rule.name,
                        description=f"Alert rule {rule.name} triggered",
                        triggered_at=now.isoformat(),
                    )

                    self.alerts.append(alert)
                    self.alert_history[rule_id] = now
                    triggered.append(alert)

            except Exception:
                pass

        return triggered

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        recent_checks = self.health_checks[-10:] if self.health_checks else []
        healthy_checks = sum(1 for c in recent_checks if c.passed)

        open_incidents = self.incident_manager.get_open_incidents()
        active_alerts = [a for a in self.alerts if a.resolved_at is None]

        health_score = (healthy_checks / len(recent_checks)) if recent_checks else 0.5

        return {
            "health_score": health_score,
            "status": "healthy" if health_score > 0.9 else "degraded" if health_score > 0.7 else "unhealthy",
            "active_alerts": len(active_alerts),
            "open_incidents": len(open_incidents),
            "recent_checks": [c.to_dict() for c in recent_checks],
            "last_check_time": recent_checks[-1].timestamp if recent_checks else None,
        }

    def get_monitoring_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        return {
            "generated_at": datetime.now().isoformat(),
            "system_status": self.get_system_status(),
            "slo_compliance": {
                slo_id: {
                    "target": slo.to_dict(),
                    "recent_values": self.metrics_store.get(slo_id, [])[-50:],
                }
                for slo_id, slo in self.slo_targets.items()
            },
            "alerts": [a.to_dict() for a in self.alerts[-50:]],
            "incidents": self.incident_manager.get_incident_summary(),
        }

    def save_monitoring_report(self, report_id: str) -> str:
        """Save monitoring report to file"""
        report = self.get_monitoring_report()
        filepath = MONITORING_DIR / f"{report_id}_report.json"
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)
        return str(filepath)


# Global monitoring system
monitoring_system = MonitoringSystem()


# MCP Tools (add to memory_server.py)

def define_slo(
    slo_id: str,
    metric_name: str,
    target_value: float,
    comparison: str,
    time_window_minutes: int = 60,
) -> dict:
    """Define Service Level Objective"""
    slo = SLOTarget(
        metric_name=metric_name,
        target_value=target_value,
        comparison=comparison,
        time_window_minutes=time_window_minutes,
    )
    monitoring_system.define_slo(slo_id, slo)
    return slo.to_dict()


def record_metric(metric_name: str, value: float) -> dict:
    """Record metric value"""
    monitoring_system.record_metric(metric_name, value)
    return {"metric": metric_name, "value": value, "recorded": True}


def check_slo_compliance(slo_id: str, current_value: float) -> dict:
    """Check SLO compliance"""
    met, message = monitoring_system.check_slo(slo_id, current_value)
    return {
        "slo_id": slo_id,
        "met": met,
        "message": message,
        "compliant": met,
    }


def perform_health_check(check_type: str) -> dict:
    """Perform health check"""
    check_enum = HealthCheck(check_type)
    # Define check function
    check_fn = lambda: True  # Simulated
    result = monitoring_system.perform_health_check(check_enum, check_fn)
    return result.to_dict()


def evaluate_alerts() -> dict:
    """Evaluate all alert rules"""
    alerts = monitoring_system.evaluate_alerts()
    return {
        "triggered_alerts": [a.to_dict() for a in alerts],
        "count": len(alerts),
    }


def get_system_status() -> dict:
    """Get system health status"""
    return monitoring_system.get_system_status()


def open_incident(
    incident_id: str,
    severity: str,
    title: str,
    description: str,
) -> dict:
    """Open new incident"""
    incident = monitoring_system.incident_manager.open_incident(
        incident_id,
        SeverityLevel(severity),
        title,
        description,
    )
    return incident


def close_incident(
    incident_id: str,
    resolution: str,
    root_cause: str = None,
) -> dict:
    """Close incident"""
    incident = monitoring_system.incident_manager.update_incident(
        incident_id,
        status="closed",
        resolution=resolution,
        root_cause=root_cause,
    )
    return incident or {"error": "Incident not found"}


def get_monitoring_report() -> dict:
    """Get comprehensive monitoring report"""
    return monitoring_system.get_monitoring_report()


if __name__ == "__main__":
    # Test monitoring
    system = MonitoringSystem()

    # Define SLO
    slo = SLOTarget(
        metric_name="response_latency",
        target_value=1000,
        comparison="less_than",
        time_window_minutes=60,
    )
    system.define_slo("latency_slo", slo)

    # Check SLO
    met, msg = system.check_slo("latency_slo", 800)
    print(f"SLO check: {msg}")

    # Perform health check
    result = system.perform_health_check(
        HealthCheck.AVAILABILITY,
        lambda: True,
    )
    print(f"Health check: {result.message}")

    # Get status
    status = system.get_system_status()
    print(f"System status: {json.dumps(status, indent=2)}")
