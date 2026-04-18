"""Conversation state persistence and recovery for resuming agent execution"""

import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

STATE_DIR = Path.home() / ".memory-mcp" / "state-recovery"
STATE_DIR.mkdir(exist_ok=True, parents=True)


class StateScope(Enum):
    """Scope of state to preserve"""
    TURN = "turn"  # Single conversation turn
    CONVERSATION = "conversation"  # Entire conversation
    SESSION = "session"  # Multi-conversation session
    AGENT = "agent"  # Agent-wide state


class SerializationFormat(Enum):
    """Serialization strategy"""
    JSON = "json"  # JSON serialization
    PICKLE = "pickle"  # Python pickle
    JSONL = "jsonl"  # Line-delimited JSON


@dataclass
class ExecutionState:
    """Captured execution state at a point in time"""
    state_id: str
    agent_id: str
    scope: StateScope
    turn: int
    variables: Dict[str, Any]
    call_stack: List[Dict]  # Function call history
    tool_results: Dict[str, Any]  # Tool execution results
    context_window: Dict[str, str]  # Conversation context
    timestamp: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict:
        """Serialize to dict"""
        return {
            "state_id": self.state_id,
            "agent_id": self.agent_id,
            "scope": self.scope.value,
            "turn": self.turn,
            "variables": self.variables,
            "call_stack": self.call_stack,
            "tool_results": self.tool_results,
            "context_window": self.context_window,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: Dict) -> "ExecutionState":
        """Deserialize from dict"""
        return ExecutionState(
            state_id=data["state_id"],
            agent_id=data["agent_id"],
            scope=StateScope(data["scope"]),
            turn=data["turn"],
            variables=data["variables"],
            call_stack=data["call_stack"],
            tool_results=data["tool_results"],
            context_window=data["context_window"],
            timestamp=data["timestamp"],
            metadata=data["metadata"],
        )


@dataclass
class StateCheckpoint:
    """Versioned state snapshot"""
    checkpoint_id: str
    state: ExecutionState
    parent_checkpoint_id: Optional[str]  # For branching
    created_at: str
    restored_count: int = 0
    branch_count: int = 0

    def to_dict(self) -> Dict:
        """Serialize checkpoint"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "state": self.state.to_dict(),
            "parent_checkpoint_id": self.parent_checkpoint_id,
            "created_at": self.created_at,
            "restored_count": self.restored_count,
            "branch_count": self.branch_count,
        }


class StateSerializer:
    """Handle state serialization/deserialization"""

    @staticmethod
    def serialize_json(state: ExecutionState) -> str:
        """Serialize to JSON"""
        return json.dumps(state.to_dict(), indent=2, default=str)

    @staticmethod
    def deserialize_json(data: str) -> ExecutionState:
        """Deserialize from JSON"""
        obj = json.loads(data)
        return ExecutionState.from_dict(obj)

    @staticmethod
    def serialize_pickle(state: ExecutionState) -> bytes:
        """Serialize to pickle"""
        return pickle.dumps(state)

    @staticmethod
    def deserialize_pickle(data: bytes) -> ExecutionState:
        """Deserialize from pickle"""
        return pickle.loads(data)

    @staticmethod
    def serialize_jsonl(states: List[ExecutionState]) -> str:
        """Serialize multiple states to JSONL"""
        lines = [json.dumps(s.to_dict(), default=str) for s in states]
        return "\n".join(lines)

    @staticmethod
    def deserialize_jsonl(data: str) -> List[ExecutionState]:
        """Deserialize JSONL to states"""
        states = []
        for line in data.strip().split("\n"):
            if line:
                obj = json.loads(line)
                states.append(ExecutionState.from_dict(obj))
        return states


class StateStore:
    """Persistent storage for execution state"""

    def __init__(self, format: SerializationFormat = SerializationFormat.JSON):
        self.format = format
        self.serializer = StateSerializer()
        self.checkpoints: Dict[str, StateCheckpoint] = {}
        self.checkpoint_index: Dict[str, List[str]] = {}  # agent_id -> checkpoint_ids

    def save_state(
        self,
        state: ExecutionState,
        checkpoint_id: str,
        parent_checkpoint_id: Optional[str] = None,
    ) -> StateCheckpoint:
        """Save state with checkpoint"""
        checkpoint = StateCheckpoint(
            checkpoint_id=checkpoint_id,
            state=state,
            parent_checkpoint_id=parent_checkpoint_id,
            created_at=datetime.now().isoformat(),
        )

        self.checkpoints[checkpoint_id] = checkpoint

        # Index by agent
        if state.agent_id not in self.checkpoint_index:
            self.checkpoint_index[state.agent_id] = []
        self.checkpoint_index[state.agent_id].append(checkpoint_id)

        # Write to file
        self._write_checkpoint(checkpoint)

        return checkpoint

    def load_state(self, checkpoint_id: str) -> Optional[ExecutionState]:
        """Load state from checkpoint"""
        if checkpoint_id not in self.checkpoints:
            # Try loading from disk
            checkpoint = self._read_checkpoint(checkpoint_id)
            if not checkpoint:
                return None
            self.checkpoints[checkpoint_id] = checkpoint
        else:
            checkpoint = self.checkpoints[checkpoint_id]

        # Track restoration
        checkpoint.restored_count += 1
        return checkpoint.state

    def create_branch(
        self,
        parent_checkpoint_id: str,
        new_state: ExecutionState,
        new_checkpoint_id: str,
    ) -> Optional[StateCheckpoint]:
        """Create branched state from parent"""
        if parent_checkpoint_id not in self.checkpoints:
            return None

        parent = self.checkpoints[parent_checkpoint_id]
        parent.branch_count += 1

        return self.save_state(new_state, new_checkpoint_id, parent_checkpoint_id)

    def get_checkpoint_history(self, agent_id: str) -> List[StateCheckpoint]:
        """Get all checkpoints for agent"""
        checkpoint_ids = self.checkpoint_index.get(agent_id, [])
        return [self.checkpoints[cid] for cid in checkpoint_ids if cid in self.checkpoints]

    def get_checkpoint_lineage(self, checkpoint_id: str) -> List[StateCheckpoint]:
        """Get chain of checkpoints leading to this one"""
        lineage = []
        current_id = checkpoint_id

        while current_id:
            if current_id not in self.checkpoints:
                break
            checkpoint = self.checkpoints[current_id]
            lineage.insert(0, checkpoint)
            current_id = checkpoint.parent_checkpoint_id

        return lineage

    def _write_checkpoint(self, checkpoint: StateCheckpoint):
        """Write checkpoint to disk"""
        agent_id = checkpoint.state.agent_id
        agent_dir = STATE_DIR / agent_id
        agent_dir.mkdir(exist_ok=True, parents=True)

        filepath = agent_dir / f"{checkpoint.checkpoint_id}.json"

        with open(filepath, "w") as f:
            json.dump(checkpoint.to_dict(), f, indent=2, default=str)

    def _read_checkpoint(self, checkpoint_id: str) -> Optional[StateCheckpoint]:
        """Read checkpoint from disk"""
        for agent_dir in STATE_DIR.iterdir():
            if not agent_dir.is_dir():
                continue
            filepath = agent_dir / f"{checkpoint_id}.json"
            if filepath.exists():
                with open(filepath, "r") as f:
                    data = json.load(f)
                    state = ExecutionState.from_dict(data["state"])
                    return StateCheckpoint(
                        checkpoint_id=data["checkpoint_id"],
                        state=state,
                        parent_checkpoint_id=data["parent_checkpoint_id"],
                        created_at=data["created_at"],
                        restored_count=data["restored_count"],
                        branch_count=data["branch_count"],
                    )
        return None


class StateRecoveryManager:
    """High-level state recovery operations"""

    def __init__(self):
        self.store = StateStore()
        self.recovery_log: List[Dict] = []

    def capture_state(
        self,
        state_id: str,
        agent_id: str,
        scope: StateScope,
        turn: int,
        variables: Dict[str, Any],
        call_stack: List[Dict],
        tool_results: Dict[str, Any],
        context_window: Dict[str, str],
        metadata: Optional[Dict] = None,
    ) -> StateCheckpoint:
        """Capture execution state"""
        state = ExecutionState(
            state_id=state_id,
            agent_id=agent_id,
            scope=scope,
            turn=turn,
            variables=variables,
            call_stack=call_stack,
            tool_results=tool_results,
            context_window=context_window,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {},
        )

        checkpoint = self.store.save_state(
            state,
            f"ckpt_{agent_id}_{turn}_{state_id}",
        )

        self.recovery_log.append({
            "action": "capture",
            "checkpoint_id": checkpoint.checkpoint_id,
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
        })

        return checkpoint

    def resume_from_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[ExecutionState]:
        """Resume execution from checkpoint"""
        state = self.store.load_state(checkpoint_id)

        if state:
            self.recovery_log.append({
                "action": "resume",
                "checkpoint_id": checkpoint_id,
                "agent_id": state.agent_id,
                "timestamp": datetime.now().isoformat(),
            })

        return state

    def create_alternative_path(
        self,
        parent_checkpoint_id: str,
        new_state: ExecutionState,
    ) -> Optional[StateCheckpoint]:
        """Create branched execution path"""
        checkpoint = self.store.create_branch(
            parent_checkpoint_id,
            new_state,
            f"branch_{new_state.state_id}",
        )

        if checkpoint:
            self.recovery_log.append({
                "action": "branch",
                "parent_checkpoint_id": parent_checkpoint_id,
                "new_checkpoint_id": checkpoint.checkpoint_id,
                "agent_id": new_state.agent_id,
                "timestamp": datetime.now().isoformat(),
            })

        return checkpoint

    def get_recovery_summary(self, agent_id: str) -> Dict[str, Any]:
        """Get recovery statistics"""
        checkpoints = self.store.get_checkpoint_history(agent_id)

        return {
            "agent_id": agent_id,
            "checkpoint_count": len(checkpoints),
            "latest_checkpoint": checkpoints[-1].checkpoint_id if checkpoints else None,
            "total_restorations": sum(cp.restored_count for cp in checkpoints),
            "branch_count": sum(cp.branch_count for cp in checkpoints),
            "checkpoints": [cp.to_dict() for cp in checkpoints[-10:]],  # Last 10
        }

    def cleanup_old_states(self, agent_id: str, keep_recent: int = 20):
        """Remove old checkpoints, keeping recent ones"""
        checkpoints = self.store.get_checkpoint_history(agent_id)

        if len(checkpoints) > keep_recent:
            to_remove = checkpoints[: len(checkpoints) - keep_recent]
            for cp in to_remove:
                if cp.checkpoint_id in self.store.checkpoints:
                    del self.store.checkpoints[cp.checkpoint_id]


# Global manager
recovery_manager = StateRecoveryManager()


# MCP Tools (add to memory_server.py)

def capture_execution_state(
    state_id: str,
    agent_id: str,
    scope: str,
    turn: int,
    variables: dict,
    call_stack: list,
    tool_results: dict,
    context_window: dict,
) -> dict:
    """Capture current execution state"""
    checkpoint = recovery_manager.capture_state(
        state_id,
        agent_id,
        StateScope(scope),
        turn,
        variables,
        call_stack,
        tool_results,
        context_window,
    )
    return checkpoint.to_dict()


def resume_from_checkpoint(checkpoint_id: str) -> dict:
    """Resume execution from saved checkpoint"""
    state = recovery_manager.resume_from_checkpoint(checkpoint_id)
    if state:
        return {"resumed": True, "state": state.to_dict()}
    return {"resumed": False, "error": "Checkpoint not found"}


def create_alternative_branch(
    parent_checkpoint_id: str,
    new_state_id: str,
    agent_id: str,
    turn: int,
    variables: dict,
    call_stack: list,
) -> dict:
    """Create branched execution path"""
    new_state = ExecutionState(
        state_id=new_state_id,
        agent_id=agent_id,
        scope=StateScope.CONVERSATION,
        turn=turn,
        variables=variables,
        call_stack=call_stack,
        tool_results={},
        context_window={},
        timestamp=datetime.now().isoformat(),
        metadata={},
    )

    checkpoint = recovery_manager.create_alternative_path(
        parent_checkpoint_id,
        new_state,
    )
    return checkpoint.to_dict() if checkpoint else {"error": "Parent not found"}


def get_state_recovery_summary(agent_id: str) -> dict:
    """Get state recovery statistics"""
    return recovery_manager.get_recovery_summary(agent_id)


def list_checkpoints(agent_id: str) -> dict:
    """List all checkpoints for agent"""
    checkpoints = recovery_manager.store.get_checkpoint_history(agent_id)
    return {
        "agent_id": agent_id,
        "checkpoints": [cp.to_dict() for cp in checkpoints],
    }


if __name__ == "__main__":
    # Test state recovery
    manager = StateRecoveryManager()

    # Capture state
    checkpoint = manager.capture_state(
        state_id="exec_001",
        agent_id="agent_1",
        scope=StateScope.CONVERSATION,
        turn=5,
        variables={"topic": "data analysis", "progress": 0.5},
        call_stack=[{"function": "analyze", "args": []}],
        tool_results={"search": "results here"},
        context_window={"earlier": "context"},
    )
    print(f"Captured checkpoint: {checkpoint.checkpoint_id}")

    # Resume from checkpoint
    state = manager.resume_from_checkpoint(checkpoint.checkpoint_id)
    print(f"Resumed state: turn={state.turn}, agent={state.agent_id}")

    # Get summary
    summary = manager.get_recovery_summary("agent_1")
    print(f"Recovery summary: {json.dumps(summary, indent=2)}")
