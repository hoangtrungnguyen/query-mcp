"""Multi-agent coordination and swarm behavior for collective problem-solving"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

SWARM_DIR = Path.home() / ".memory-mcp" / "swarms"
SWARM_DIR.mkdir(exist_ok=True, parents=True)


class CoordinationStrategy(Enum):
    """Agent coordination approaches"""
    SEQUENTIAL = "sequential"  # One after another
    PARALLEL = "parallel"  # Simultaneous
    HIERARCHICAL = "hierarchical"  # Leader-follower
    CONSENSUS = "consensus"  # Agree on answer
    VOTING = "voting"  # Majority decision
    AUCTION = "auction"  # Competitive bidding


class AgentRole(Enum):
    """Role in swarm"""
    LEADER = "leader"  # Coordinates
    SPECIALIST = "specialist"  # Domain expert
    GENERALIST = "generalist"  # Broad capability
    CRITIC = "critic"  # Evaluates
    SYNTHESIZER = "synthesizer"  # Combines


@dataclass
class SwarmMember:
    """Agent in swarm"""
    agent_id: str
    role: AgentRole
    expertise: List[str]
    capability_score: float = 0.8
    participation_history: List[str] = field(default_factory=list)
    total_contributions: int = 0

    def to_dict(self) -> Dict:
        """Serialize member"""
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "expertise": self.expertise,
            "capability_score": self.capability_score,
            "contributions": self.total_contributions,
        }


@dataclass
class SwarmTask:
    """Task for swarm to solve"""
    task_id: str
    problem: str
    strategy: CoordinationStrategy
    required_expertise: List[str]
    deadline: Optional[str] = None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize task"""
        return {
            "task_id": self.task_id,
            "problem": self.problem,
            "strategy": self.strategy.value,
            "required_expertise": self.required_expertise,
            "created_at": self.created_at,
        }


@dataclass
class AgentResponse:
    """Response from swarm member"""
    response_id: str
    agent_id: str
    task_id: str
    solution: str
    confidence: float
    reasoning: str
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize response"""
        return {
            "response_id": self.response_id,
            "agent_id": self.agent_id,
            "solution": self.solution,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "created_at": self.created_at,
        }


class Swarm:
    """Collection of coordinated agents"""

    def __init__(self, swarm_id: str, name: str):
        self.swarm_id = swarm_id
        self.name = name
        self.members: Dict[str, SwarmMember] = {}
        self.tasks: Dict[str, SwarmTask] = {}
        self.responses: Dict[str, List[AgentResponse]] = {}
        self.created_at = datetime.now().isoformat()

    def add_member(
        self,
        agent_id: str,
        role: AgentRole,
        expertise: List[str],
    ) -> SwarmMember:
        """Add agent to swarm"""
        member = SwarmMember(
            agent_id=agent_id,
            role=role,
            expertise=expertise,
        )
        self.members[agent_id] = member
        return member

    def create_task(
        self,
        task_id: str,
        problem: str,
        strategy: CoordinationStrategy,
        required_expertise: List[str],
    ) -> SwarmTask:
        """Create task for swarm"""
        task = SwarmTask(
            task_id=task_id,
            problem=problem,
            strategy=strategy,
            required_expertise=required_expertise,
        )
        self.tasks[task_id] = task
        return task

    def find_suitable_members(
        self,
        required_expertise: List[str],
    ) -> List[SwarmMember]:
        """Find agents matching expertise"""
        suitable = []

        for member in self.members.values():
            matches = sum(
                1 for req in required_expertise
                if req in member.expertise
            )
            if matches > 0:
                suitable.append(member)

        return sorted(suitable, key=lambda m: m.capability_score, reverse=True)

    def add_response(
        self,
        task_id: str,
        agent_id: str,
        solution: str,
        confidence: float,
        reasoning: str,
    ) -> AgentResponse:
        """Add agent response"""
        response = AgentResponse(
            response_id=f"resp_{len(self.responses.get(task_id, []))}",
            agent_id=agent_id,
            task_id=task_id,
            solution=solution,
            confidence=confidence,
            reasoning=reasoning,
        )

        if task_id not in self.responses:
            self.responses[task_id] = []

        self.responses[task_id].append(response)

        # Update member stats
        if agent_id in self.members:
            self.members[agent_id].total_contributions += 1
            self.members[agent_id].participation_history.append(task_id)

        return response

    def execute_consensus(self, task_id: str) -> Optional[Dict]:
        """Consensus voting on task"""
        if task_id not in self.responses:
            return None

        responses = self.responses[task_id]

        if not responses:
            return None

        # Group by solution
        solution_groups = {}
        for resp in responses:
            if resp.solution not in solution_groups:
                solution_groups[resp.solution] = []
            solution_groups[resp.solution].append(resp)

        # Find most agreed solution
        best_solution = max(
            solution_groups.items(),
            key=lambda x: (len(x[1]), sum(r.confidence for r in x[1])),
        )

        consensus_solution = best_solution[0]
        agreement_ratio = len(best_solution[1]) / len(responses)
        avg_confidence = sum(r.confidence for r in best_solution[1]) / len(best_solution[1])

        return {
            "task_id": task_id,
            "consensus_solution": consensus_solution,
            "agreement_ratio": agreement_ratio,
            "agents_agreeing": len(best_solution[1]),
            "avg_confidence": avg_confidence,
            "reasoning": "; ".join(r.reasoning for r in best_solution[1][:3]),
        }

    def execute_hierarchical(self, task_id: str) -> Optional[Dict]:
        """Hierarchical decision (leader decides)"""
        if task_id not in self.responses:
            return None

        responses = self.responses[task_id]

        # Find leader
        leaders = [m for m in self.members.values() if m.role == AgentRole.LEADER]

        if not leaders:
            return None

        leader = leaders[0]
        leader_response = next(
            (r for r in responses if r.agent_id == leader.agent_id),
            None,
        )

        if leader_response:
            return {
                "task_id": task_id,
                "leader": leader.agent_id,
                "decision": leader_response.solution,
                "reasoning": leader_response.reasoning,
                "confidence": leader_response.confidence,
            }

        return None

    def get_swarm_summary(self) -> Dict[str, Any]:
        """Get swarm statistics"""
        return {
            "swarm_id": self.swarm_id,
            "name": self.name,
            "member_count": len(self.members),
            "roles": {
                role.value: sum(1 for m in self.members.values() if m.role == role)
                for role in AgentRole
            },
            "task_count": len(self.tasks),
            "total_responses": sum(len(r) for r in self.responses.values()),
            "created_at": self.created_at,
        }


class SwarmManager:
    """Manage multiple swarms"""

    def __init__(self):
        self.swarms: Dict[str, Swarm] = {}

    def create_swarm(self, swarm_id: str, name: str) -> Swarm:
        """Create swarm"""
        swarm = Swarm(swarm_id, name)
        self.swarms[swarm_id] = swarm
        return swarm

    def get_swarm(self, swarm_id: str) -> Optional[Swarm]:
        """Get swarm"""
        return self.swarms.get(swarm_id)

    def execute_task(
        self,
        swarm_id: str,
        task_id: str,
        strategy: CoordinationStrategy,
        agent_solutions: Dict[str, Tuple[str, float, str]],  # agent_id -> (solution, confidence, reasoning)
    ) -> Optional[Dict]:
        """Execute task with swarm"""
        swarm = self.get_swarm(swarm_id)

        if not swarm or task_id not in swarm.tasks:
            return None

        # Add responses
        for agent_id, (solution, confidence, reasoning) in agent_solutions.items():
            swarm.add_response(task_id, agent_id, solution, confidence, reasoning)

        # Execute coordination
        if strategy == CoordinationStrategy.CONSENSUS:
            return swarm.execute_consensus(task_id)
        elif strategy == CoordinationStrategy.HIERARCHICAL:
            return swarm.execute_hierarchical(task_id)

        return None

    def get_all_swarms_summary(self) -> List[Dict]:
        """Get all swarms"""
        return [s.get_swarm_summary() for s in self.swarms.values()]


# Global manager
swarm_manager = SwarmManager()


# MCP Tools (add to memory_server.py)

def create_swarm(swarm_id: str, name: str) -> dict:
    """Create swarm"""
    swarm = swarm_manager.create_swarm(swarm_id, name)
    return {"swarm_id": swarm.swarm_id, "name": swarm.name, "created": True}


def add_swarm_member(
    swarm_id: str,
    agent_id: str,
    role: str,
    expertise: list,
) -> dict:
    """Add agent to swarm"""
    swarm = swarm_manager.get_swarm(swarm_id)
    if not swarm:
        return {"error": "Swarm not found"}

    member = swarm.add_member(agent_id, AgentRole(role), expertise)
    return member.to_dict()


def create_swarm_task(
    swarm_id: str,
    task_id: str,
    problem: str,
    strategy: str,
    required_expertise: list,
) -> dict:
    """Create task"""
    swarm = swarm_manager.get_swarm(swarm_id)
    if not swarm:
        return {"error": "Swarm not found"}

    task = swarm.create_task(
        task_id,
        problem,
        CoordinationStrategy(strategy),
        required_expertise,
    )
    return task.to_dict()


def submit_swarm_response(
    swarm_id: str,
    task_id: str,
    agent_id: str,
    solution: str,
    confidence: float,
    reasoning: str,
) -> dict:
    """Submit response"""
    swarm = swarm_manager.get_swarm(swarm_id)
    if not swarm:
        return {"error": "Swarm not found"}

    response = swarm.add_response(task_id, agent_id, solution, confidence, reasoning)
    return response.to_dict()


def execute_swarm_task(
    swarm_id: str,
    task_id: str,
    strategy: str,
) -> dict:
    """Execute task"""
    swarm = swarm_manager.get_swarm(swarm_id)
    if not swarm or task_id not in swarm.tasks:
        return {"error": "Task not found"}

    task = swarm.tasks[task_id]
    result = swarm_manager.execute_task(
        swarm_id,
        task_id,
        CoordinationStrategy(strategy),
        {},
    )
    return result or {"executed": False}


def get_swarm_summary(swarm_id: str) -> dict:
    """Get swarm info"""
    swarm = swarm_manager.get_swarm(swarm_id)
    return swarm.get_swarm_summary() if swarm else {"error": "Swarm not found"}


if __name__ == "__main__":
    # Test swarms
    manager = SwarmManager()

    # Create swarm
    swarm = manager.create_swarm("sw_1", "Problem Solvers")
    print(f"Swarm: {swarm.swarm_id}")

    # Add members
    swarm.add_member("agent_1", AgentRole.LEADER, ["planning", "coordination"])
    swarm.add_member("agent_2", AgentRole.SPECIALIST, ["analysis"])
    swarm.add_member("agent_3", AgentRole.SPECIALIST, ["implementation"])

    # Create task
    task = swarm.create_task(
        "task_1",
        "How to optimize database?",
        CoordinationStrategy.CONSENSUS,
        ["analysis", "implementation"],
    )
    print(f"Task: {task.task_id}")

    # Get suitable members
    suitable = swarm.find_suitable_members(["analysis"])
    print(f"Suitable members: {len(suitable)}")

    # Summary
    summary = swarm.get_swarm_summary()
    print(f"Summary: {json.dumps(summary, indent=2)}")
