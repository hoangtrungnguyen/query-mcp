"""Dialogue state management and conversation flow control"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

DIALOGUE_DIR = Path.home() / ".memory-mcp" / "dialogue-state"
DIALOGUE_DIR.mkdir(exist_ok=True, parents=True)


class DialogueAct(Enum):
    """Types of dialogue acts"""
    INFORM = "inform"  # Provide information
    REQUEST = "request"  # Ask for information
    CONFIRM = "confirm"  # Verify understanding
    CLARIFY = "clarify"  # Request clarification
    ACCEPT = "accept"  # Accept proposal
    REJECT = "reject"  # Decline proposal
    GREET = "greet"  # Greeting
    FAREWELL = "farewell"  # Goodbye
    ACKNOWLEDGE = "acknowledge"  # Got it
    SUGGEST = "suggest"  # Make suggestion


class DialogueState(Enum):
    """States in conversation flow"""
    INIT = "init"  # Conversation start
    UNDERSTANDING = "understanding"  # Building understanding
    PROBLEM_SOLVING = "problem_solving"  # Working on problem
    INFORMATION_SEEKING = "information_seeking"  # Gathering info
    NEGOTIATION = "negotiation"  # Discussing options
    DECISION = "decision"  # Making decision
    EXECUTION = "execution"  # Carrying out plan
    CLOSING = "closing"  # Wrapping up
    ENDED = "ended"  # Conversation done


class Slot(Enum):
    """Information slots in dialogue"""
    TOPIC = "topic"  # What are we discussing
    GOAL = "goal"  # What do they want to achieve
    CONSTRAINTS = "constraints"  # Any limitations
    PREFERENCES = "preferences"  # How they want it done
    STATUS = "status"  # Progress status
    NEXT_ACTION = "next_action"  # What's next


@dataclass
class DialogueSlot:
    """Slot value pair in dialogue"""
    slot_type: Slot
    value: Any
    confidence: float = 0.8
    updated_at: str = ""

    def __post_init__(self):
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize slot"""
        return {
            "slot": self.slot_type.value,
            "value": str(self.value)[:50],
            "confidence": self.confidence,
        }


@dataclass
class ConversationContext:
    """Current conversation context"""
    context_id: str
    current_state: DialogueState
    slots: Dict[Slot, DialogueSlot] = field(default_factory=dict)
    dialogue_history: List[Dict[str, Any]] = field(default_factory=list)
    turn_count: int = 0
    last_act: Optional[DialogueAct] = None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def update_slot(self, slot_type: Slot, value: Any, confidence: float = 0.8):
        """Update slot value"""
        self.slots[slot_type] = DialogueSlot(slot_type, value, confidence)

    def get_slot(self, slot_type: Slot) -> Optional[Any]:
        """Get slot value"""
        slot = self.slots.get(slot_type)
        return slot.value if slot else None

    def to_dict(self) -> Dict:
        """Serialize context"""
        return {
            "context_id": self.context_id,
            "state": self.current_state.value,
            "slots_filled": len(self.slots),
            "turns": self.turn_count,
            "last_act": self.last_act.value if self.last_act else None,
        }


@dataclass
class DialogueTransition:
    """Transition between dialogue states"""
    transition_id: str
    from_state: DialogueState
    to_state: DialogueState
    trigger: DialogueAct
    conditions: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    probability: float = 1.0  # If probabilistic

    def to_dict(self) -> Dict:
        """Serialize transition"""
        return {
            "transition_id": self.transition_id,
            "from": self.from_state.value,
            "to": self.to_state.value,
            "trigger": self.trigger.value,
            "actions": len(self.actions),
        }


class DialoguePolicy:
    """Policy for managing dialogue flow"""

    def __init__(self):
        self.transitions: Dict[str, DialogueTransition] = {}
        self.state_actions: Dict[DialogueState, List[Callable]] = {}

    def add_transition(
        self,
        from_state: DialogueState,
        to_state: DialogueState,
        trigger: DialogueAct,
        conditions: List[str] = None,
    ) -> DialogueTransition:
        """Add state transition"""
        transition = DialogueTransition(
            transition_id=f"trans_{from_state.value}_{to_state.value}",
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            conditions=conditions or [],
        )
        self.transitions[transition.transition_id] = transition
        return transition

    def get_next_state(
        self,
        current_state: DialogueState,
        dialogue_act: DialogueAct,
        context: ConversationContext,
    ) -> Optional[DialogueState]:
        """Get next state based on current state and act"""
        candidates = [
            t for t in self.transitions.values()
            if t.from_state == current_state and t.trigger == dialogue_act
        ]

        if not candidates:
            return None

        # Check conditions
        for transition in candidates:
            # Simple condition checking
            if not transition.conditions:
                return transition.to_state

        return candidates[0].to_state if candidates else None

    def get_valid_acts(self, current_state: DialogueState) -> List[DialogueAct]:
        """Get valid dialogue acts for state"""
        valid = set()
        for trans in self.transitions.values():
            if trans.from_state == current_state:
                valid.add(trans.trigger)

        return list(valid)


class StateManager:
    """Manage dialogue state and flow"""

    def __init__(self):
        self.contexts: Dict[str, ConversationContext] = {}
        self.policy = DialoguePolicy()
        self._setup_default_policy()

    def _setup_default_policy(self):
        """Set up default dialogue policy"""
        # Greeting → Understanding
        self.policy.add_transition(
            DialogueState.INIT,
            DialogueState.UNDERSTANDING,
            DialogueAct.GREET,
        )

        # Understanding → Problem Solving
        self.policy.add_transition(
            DialogueState.UNDERSTANDING,
            DialogueState.PROBLEM_SOLVING,
            DialogueAct.INFORM,
        )

        # Problem Solving → Decision
        self.policy.add_transition(
            DialogueState.PROBLEM_SOLVING,
            DialogueState.DECISION,
            DialogueAct.CONFIRM,
        )

        # Decision → Execution
        self.policy.add_transition(
            DialogueState.DECISION,
            DialogueState.EXECUTION,
            DialogueAct.ACCEPT,
        )

        # Execution → Closing
        self.policy.add_transition(
            DialogueState.EXECUTION,
            DialogueState.CLOSING,
            DialogueAct.ACKNOWLEDGE,
        )

        # Any state → Closing
        for state in DialogueState:
            if state != DialogueState.CLOSING and state != DialogueState.ENDED:
                self.policy.add_transition(
                    state,
                    DialogueState.CLOSING,
                    DialogueAct.FAREWELL,
                )

        # Closing → Ended
        self.policy.add_transition(
            DialogueState.CLOSING,
            DialogueState.ENDED,
            DialogueAct.FAREWELL,
        )

    def create_context(self, context_id: str) -> ConversationContext:
        """Create new dialogue context"""
        context = ConversationContext(
            context_id=context_id,
            current_state=DialogueState.INIT,
        )
        self.contexts[context_id] = context
        return context

    def process_turn(
        self,
        context_id: str,
        user_input: str,
        detected_act: DialogueAct,
    ) -> Dict[str, Any]:
        """Process conversation turn"""
        if context_id not in self.contexts:
            return {"error": "Context not found"}

        context = self.contexts[context_id]

        # Get next state
        next_state = self.policy.get_next_state(
            context.current_state,
            detected_act,
            context,
        )

        # Update context
        context.turn_count += 1
        context.last_act = detected_act
        context.dialogue_history.append({
            "turn": context.turn_count,
            "input": user_input,
            "act": detected_act.value,
            "previous_state": context.current_state.value,
            "next_state": next_state.value if next_state else None,
        })

        if next_state:
            context.current_state = next_state

        return {
            "context_id": context_id,
            "previous_state": context.dialogue_history[-1]["previous_state"],
            "new_state": context.current_state.value,
            "valid_acts": [a.value for a in self.policy.get_valid_acts(context.current_state)],
            "turn": context.turn_count,
        }

    def get_dialogue_summary(self, context_id: str) -> Optional[Dict[str, Any]]:
        """Get dialogue summary"""
        if context_id not in self.contexts:
            return None

        context = self.contexts[context_id]

        return {
            "context_id": context_id,
            "state": context.current_state.value,
            "turns": context.turn_count,
            "topic": str(context.get_slot(Slot.TOPIC)),
            "goal": str(context.get_slot(Slot.GOAL)),
            "slots_filled": len(context.slots),
            "completion": (
                100 if context.current_state == DialogueState.ENDED else
                (context.turn_count / 10 * 100) if context.turn_count < 10 else 100
            ),
        }

    def get_state_info(self, context_id: str) -> Optional[Dict]:
        """Get detailed state information"""
        if context_id not in self.contexts:
            return None

        context = self.contexts[context_id]

        return {
            "context": context.to_dict(),
            "valid_next_acts": [
                a.value for a in self.policy.get_valid_acts(context.current_state)
            ],
            "slots": [s.to_dict() for s in context.slots.values()],
            "history_length": len(context.dialogue_history),
        }


class DialogueManager:
    """Manage dialogue states across conversations"""

    def __init__(self):
        self.managers: Dict[str, StateManager] = {}

    def create_manager(self, manager_id: str) -> StateManager:
        """Create state manager"""
        manager = StateManager()
        self.managers[manager_id] = manager
        return manager

    def get_manager(self, manager_id: str) -> Optional[StateManager]:
        """Get manager"""
        return self.managers.get(manager_id)


# Global manager
dialogue_manager = DialogueManager()


# MCP Tools

def create_dialogue_manager(manager_id: str) -> dict:
    """Create dialogue state manager"""
    manager = dialogue_manager.create_manager(manager_id)
    return {"manager_id": manager_id, "created": True}


def create_dialogue_context(manager_id: str, context_id: str) -> dict:
    """Create dialogue context"""
    manager = dialogue_manager.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    context = manager.create_context(context_id)
    return context.to_dict()


def process_dialogue_turn(
    manager_id: str,
    context_id: str,
    user_input: str,
    dialogue_act: str,
) -> dict:
    """Process dialogue turn"""
    manager = dialogue_manager.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    return manager.process_turn(context_id, user_input, DialogueAct(dialogue_act))


def get_dialogue_summary(manager_id: str, context_id: str) -> dict:
    """Get dialogue summary"""
    manager = dialogue_manager.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    summary = manager.get_dialogue_summary(context_id)
    return summary or {"error": "Context not found"}


def get_state_info(manager_id: str, context_id: str) -> dict:
    """Get state information"""
    manager = dialogue_manager.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    info = manager.get_state_info(context_id)
    return info or {"error": "Context not found"}


if __name__ == "__main__":
    # Test dialogue state management
    manager = StateManager()
    context = manager.create_context("ctx_1")

    # Simulate conversation
    manager.process_turn("ctx_1", "Hello", DialogueAct.GREET)
    manager.process_turn("ctx_1", "I need help with X", DialogueAct.INFORM)
    manager.process_turn("ctx_1", "I want Y", DialogueAct.CONFIRM)
    manager.process_turn("ctx_1", "Yes, proceed", DialogueAct.ACCEPT)
    manager.process_turn("ctx_1", "Done", DialogueAct.ACKNOWLEDGE)

    # Summary
    summary = manager.get_dialogue_summary("ctx_1")
    print(f"Summary: {json.dumps(summary, indent=2)}")

    # State info
    info = manager.get_state_info("ctx_1")
    print(f"State info: {json.dumps(info, indent=2)}")
