"""Dialogue context stacking and topic management"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

STACK_DIR = Path.home() / ".memory-mcp" / "context-stacking"
STACK_DIR.mkdir(exist_ok=True, parents=True)


class ContextStatus(Enum):
    """Status of dialogue context"""
    ACTIVE = "active"  # Currently being discussed
    SUSPENDED = "suspended"  # Set aside, can resume
    CLOSED = "closed"  # Finished, not resumable
    INTERRUPTED = "interrupted"  # Abruptly suspended


@dataclass
class DialogueContext:
    """Dialogue context (topic, goals, entities)"""
    context_id: str
    topic: str
    status: ContextStatus
    start_turn: int
    entities: List[str] = field(default_factory=list)  # Key entities
    goals: List[str] = field(default_factory=list)  # Dialogue goals
    assumptions: List[str] = field(default_factory=list)  # Working assumptions
    resolution: Optional[str] = None  # How topic resolved (if closed)
    end_turn: Optional[int] = None

    def to_dict(self) -> Dict:
        """Serialize context"""
        return {
            "context_id": self.context_id,
            "topic": self.topic,
            "status": self.status.value,
            "start_turn": self.start_turn,
            "entities": len(self.entities),
        }


@dataclass
class ContextStackFrame:
    """Frame in context stack"""
    frame_id: str
    context: DialogueContext
    depth: int  # Position in stack (0=bottom)
    pushed_at: str
    suspended_at: Optional[str] = None

    def to_dict(self) -> Dict:
        """Serialize frame"""
        return {
            "frame_id": self.frame_id,
            "topic": self.context.topic,
            "depth": self.depth,
            "status": self.context.status.value,
        }


@dataclass
class ContextTransition:
    """Transition between contexts"""
    transition_id: str
    from_context: str
    to_context: str
    transition_type: str  # PUSH, POP, SWITCH
    turn_num: int
    reason: str = ""

    def to_dict(self) -> Dict:
        """Serialize transition"""
        return {
            "transition_id": self.transition_id,
            "type": self.transition_type,
            "turn": self.turn_num,
            "reason": self.reason,
        }


class ContextStack:
    """Stack-based context management"""

    def __init__(self):
        self.stack: List[ContextStackFrame] = []
        self.all_contexts: Dict[str, DialogueContext] = {}
        self.transitions: List[ContextTransition] = []

    def push_context(
        self,
        topic: str,
        turn_num: int,
        entities: List[str] = None,
        goals: List[str] = None,
    ) -> ContextStackFrame:
        """Push new context onto stack"""
        context = DialogueContext(
            context_id=f"ctx_{len(self.all_contexts)}",
            topic=topic,
            status=ContextStatus.ACTIVE,
            start_turn=turn_num,
            entities=entities or [],
            goals=goals or [],
        )
        self.all_contexts[context.context_id] = context

        # Suspend current context if any
        if self.stack:
            self.stack[-1].context.status = ContextStatus.SUSPENDED
            self.stack[-1].suspended_at = datetime.now().isoformat()

        # Create frame
        frame = ContextStackFrame(
            frame_id=f"frame_{len(self.stack)}",
            context=context,
            depth=len(self.stack),
            pushed_at=datetime.now().isoformat(),
        )
        self.stack.append(frame)

        # Record transition
        if self.stack and len(self.stack) > 1:
            prev_id = self.stack[-2].context.context_id
            transition = ContextTransition(
                transition_id=f"trans_{len(self.transitions)}",
                from_context=prev_id,
                to_context=context.context_id,
                transition_type="PUSH",
                turn_num=turn_num,
                reason=f"New topic: {topic}",
            )
            self.transitions.append(transition)

        return frame

    def pop_context(
        self,
        turn_num: int,
        resolution: str = "",
    ) -> Optional[ContextStackFrame]:
        """Pop context from stack"""
        if not self.stack:
            return None

        popped_frame = self.stack.pop()
        popped_frame.context.status = ContextStatus.CLOSED
        popped_frame.context.end_turn = turn_num
        popped_frame.context.resolution = resolution

        # Reactivate previous context
        if self.stack:
            self.stack[-1].context.status = ContextStatus.ACTIVE
            self.stack[-1].suspended_at = None

        # Record transition
        if len(self.stack) > 0:
            next_context = self.stack[-1].context.context_id if self.stack else None
            if next_context:
                transition = ContextTransition(
                    transition_id=f"trans_{len(self.transitions)}",
                    from_context=popped_frame.context.context_id,
                    to_context=next_context,
                    transition_type="POP",
                    turn_num=turn_num,
                    reason=f"Resolved: {resolution}",
                )
                self.transitions.append(transition)

        return popped_frame

    def peek_context(self) -> Optional[DialogueContext]:
        """Get current (top) context"""
        if self.stack:
            return self.stack[-1].context
        return None

    def get_context_path(self) -> List[str]:
        """Get path of contexts (topics) from bottom to top"""
        return [frame.context.topic for frame in self.stack]

    def get_stack_depth(self) -> int:
        """Get current stack depth"""
        return len(self.stack)

    def get_suspended_contexts(self) -> List[DialogueContext]:
        """Get suspended contexts"""
        suspended = []
        for frame in self.stack[:-1]:  # All but top
            if frame.context.status == ContextStatus.SUSPENDED:
                suspended.append(frame.context)
        return suspended

    def get_summary(self) -> Dict[str, Any]:
        """Get stack summary"""
        return {
            "depth": len(self.stack),
            "context_path": self.get_context_path(),
            "current_topic": self.stack[-1].context.topic if self.stack else None,
            "suspended": len(self.get_suspended_contexts()),
            "total_contexts": len(self.all_contexts),
            "transitions": len(self.transitions),
        }


class ContextStackManager:
    """Manage context stacks across conversations"""

    def __init__(self):
        self.stacks: Dict[str, ContextStack] = {}

    def create_stack(self, stack_id: str) -> ContextStack:
        """Create context stack"""
        stack = ContextStack()
        self.stacks[stack_id] = stack
        return stack

    def get_stack(self, stack_id: str) -> Optional[ContextStack]:
        """Get stack"""
        return self.stacks.get(stack_id)

    def push_to_stack(
        self,
        stack_id: str,
        topic: str,
        turn_num: int,
        entities: List[str] = None,
        goals: List[str] = None,
    ) -> Dict[str, Any]:
        """Push context"""
        stack = self.get_stack(stack_id)
        if not stack:
            return {"error": "Stack not found"}

        frame = stack.push_context(topic, turn_num, entities, goals)
        return {
            "frame_id": frame.frame_id,
            "topic": topic,
            "depth": frame.depth,
            "stack_depth": stack.get_stack_depth(),
        }

    def pop_from_stack(
        self,
        stack_id: str,
        turn_num: int,
        resolution: str = "",
    ) -> Dict[str, Any]:
        """Pop context"""
        stack = self.get_stack(stack_id)
        if not stack:
            return {"error": "Stack not found"}

        popped = stack.pop_context(turn_num, resolution)
        if not popped:
            return {"error": "Stack is empty"}

        return {
            "popped_topic": popped.context.topic,
            "stack_depth": stack.get_stack_depth(),
            "resumed_topic": stack.peek_context().topic if stack.peek_context() else None,
        }

    def get_stack_info(self, stack_id: str) -> Optional[Dict[str, Any]]:
        """Get stack information"""
        stack = self.get_stack(stack_id)
        if not stack:
            return None

        return stack.get_summary()


# Global manager
stack_manager = ContextStackManager()


# MCP Tools

def create_context_stack(stack_id: str) -> dict:
    """Create context stack"""
    stack = stack_manager.create_stack(stack_id)
    return {"stack_id": stack_id, "created": True}


def push_context(
    stack_id: str,
    topic: str,
    turn_num: int,
    entities: list = None,
) -> dict:
    """Push context onto stack"""
    return stack_manager.push_to_stack(stack_id, topic, turn_num, entities)


def pop_context(
    stack_id: str,
    turn_num: int,
    resolution: str = "",
) -> dict:
    """Pop context from stack"""
    return stack_manager.pop_from_stack(stack_id, turn_num, resolution)


def get_context_stack_info(stack_id: str) -> dict:
    """Get stack information"""
    info = stack_manager.get_stack_info(stack_id)
    return info or {"error": "Stack not found"}


if __name__ == "__main__":
    stack = ContextStack()

    # Simulate topic flow
    stack.push_context("weather", 1, goals=["discuss temperature"])
    stack.push_context("vacation plans", 3, goals=["plan trip"])
    stack.push_context("flight booking", 5, goals=["book flight"])

    print(f"Stack path: {stack.get_context_path()}")
    print(f"Depth: {stack.get_stack_depth()}")

    # Pop contexts
    stack.pop_context(8, "flight booked")
    print(f"After pop: {stack.get_context_path()}")

    summary = stack.get_summary()
    print(f"Summary: {json.dumps(summary, indent=2)}")
