"""Agent routing and handoff system with context preservation"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass

ROUTING_DIR = Path.home() / ".memory-mcp" / "routing"
ROUTING_DIR.mkdir(exist_ok=True, parents=True)


class HandoffTrigger(Enum):
    """Reasons for agent handoff"""
    CONFIDENCE_LOW = "confidence_low"
    CRITICAL_ACTION = "critical_action"
    ERROR_STATE = "error_state"
    CAPABILITY_MISMATCH = "capability_mismatch"
    COMPLETION = "completion"
    ESCALATION = "escalation"
    USER_REQUEST = "user_request"


@dataclass
class AgentCapability:
    """Define what an agent can do"""
    agent_id: str
    agent_name: str
    capabilities: List[str]  # e.g., ["search", "analyze", "code"]
    expertise_level: float = 1.0  # 0.0-1.0
    max_confidence_threshold: float = 0.95
    is_available: bool = True
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def matches_capability(self, required_capability: str) -> bool:
        """Check if agent has required capability"""
        return required_capability in self.capabilities


class ContextPackage:
    """Package containing context for handoff"""

    def __init__(self, source_agent: str, target_agent: str):
        self.source_agent = source_agent
        self.target_agent = target_agent
        self.timestamp = datetime.now().isoformat()
        self.message_history: List[Dict] = []
        self.state: Dict = {}  # Shared state
        self.decisions: List[str] = []  # Prior decisions
        self.artifacts: Dict = {}  # Files, results
        self.error_logs: List[str] = []
        self.summary: str = ""
        self.trigger: Optional[HandoffTrigger] = None

    def add_message(self, role: str, content: str):
        """Add message to history"""
        self.message_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })

    def add_error(self, error_msg: str):
        """Log error"""
        self.error_logs.append({
            "error": error_msg,
            "timestamp": datetime.now().isoformat(),
        })

    def set_summary(self, summary: str):
        """Set handoff summary"""
        self.summary = summary

    def to_dict(self) -> Dict:
        """Serialize context package"""
        return {
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "timestamp": self.timestamp,
            "message_history": self.message_history[-20:],  # Last 20 messages
            "state": self.state,
            "decisions": self.decisions,
            "artifacts": self.artifacts,
            "error_logs": self.error_logs,
            "summary": self.summary,
            "trigger": self.trigger.value if self.trigger else None,
        }


class AgentRouter:
    """Route queries to most appropriate agent"""

    def __init__(self):
        self.agents: Dict[str, AgentCapability] = {}
        self.routing_rules: List[Dict] = []
        self.history: List[Dict] = []

    def register_agent(self, agent: AgentCapability):
        """Register an agent"""
        self.agents[agent.agent_id] = agent

    def add_routing_rule(
        self,
        name: str,
        condition: Callable[[Dict], bool],
        target_agent: str,
        priority: int = 0,
    ):
        """Add routing rule"""
        self.routing_rules.append({
            "name": name,
            "condition": condition,
            "target_agent": target_agent,
            "priority": priority,
        })

    def find_best_agent(
        self,
        query: str,
        required_capability: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> Optional[AgentCapability]:
        """
        Find best agent for query using decision tree routing.
        1. Check routing rules
        2. Match by capability
        3. Select by expertise + availability
        """
        context = context or {}

        # Step 1: Check routing rules (priority order)
        for rule in sorted(self.routing_rules, key=lambda r: r["priority"], reverse=True):
            try:
                if rule["condition"]({"query": query, "context": context}):
                    agent = self.agents.get(rule["target_agent"])
                    if agent and agent.is_available:
                        return agent
            except Exception:
                continue

        # Step 2: Match by capability
        if required_capability:
            capable_agents = [
                a for a in self.agents.values()
                if a.matches_capability(required_capability) and a.is_available
            ]
            if capable_agents:
                # Return agent with highest expertise level
                return max(capable_agents, key=lambda a: a.expertise_level)

        # Step 3: Return most available expert
        available = [a for a in self.agents.values() if a.is_available]
        if available:
            return max(available, key=lambda a: a.expertise_level)

        return None

    def route_query(
        self,
        query: str,
        required_capability: Optional[str] = None,
    ) -> Optional[AgentCapability]:
        """Route a query to appropriate agent"""
        agent = self.find_best_agent(query, required_capability)

        if agent:
            self.history.append({
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "selected_agent": agent.agent_id,
                "capability": required_capability,
            })

        return agent


class HandoffManager:
    """Manage agent handoffs with context preservation"""

    def __init__(self, router: AgentRouter):
        self.router = router
        self.active_handoffs: Dict[str, ContextPackage] = {}
        self.handoff_history: List[Dict] = []

    def initiate_handoff(
        self,
        source_agent: str,
        target_agent: Optional[str] = None,
        trigger: HandoffTrigger = HandoffTrigger.COMPLETION,
        query: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> Optional[ContextPackage]:
        """
        Initiate handoff from source to target agent.
        If target_agent not specified, router will select.
        """
        # Determine target agent
        if not target_agent:
            agent = self.router.route_query(query or "", context=context or {})
            target_agent = agent.agent_id if agent else None

        if not target_agent:
            return None

        # Create context package
        package = ContextPackage(source_agent, target_agent)
        package.trigger = trigger

        handoff_id = f"{source_agent}_to_{target_agent}_{len(self.active_handoffs)}"
        self.active_handoffs[handoff_id] = package

        # Log handoff
        self.handoff_history.append({
            "handoff_id": handoff_id,
            "source_agent": source_agent,
            "target_agent": target_agent,
            "trigger": trigger.value,
            "timestamp": datetime.now().isoformat(),
            "status": "initiated",
        })

        return package

    def complete_handoff(self, handoff_id: str, output: Optional[str] = None):
        """Complete handoff and save context"""
        if handoff_id not in self.active_handoffs:
            return False

        package = self.active_handoffs[handoff_id]

        if output:
            package.set_summary(output)

        # Save context package
        filepath = ROUTING_DIR / f"{handoff_id}.json"
        with open(filepath, "w") as f:
            json.dump(package.to_dict(), f, indent=2)

        # Update history
        for entry in self.handoff_history:
            if entry["handoff_id"] == handoff_id:
                entry["status"] = "completed"

        # Remove from active
        del self.active_handoffs[handoff_id]

        return True

    def get_context_for_agent(self, handoff_id: str) -> Optional[Dict]:
        """Get context package for target agent"""
        if handoff_id not in self.active_handoffs:
            return None

        package = self.active_handoffs[handoff_id]
        return package.to_dict()

    def list_handoffs(self, agent_id: Optional[str] = None) -> List[Dict]:
        """List handoff history"""
        if agent_id:
            return [
                h for h in self.handoff_history
                if h["source_agent"] == agent_id or h["target_agent"] == agent_id
            ]
        return self.handoff_history


class ConfidenceMonitor:
    """Monitor agent confidence and trigger handoffs when needed"""

    def __init__(self, handoff_manager: HandoffManager):
        self.handoff_manager = handoff_manager
        self.confidence_scores: Dict[str, float] = {}

    def update_confidence(self, agent_id: str, score: float):
        """Update agent confidence (0.0-1.0)"""
        self.confidence_scores[agent_id] = max(0.0, min(1.0, score))

    def should_handoff(self, agent_id: str) -> bool:
        """Check if agent confidence is too low"""
        score = self.confidence_scores.get(agent_id, 1.0)
        agent = self.handoff_manager.router.agents.get(agent_id)

        if agent:
            return score < (1.0 - agent.max_confidence_threshold)

        return score < 0.5

    def get_confidence_report(self) -> Dict[str, float]:
        """Get all confidence scores"""
        return self.confidence_scores.copy()


class DecisionTree:
    """Decision tree for rule-based agent routing"""

    def __init__(self):
        self.root = None

    def add_rule(
        self,
        path: List[str],
        condition: Callable[[Dict], bool],
        action: Callable,
    ):
        """
        Add decision rule.
        path: ["intent", "search"] means condition evaluated at those nodes
        """
        pass

    def evaluate(self, context: Dict) -> Any:
        """Traverse tree and return action result"""
        pass


# Global instances
class RoutingSystem:
    """Complete routing system"""

    def __init__(self):
        self.router = AgentRouter()
        self.handoff_manager = HandoffManager(self.router)
        self.confidence_monitor = ConfidenceMonitor(self.handoff_manager)

    def register_agent(
        self,
        agent_id: str,
        agent_name: str,
        capabilities: List[str],
        expertise_level: float = 1.0,
    ) -> AgentCapability:
        """Register agent in system"""
        agent = AgentCapability(
            agent_id=agent_id,
            agent_name=agent_name,
            capabilities=capabilities,
            expertise_level=expertise_level,
        )
        self.router.register_agent(agent)
        return agent

    def route_and_maybe_handoff(
        self,
        current_agent: str,
        query: str,
        required_capability: Optional[str] = None,
        confidence: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Route query and check if handoff needed.
        Returns: {"agent": AgentCapability, "handoff": bool, "package": ContextPackage}
        """
        self.confidence_monitor.update_confidence(current_agent, confidence)

        # Check if handoff needed
        should_handoff = self.confidence_monitor.should_handoff(current_agent)

        # Find target agent
        target_agent = self.router.route_query(query, required_capability)

        if should_handoff and target_agent:
            package = self.handoff_manager.initiate_handoff(
                current_agent,
                target_agent.agent_id,
                HandoffTrigger.CONFIDENCE_LOW,
                query,
            )
            return {
                "agent": target_agent,
                "handoff": True,
                "package": package,
            }

        return {
            "agent": target_agent,
            "handoff": False,
            "package": None,
        }


system = RoutingSystem()


# MCP Tools (add to memory_server.py)

def register_agent(
    agent_id: str,
    agent_name: str,
    capabilities: list,
    expertise_level: float = 1.0,
) -> dict:
    """Register agent in routing system"""
    agent = system.register_agent(agent_id, agent_name, capabilities, expertise_level)
    return agent.__dict__


def route_query(
    query: str,
    required_capability: str = None,
) -> dict:
    """Route query to best agent"""
    agent = system.router.route_query(query, required_capability)
    return agent.__dict__ if agent else {"error": "No agent found"}


def initiate_handoff(
    source_agent: str,
    target_agent: str = None,
    trigger: str = "completion",
    query: str = None,
) -> dict:
    """Initiate agent handoff with context"""
    package = system.handoff_manager.initiate_handoff(
        source_agent,
        target_agent,
        HandoffTrigger(trigger),
        query,
    )
    return package.to_dict() if package else {"error": "Handoff failed"}


def complete_handoff(handoff_id: str, output: str = None) -> bool:
    """Complete handoff"""
    return system.handoff_manager.complete_handoff(handoff_id, output)


def update_confidence(agent_id: str, score: float) -> dict:
    """Update agent confidence score"""
    system.confidence_monitor.update_confidence(agent_id, score)
    return {"agent_id": agent_id, "confidence": score}


def get_handoff_history(agent_id: str = None) -> list:
    """Get handoff history"""
    return system.handoff_manager.list_handoffs(agent_id)


if __name__ == "__main__":
    # Test routing system
    system.register_agent("analyzer", "Data Analyzer", ["analyze", "search"], 0.9)
    system.register_agent("coder", "Code Expert", ["code", "debug"], 0.95)
    system.register_agent("writer", "Content Writer", ["write", "edit"], 0.85)

    # Add routing rule
    system.router.add_routing_rule(
        "code_queries",
        lambda ctx: "code" in ctx["query"].lower() or "debug" in ctx["query"].lower(),
        "coder",
        priority=10,
    )

    # Test routing
    result = system.route_and_maybe_handoff("analyzer", "write a function", "code", 0.3)
    print("Routing result:", result)

    # Test handoff
    package = system.handoff_manager.initiate_handoff(
        "analyzer",
        "coder",
        HandoffTrigger.CAPABILITY_MISMATCH,
        "write a function",
    )
    print("Handoff package:", package.to_dict() if package else None)
