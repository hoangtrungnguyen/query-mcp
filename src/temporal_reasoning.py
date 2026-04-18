"""Temporal reasoning and scheduling for constrained execution"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

TEMPORAL_DIR = Path.home() / ".memory-mcp" / "temporal-reasoning"
TEMPORAL_DIR.mkdir(exist_ok=True, parents=True)


class TemporalRelation(Enum):
    """Temporal relationships between events"""
    BEFORE = "before"  # A happens before B
    AFTER = "after"  # A happens after B
    DURING = "during"  # A happens during B
    OVERLAPS = "overlaps"  # A and B overlap
    MEETS = "meets"  # A ends when B starts
    CONTAINS = "contains"  # A contains B
    EQUAL = "equal"  # A and B are same time


class ConstraintType(Enum):
    """Types of temporal constraints"""
    DEADLINE = "deadline"  # Must complete by
    MINIMUM_DURATION = "minimum_duration"  # Must take at least this long
    MAXIMUM_DURATION = "maximum_duration"  # Cannot exceed this
    START_TIME = "start_time"  # Must start at/after
    END_TIME = "end_time"  # Must end by
    PRECEDENCE = "precedence"  # Must happen after another
    EXCLUSION = "exclusion"  # Cannot overlap with another


@dataclass
class TimeInterval:
    """Time interval representation"""
    start_time: datetime
    end_time: datetime
    duration_minutes: int = 0

    def __post_init__(self):
        if self.duration_minutes == 0:
            self.duration_minutes = int(
                (self.end_time - self.start_time).total_seconds() / 60
            )

    def overlaps(self, other: 'TimeInterval') -> bool:
        """Check if intervals overlap"""
        return self.start_time < other.end_time and other.start_time < self.end_time

    def contains(self, other: 'TimeInterval') -> bool:
        """Check if contains another interval"""
        return self.start_time <= other.start_time and other.end_time <= self.end_time

    def to_dict(self) -> Dict:
        """Serialize interval"""
        return {
            "start": self.start_time.isoformat(),
            "end": self.end_time.isoformat(),
            "duration_minutes": self.duration_minutes,
        }


@dataclass
class TemporalEvent:
    """Event with temporal properties"""
    event_id: str
    name: str
    scheduled_time: datetime
    duration_minutes: int
    dependencies: List[str] = field(default_factory=list)  # event IDs that must precede
    constraints: List[str] = field(default_factory=list)  # constraint IDs
    priority: int = 0  # Higher = more important
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def get_interval(self) -> TimeInterval:
        """Get time interval for event"""
        end_time = self.scheduled_time + timedelta(minutes=self.duration_minutes)
        return TimeInterval(self.scheduled_time, end_time, self.duration_minutes)

    def to_dict(self) -> Dict:
        """Serialize event"""
        return {
            "event_id": self.event_id,
            "name": self.name,
            "scheduled": self.scheduled_time.isoformat(),
            "duration": self.duration_minutes,
            "dependencies": len(self.dependencies),
            "priority": self.priority,
        }


@dataclass
class TemporalConstraint:
    """Temporal constraint on events"""
    constraint_id: str
    constraint_type: ConstraintType
    event_id: str
    reference_event: Optional[str] = None  # For relative constraints
    value: Any = None  # The constraint value (e.g., deadline time)
    is_satisfied: bool = False
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize constraint"""
        return {
            "constraint_id": self.constraint_id,
            "type": self.constraint_type.value,
            "event": self.event_id,
            "satisfied": self.is_satisfied,
        }


@dataclass
class Schedule:
    """Scheduled plan with events and constraints"""
    schedule_id: str
    events: List[TemporalEvent] = field(default_factory=list)
    constraints: List[TemporalConstraint] = field(default_factory=list)
    feasible: bool = True
    conflicts: List[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def get_critical_path(self) -> List[str]:
        """Get critical path (longest dependency chain)"""
        # Simple approximation: topologically sort and find longest path
        if not self.events:
            return []

        paths = {}
        for event in self.events:
            if not event.dependencies:
                paths[event.event_id] = [event.event_id]
            else:
                longest = max(
                    [paths.get(dep, []) for dep in event.dependencies],
                    default=[]
                )
                paths[event.event_id] = longest + [event.event_id]

        return max(paths.values(), default=[])

    def to_dict(self) -> Dict:
        """Serialize schedule"""
        return {
            "schedule_id": self.schedule_id,
            "events": len(self.events),
            "constraints": len(self.constraints),
            "feasible": self.feasible,
            "conflicts": len(self.conflicts),
        }


class CausalityTracker:
    """Track causal relationships between events"""

    def __init__(self):
        self.events: Dict[str, TemporalEvent] = {}
        self.relations: Dict[str, TemporalRelation] = {}

    def add_event(
        self,
        event_id: str,
        name: str,
        scheduled_time: datetime,
        duration_minutes: int,
    ) -> TemporalEvent:
        """Add temporal event"""
        event = TemporalEvent(
            event_id=event_id,
            name=name,
            scheduled_time=scheduled_time,
            duration_minutes=duration_minutes,
        )
        self.events[event_id] = event
        return event

    def establish_relation(
        self,
        event1_id: str,
        event2_id: str,
        relation: TemporalRelation,
    ) -> bool:
        """Establish temporal relationship"""
        if event1_id not in self.events or event2_id not in self.events:
            return False

        # Add to dependency if BEFORE relation
        if relation == TemporalRelation.BEFORE:
            self.events[event2_id].dependencies.append(event1_id)

        # Store relation
        key = f"{event1_id}_{event2_id}"
        self.relations[key] = relation

        return True

    def get_causal_chain(self, event_id: str) -> List[str]:
        """Get causal chain leading to event"""
        if event_id not in self.events:
            return []

        event = self.events[event_id]
        chain = list(event.dependencies)

        # Recursively add dependencies
        for dep in event.dependencies:
            chain.extend(self.get_causal_chain(dep))

        return list(set(chain))


class SchedulingEngine:
    """Schedule events respecting temporal constraints"""

    def __init__(self):
        self.schedules: Dict[str, Schedule] = {}
        self.causality = CausalityTracker()

    def create_schedule(self, schedule_id: str) -> Schedule:
        """Create new schedule"""
        schedule = Schedule(schedule_id=schedule_id)
        self.schedules[schedule_id] = schedule
        return schedule

    def add_event_to_schedule(
        self,
        schedule_id: str,
        event_id: str,
        name: str,
        scheduled_time: datetime,
        duration_minutes: int,
        dependencies: List[str] = None,
    ) -> Optional[TemporalEvent]:
        """Add event to schedule"""
        if schedule_id not in self.schedules:
            return None

        event = TemporalEvent(
            event_id=event_id,
            name=name,
            scheduled_time=scheduled_time,
            duration_minutes=duration_minutes,
            dependencies=dependencies or [],
        )

        schedule = self.schedules[schedule_id]
        schedule.events.append(event)

        return event

    def add_constraint(
        self,
        schedule_id: str,
        constraint_id: str,
        constraint_type: ConstraintType,
        event_id: str,
        value: Any = None,
    ) -> Optional[TemporalConstraint]:
        """Add temporal constraint"""
        if schedule_id not in self.schedules:
            return None

        constraint = TemporalConstraint(
            constraint_id=constraint_id,
            constraint_type=constraint_type,
            event_id=event_id,
            value=value,
        )

        schedule = self.schedules[schedule_id]
        schedule.constraints.append(constraint)

        return constraint

    def check_feasibility(self, schedule_id: str) -> Dict[str, Any]:
        """Check if schedule is feasible"""
        if schedule_id not in self.schedules:
            return {}

        schedule = self.schedules[schedule_id]
        conflicts = []

        # Check for overlapping events
        for i, event1 in enumerate(schedule.events):
            for event2 in schedule.events[i+1:]:
                if event1.get_interval().overlaps(event2.get_interval()):
                    conflicts.append(f"{event1.name} overlaps with {event2.name}")

        # Check dependencies are satisfied
        for event in schedule.events:
            for dep_id in event.dependencies:
                dep_event = next((e for e in schedule.events if e.event_id == dep_id), None)
                if dep_event and dep_event.get_interval().end_time > event.get_interval().start_time:
                    conflicts.append(f"{event.name} depends on {dep_event.name} but violates timing")

        # Check constraints
        for constraint in schedule.constraints:
            if constraint.constraint_type == ConstraintType.DEADLINE:
                event = next((e for e in schedule.events if e.event_id == constraint.event_id), None)
                if event and event.get_interval().end_time > constraint.value:
                    conflicts.append(f"{event.name} violates deadline {constraint.value}")

        schedule.feasible = len(conflicts) == 0
        schedule.conflicts = conflicts

        return {
            "schedule_id": schedule_id,
            "feasible": schedule.feasible,
            "conflicts": conflicts,
            "conflict_count": len(conflicts),
        }

    def optimize_schedule(
        self,
        schedule_id: str,
        optimization_goal: str = "minimize_duration",
    ) -> Optional[Dict[str, Any]]:
        """Optimize schedule based on goal"""
        if schedule_id not in self.schedules:
            return None

        schedule = self.schedules[schedule_id]

        if optimization_goal == "minimize_duration":
            # Move events earlier where possible
            for event in sorted(schedule.events, key=lambda e: e.priority, reverse=True):
                # Find earliest feasible start time
                earliest = event.scheduled_time
                for other in schedule.events:
                    if event.event_id in other.dependencies:
                        earliest = max(earliest, other.get_interval().end_time)

                event.scheduled_time = earliest

        elif optimization_goal == "balance_load":
            # Distribute events more evenly
            event_count = len(schedule.events)
            day_start = min((e.scheduled_time for e in schedule.events), default=datetime.now())

            for i, event in enumerate(sorted(schedule.events, key=lambda e: e.priority)):
                hours_offset = (i * 24) / event_count
                event.scheduled_time = day_start + timedelta(hours=hours_offset)

        return self.check_feasibility(schedule_id)


class TemporalManager:
    """Manage temporal reasoning across systems"""

    def __init__(self):
        self.engines: Dict[str, SchedulingEngine] = {}

    def create_engine(self, engine_id: str) -> SchedulingEngine:
        """Create scheduling engine"""
        engine = SchedulingEngine()
        self.engines[engine_id] = engine
        return engine

    def get_engine(self, engine_id: str) -> Optional[SchedulingEngine]:
        """Get engine"""
        return self.engines.get(engine_id)


# Global manager
temporal_manager = TemporalManager()


# MCP Tools

def create_scheduling_engine(engine_id: str) -> dict:
    """Create temporal reasoning engine"""
    engine = temporal_manager.create_engine(engine_id)
    return {"engine_id": engine_id, "created": True}


def create_schedule(engine_id: str, schedule_id: str) -> dict:
    """Create schedule"""
    engine = temporal_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    schedule = engine.create_schedule(schedule_id)
    return schedule.to_dict()


def add_event(
    engine_id: str,
    schedule_id: str,
    event_id: str,
    name: str,
    scheduled_time: str,
    duration_minutes: int,
    dependencies: list = None,
) -> dict:
    """Add event to schedule"""
    engine = temporal_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    try:
        sched_time = datetime.fromisoformat(scheduled_time)
    except:
        return {"error": "Invalid datetime format"}

    event = engine.add_event_to_schedule(
        schedule_id,
        event_id,
        name,
        sched_time,
        duration_minutes,
        dependencies,
    )

    return event.to_dict() if event else {"error": "Schedule not found"}


def add_temporal_constraint(
    engine_id: str,
    schedule_id: str,
    constraint_id: str,
    constraint_type: str,
    event_id: str,
    value: str = None,
) -> dict:
    """Add temporal constraint"""
    engine = temporal_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    constraint = engine.add_constraint(
        schedule_id,
        constraint_id,
        ConstraintType(constraint_type),
        event_id,
        value,
    )

    return constraint.to_dict() if constraint else {"error": "Schedule not found"}


def check_schedule_feasibility(engine_id: str, schedule_id: str) -> dict:
    """Check schedule feasibility"""
    engine = temporal_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    return engine.check_feasibility(schedule_id)


def optimize_schedule(
    engine_id: str,
    schedule_id: str,
    goal: str = "minimize_duration",
) -> dict:
    """Optimize schedule"""
    engine = temporal_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    return engine.optimize_schedule(schedule_id, goal) or {"error": "Schedule not found"}


if __name__ == "__main__":
    # Test temporal reasoning
    engine = SchedulingEngine()
    schedule = engine.create_schedule("sched_1")

    # Add events
    now = datetime.now()
    engine.add_event_to_schedule(
        "sched_1",
        "evt_1",
        "Planning",
        now,
        30,
    )
    engine.add_event_to_schedule(
        "sched_1",
        "evt_2",
        "Implementation",
        now + timedelta(hours=1),
        120,
        dependencies=["evt_1"],
    )
    engine.add_event_to_schedule(
        "sched_1",
        "evt_3",
        "Testing",
        now + timedelta(hours=3),
        60,
        dependencies=["evt_2"],
    )

    # Add constraint
    engine.add_constraint(
        "sched_1",
        "con_1",
        ConstraintType.DEADLINE,
        "evt_3",
        now + timedelta(hours=4),
    )

    # Check feasibility
    feasibility = engine.check_feasibility("sched_1")
    print(f"Feasibility: {json.dumps(feasibility, indent=2)}")

    # Get critical path
    critical = schedule.get_critical_path()
    print(f"Critical path: {critical}")

    # Optimize
    optimized = engine.optimize_schedule("sched_1")
    print(f"Optimized: {json.dumps(optimized, indent=2)}")
