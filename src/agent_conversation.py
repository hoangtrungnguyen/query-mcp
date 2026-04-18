"""Agent-to-agent conversation protocol and messaging"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

AGENT_DIR = Path.home() / ".memory-mcp" / "agent-conversation"
AGENT_DIR.mkdir(exist_ok=True, parents=True)


class AgentRole(Enum):
    """Role of agent in conversation"""
    INITIATOR = "initiator"  # Started conversation
    RESPONDER = "responder"  # Responding to initiator
    MEDIATOR = "mediator"  # Facilitating between agents
    OBSERVER = "observer"  # Monitoring but not speaking


class MessageType(Enum):
    """Types of agent messages"""
    REQUEST = "request"  # Asking for info/action
    RESPONSE = "response"  # Answering request
    CLARIFICATION = "clarification"  # Asking for details
    AGREEMENT = "agreement"  # Accepting proposal
    REJECTION = "rejection"  # Declining proposal
    HANDOFF = "handoff"  # Passing conversation to another agent
    STATUS = "status"  # Reporting current state


class HandoffReason(Enum):
    """Why conversation is handed off"""
    EXPERTISE = "expertise"  # Other agent has better expertise
    BLOCKED = "blocked"  # This agent is blocked, other can help
    SPECIALIZATION = "specialization"  # Task requires specialized agent
    OVERLOAD = "overload"  # This agent at capacity
    USER_REQUEST = "user_request"  # User specifically asked for other agent


@dataclass
class AgentMessage:
    """Message from one agent to another"""
    message_id: str
    sender_agent: str
    receiver_agent: str
    message_type: MessageType
    content: str
    context: Dict[str, Any] = field(default_factory=dict)  # Shared context
    confidence: float = 0.8
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize message"""
        return {
            "message_id": self.message_id,
            "sender": self.sender_agent,
            "receiver": self.receiver_agent,
            "type": self.message_type.value,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class Handoff:
    """Handoff of conversation between agents"""
    handoff_id: str
    from_agent: str
    to_agent: str
    reason: HandoffReason
    context_transferred: Dict[str, Any] = field(default_factory=dict)
    turn_num: int = 0
    success: bool = False

    def to_dict(self) -> Dict:
        """Serialize handoff"""
        return {
            "handoff_id": self.handoff_id,
            "from": self.from_agent,
            "to": self.to_agent,
            "reason": self.reason.value,
            "success": self.success,
        }


@dataclass
class AgentConversationState:
    """State of agent-to-agent conversation"""
    conversation_id: str
    agents: List[str]  # Participating agents
    current_agent: str  # Who's speaking
    turn_num: int = 0
    messages: List[AgentMessage] = field(default_factory=list)
    handoffs: List[Handoff] = field(default_factory=list)
    shared_context: Dict[str, Any] = field(default_factory=dict)
    goal: str = ""
    goal_achieved: bool = False

    def to_dict(self) -> Dict:
        """Serialize state"""
        return {
            "conversation_id": self.conversation_id,
            "agents": len(self.agents),
            "current_agent": self.current_agent,
            "turns": self.turn_num,
            "goal_achieved": self.goal_achieved,
        }


class AgentConversationManager:
    """Manage agent-to-agent conversations"""

    def __init__(self):
        self.conversations: Dict[str, AgentConversationState] = {}
        self.agent_registry: Dict[str, Dict] = {}  # Agent metadata

    def register_agent(
        self,
        agent_id: str,
        agent_name: str,
        capabilities: List[str],
        expertise_areas: List[str],
    ):
        """Register agent in system"""
        self.agent_registry[agent_id] = {
            "id": agent_id,
            "name": agent_name,
            "capabilities": capabilities,
            "expertise": expertise_areas,
            "registered_at": datetime.now().isoformat(),
        }

    def create_agent_conversation(
        self,
        conversation_id: str,
        agents: List[str],
        goal: str,
        initiator: str,
    ) -> AgentConversationState:
        """Create conversation between agents"""
        state = AgentConversationState(
            conversation_id=conversation_id,
            agents=agents,
            current_agent=initiator,
            goal=goal,
        )
        self.conversations[conversation_id] = state
        return state

    def send_agent_message(
        self,
        conversation_id: str,
        sender: str,
        receiver: str,
        message_type: MessageType,
        content: str,
    ) -> AgentMessage:
        """Send message between agents"""
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation = self.conversations[conversation_id]

        message = AgentMessage(
            message_id=f"msg_{conversation.turn_num}_{int(datetime.now().timestamp())}",
            sender_agent=sender,
            receiver_agent=receiver,
            message_type=message_type,
            content=content,
            context=conversation.shared_context.copy(),
        )

        conversation.messages.append(message)
        conversation.turn_num += 1
        conversation.current_agent = receiver

        return message

    def initiate_handoff(
        self,
        conversation_id: str,
        from_agent: str,
        to_agent: str,
        reason: HandoffReason,
        context: Dict[str, Any] = None,
    ) -> Handoff:
        """Initiate handoff between agents"""
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation = self.conversations[conversation_id]

        handoff = Handoff(
            handoff_id=f"handoff_{conversation.turn_num}",
            from_agent=from_agent,
            to_agent=to_agent,
            reason=reason,
            context_transferred=context or conversation.shared_context.copy(),
            turn_num=conversation.turn_num,
            success=False,
        )

        conversation.handoffs.append(handoff)
        conversation.current_agent = to_agent

        # Mark handoff successful if new agent accepts
        handoff.success = True

        return handoff

    def update_shared_context(
        self,
        conversation_id: str,
        updates: Dict[str, Any],
    ):
        """Update context shared by all agents"""
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation = self.conversations[conversation_id]
        conversation.shared_context.update(updates)

    def complete_goal(self, conversation_id: str):
        """Mark conversation goal as achieved"""
        if conversation_id not in self.conversations:
            return

        conversation = self.conversations[conversation_id]
        conversation.goal_achieved = True

    def get_conversation_summary(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation summary"""
        conversation = self.conversations.get(conversation_id)
        if not conversation:
            return None

        return {
            "conversation_id": conversation_id,
            "agents": conversation.agents,
            "turns": conversation.turn_num,
            "messages": len(conversation.messages),
            "handoffs": len(conversation.handoffs),
            "goal": conversation.goal,
            "goal_achieved": conversation.goal_achieved,
            "current_agent": conversation.current_agent,
        }

    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get agent's conversation statistics"""
        sent_count = 0
        received_count = 0
        handoffs_initiated = 0
        handoffs_received = 0

        for conversation in self.conversations.values():
            for message in conversation.messages:
                if message.sender_agent == agent_id:
                    sent_count += 1
                if message.receiver_agent == agent_id:
                    received_count += 1

            for handoff in conversation.handoffs:
                if handoff.from_agent == agent_id:
                    handoffs_initiated += 1
                if handoff.to_agent == agent_id:
                    handoffs_received += 1

        return {
            "agent_id": agent_id,
            "messages_sent": sent_count,
            "messages_received": received_count,
            "handoffs_initiated": handoffs_initiated,
            "handoffs_received": handoffs_received,
            "total_conversations": len([c for c in self.conversations.values() if agent_id in c.agents]),
        }


# Global manager
agent_conversation_manager = AgentConversationManager()


# MCP Tools

def register_agent(agent_id: str, agent_name: str, capabilities: list, expertise: list) -> dict:
    """Register agent"""
    agent_conversation_manager.register_agent(agent_id, agent_name, capabilities, expertise)
    return {"agent_id": agent_id, "registered": True}


def create_agent_conversation(
    conversation_id: str,
    agents: list,
    goal: str,
    initiator: str,
) -> dict:
    """Create agent conversation"""
    conversation = agent_conversation_manager.create_agent_conversation(
        conversation_id, agents, goal, initiator
    )
    return conversation.to_dict()


def send_agent_message(
    conversation_id: str,
    sender: str,
    receiver: str,
    message_type: str,
    content: str,
) -> dict:
    """Send agent message"""
    try:
        msg_type = MessageType(message_type)
        message = agent_conversation_manager.send_agent_message(
            conversation_id, sender, receiver, msg_type, content
        )
        return message.to_dict()
    except ValueError as e:
        return {"error": str(e)}


def initiate_handoff(
    conversation_id: str,
    from_agent: str,
    to_agent: str,
    reason: str,
) -> dict:
    """Initiate handoff"""
    try:
        handoff_reason = HandoffReason(reason)
        handoff = agent_conversation_manager.initiate_handoff(
            conversation_id, from_agent, to_agent, handoff_reason
        )
        return handoff.to_dict()
    except ValueError as e:
        return {"error": str(e)}


def get_conversation_summary(conversation_id: str) -> dict:
    """Get conversation summary"""
    summary = agent_conversation_manager.get_conversation_summary(conversation_id)
    return summary or {"error": "Conversation not found"}


def get_agent_stats(agent_id: str) -> dict:
    """Get agent statistics"""
    return agent_conversation_manager.get_agent_stats(agent_id)


if __name__ == "__main__":
    # Test agent conversation
    manager = AgentConversationManager()

    # Register agents
    manager.register_agent("agent_1", "Analyzer", ["analyze"], ["data"])
    manager.register_agent("agent_2", "Executor", ["execute"], ["actions"])

    # Create conversation
    conv = manager.create_agent_conversation("conv_1", ["agent_1", "agent_2"], "Analyze and execute", "agent_1")
    print(f"Conversation: {json.dumps(conv.to_dict(), indent=2)}")

    # Send messages
    msg = manager.send_agent_message("conv_1", "agent_1", "agent_2", MessageType.REQUEST, "Please execute X")
    print(f"Message: {json.dumps(msg.to_dict(), indent=2)}")

    # Get summary
    summary = manager.get_conversation_summary("conv_1")
    print(f"Summary: {json.dumps(summary, indent=2)}")
