"""Analytics and metrics dashboard for real-time monitoring"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

DASHBOARD_DIR = Path.home() / ".memory-mcp" / "dashboards"
DASHBOARD_DIR.mkdir(exist_ok=True, parents=True)


class MetricCategory(Enum):
    """Dashboard metric categories"""
    PERFORMANCE = "performance"
    QUALITY = "quality"
    USAGE = "usage"
    COST = "cost"
    HEALTH = "health"


class AnomalyDetection(Enum):
    """Anomaly types"""
    SPIKE = "spike"  # Sudden increase
    DROP = "drop"  # Sudden decrease
    TREND = "trend"  # Gradual change
    OUTLIER = "outlier"  # Unusual value
    SEASONAL = "seasonal"  # Expected variation


@dataclass
class MetricPoint:
    """Single data point"""
    timestamp: str
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Serialize point"""
        return {
            "timestamp": self.timestamp,
            "value": self.value,
            "metadata": self.metadata,
        }


@dataclass
class Anomaly:
    """Detected anomaly"""
    anomaly_id: str
    metric_name: str
    anomaly_type: AnomalyDetection
    severity: float  # 0-1
    detected_at: str
    value: float
    expected_range: tuple
    description: str
    auto_resolved: bool = False

    def to_dict(self) -> Dict:
        """Serialize anomaly"""
        return {
            "anomaly_id": self.anomaly_id,
            "metric_name": self.metric_name,
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity,
            "detected_at": self.detected_at,
            "value": self.value,
            "expected_range": self.expected_range,
            "description": self.description,
            "auto_resolved": self.auto_resolved,
        }


class Dashboard:
    """Analytics dashboard"""

    def __init__(self, dashboard_id: str, name: str):
        self.dashboard_id = dashboard_id
        self.name = name
        self.metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self.anomalies: Dict[str, List[Anomaly]] = defaultdict(list)
        self.created_at = datetime.now().isoformat()
        self.last_updated = self.created_at

    def record_metric(
        self,
        metric_name: str,
        value: float,
        metadata: Optional[Dict] = None,
    ) -> MetricPoint:
        """Record metric value"""
        point = MetricPoint(
            timestamp=datetime.now().isoformat(),
            value=value,
            metadata=metadata or {},
        )

        self.metrics[metric_name].append(point)
        self.last_updated = datetime.now().isoformat()

        return point

    def detect_anomalies(
        self,
        metric_name: str,
        window_points: int = 10,
        threshold_std: float = 2.0,
    ) -> List[Anomaly]:
        """Detect anomalies in metric"""
        if metric_name not in self.metrics or len(self.metrics[metric_name]) < window_points:
            return []

        recent_points = self.metrics[metric_name][-window_points:]
        values = [p.value for p in recent_points]

        # Calculate statistics
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5

        anomalies = []
        latest_value = values[-1]

        # Detect outliers (beyond threshold std devs)
        if abs(latest_value - mean) > threshold_std * std_dev:
            anomaly_type = (
                AnomalyDetection.SPIKE if latest_value > mean
                else AnomalyDetection.DROP
            )

            anomaly = Anomaly(
                anomaly_id=f"anom_{len(self.anomalies.get(metric_name, []))}",
                metric_name=metric_name,
                anomaly_type=anomaly_type,
                severity=min(1.0, abs(latest_value - mean) / (std_dev * 3)),
                detected_at=datetime.now().isoformat(),
                value=latest_value,
                expected_range=(mean - threshold_std * std_dev, mean + threshold_std * std_dev),
                description=f"Value {latest_value:.2f} deviates {(abs(latest_value - mean) / std_dev):.1f} std devs from mean",
            )

            anomalies.append(anomaly)
            if metric_name not in self.anomalies:
                self.anomalies[metric_name] = []
            self.anomalies[metric_name].append(anomaly)

        return anomalies

    def get_metric_summary(self, metric_name: str) -> Optional[Dict]:
        """Get summary statistics for metric"""
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return None

        points = self.metrics[metric_name]
        values = [p.value for p in points]

        return {
            "metric_name": metric_name,
            "current_value": values[-1],
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "count": len(values),
            "first_recorded": points[0].timestamp,
            "last_recorded": points[-1].timestamp,
        }

    def get_dashboard_view(self, category: Optional[MetricCategory] = None) -> Dict:
        """Get dashboard view"""
        metrics_data = {}

        for metric_name, points in self.metrics.items():
            if not points:
                continue

            summary = self.get_metric_summary(metric_name)
            recent_anomalies = self.anomalies.get(metric_name, [])

            metrics_data[metric_name] = {
                "summary": summary,
                "recent_points": [p.to_dict() for p in points[-10:]],
                "anomalies": [a.to_dict() for a in recent_anomalies[-5:]],
                "anomaly_count": len(recent_anomalies),
            }

        return {
            "dashboard_id": self.dashboard_id,
            "name": self.name,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "metrics": metrics_data,
            "metric_count": len(metrics_data),
            "total_anomalies": sum(len(a) for a in self.anomalies.values()),
        }

    def get_key_insights(self) -> List[str]:
        """Extract key insights"""
        insights = []

        for metric_name, points in self.metrics.items():
            if len(points) < 3:
                continue

            values = [p.value for p in points[-5:]]
            old_avg = sum([p.value for p in points[-10:-5]]) / 5 if len(points) >= 10 else values[0]
            new_avg = sum(values) / len(values)

            # Detect trends
            pct_change = ((new_avg - old_avg) / old_avg * 100) if old_avg != 0 else 0

            if pct_change > 10:
                insights.append(f"📈 {metric_name} increasing (+{pct_change:.0f}%)")
            elif pct_change < -10:
                insights.append(f"📉 {metric_name} decreasing ({pct_change:.0f}%)")

        # Anomaly insights
        high_severity_anomalies = [
            a for anomalies in self.anomalies.values()
            for a in anomalies
            if a.severity > 0.7 and not a.auto_resolved
        ]

        if high_severity_anomalies:
            insights.append(f"⚠️ {len(high_severity_anomalies)} high-severity anomalies")

        return insights[:5]

    def save_snapshot(self) -> str:
        """Save dashboard snapshot"""
        snapshot = {
            "dashboard_id": self.dashboard_id,
            "snapshot_at": datetime.now().isoformat(),
            "view": self.get_dashboard_view(),
            "insights": self.get_key_insights(),
        }

        filepath = DASHBOARD_DIR / f"{self.dashboard_id}_snapshot.json"
        with open(filepath, "w") as f:
            json.dump(snapshot, f, indent=2, default=str)

        return str(filepath)


class DashboardManager:
    """Manage multiple dashboards"""

    def __init__(self):
        self.dashboards: Dict[str, Dashboard] = {}

    def create_dashboard(self, dashboard_id: str, name: str) -> Dashboard:
        """Create new dashboard"""
        dashboard = Dashboard(dashboard_id, name)
        self.dashboards[dashboard_id] = dashboard
        return dashboard

    def record_metric(
        self,
        dashboard_id: str,
        metric_name: str,
        value: float,
    ) -> bool:
        """Record metric on dashboard"""
        if dashboard_id not in self.dashboards:
            return False

        self.dashboards[dashboard_id].record_metric(metric_name, value)
        return True

    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get dashboard"""
        return self.dashboards.get(dashboard_id)

    def get_all_dashboards_summary(self) -> List[Dict]:
        """Get summary of all dashboards"""
        summaries = []

        for dashboard in self.dashboards.values():
            view = dashboard.get_dashboard_view()
            insights = dashboard.get_key_insights()

            summaries.append({
                "dashboard_id": dashboard.dashboard_id,
                "name": dashboard.name,
                "metric_count": view["metric_count"],
                "anomaly_count": view["total_anomalies"],
                "top_insights": insights[:2],
                "last_updated": dashboard.last_updated,
            })

        return summaries


# Global manager
dashboard_manager = DashboardManager()


# MCP Tools (add to memory_server.py)

def create_metrics_dashboard(dashboard_id: str, name: str) -> dict:
    """Create dashboard"""
    dashboard = dashboard_manager.create_dashboard(dashboard_id, name)
    return {
        "dashboard_id": dashboard.dashboard_id,
        "name": dashboard.name,
        "created": True,
    }


def record_dashboard_metric(
    dashboard_id: str,
    metric_name: str,
    value: float,
) -> dict:
    """Record metric"""
    success = dashboard_manager.record_metric(dashboard_id, metric_name, value)
    return {"recorded": success, "metric": metric_name}


def get_dashboard_view(dashboard_id: str) -> dict:
    """Get dashboard view"""
    dashboard = dashboard_manager.get_dashboard(dashboard_id)
    if dashboard:
        return dashboard.get_dashboard_view()
    return {"error": "Dashboard not found"}


def detect_dashboard_anomalies(dashboard_id: str, metric_name: str) -> dict:
    """Detect anomalies"""
    dashboard = dashboard_manager.get_dashboard(dashboard_id)
    if not dashboard:
        return {"error": "Dashboard not found"}

    anomalies = dashboard.detect_anomalies(metric_name)
    return {
        "metric_name": metric_name,
        "anomalies_detected": len(anomalies),
        "anomalies": [a.to_dict() for a in anomalies],
    }


def get_dashboard_insights(dashboard_id: str) -> dict:
    """Get key insights"""
    dashboard = dashboard_manager.get_dashboard(dashboard_id)
    if not dashboard:
        return {"error": "Dashboard not found"}

    insights = dashboard.get_key_insights()
    return {
        "dashboard_id": dashboard_id,
        "insights": insights,
        "insight_count": len(insights),
    }


def get_all_dashboards(self) -> dict:
    """Get all dashboards"""
    summaries = dashboard_manager.get_all_dashboards_summary()
    return {
        "dashboards": summaries,
        "count": len(summaries),
    }


if __name__ == "__main__":
    # Test dashboard
    manager = DashboardManager()

    # Create dashboard
    dashboard = manager.create_dashboard("main", "Main Metrics")
    print(f"Dashboard: {dashboard.dashboard_id}")

    # Record metrics
    for i in range(20):
        dashboard.record_metric("latency_ms", 100 + i * 5)
        dashboard.record_metric("error_rate", 0.01 + (i * 0.001))

    # Detect anomalies
    anomalies = dashboard.detect_anomalies("latency_ms")
    print(f"Anomalies: {len(anomalies)}")

    # Get insights
    insights = dashboard.get_key_insights()
    print(f"Insights: {insights}")

    # Get view
    view = dashboard.get_dashboard_view()
    print(f"Metrics: {view['metric_count']}")
