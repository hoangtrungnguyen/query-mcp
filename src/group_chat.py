"""Group chat orchestration for multi-agent conversations"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass

CHATS_DIR = Path.home() / ".memory-mcp" / "group-chats"
CHATS_DIR.mkdir(exist_ok=True, parents=True)


class SpeakerSelection(Enum):
    """Speaker selection strategies"""
    ROUND_ROBIN = "round_robin"
    CONTEXT_AWARE = "context_aware"
    RANDOM = "random"
    MODERATOR_CHOSEN = "moderator_chosen"


class AgentRole(Enum):
    """Roles agents can play in group chat"""
    PARTICIPANT = "participant"
    EXPERT = "expert"  # Domain expert
    DEVIL_ADVOCATE = "devil_advocate"  # Challenges proposals
    MODERATOR = "moderator"  # Guides discussion
    SYNTHESIZER = "synthesizer"  # Summarizes consensus
    JUDGE = "judge"  # Makes final decision


@dataclass
class AgentParticipant:
    """Agent participating in group chat"""
    agent_id: str
    agent_name: str
    role: AgentRole
    expertise: Optional[str] = None  # Domain expertise
    has_spoken: bool = False
    turn_count: int = 0
    last_response: Optional[str] = None


class GroupChatMessage:
    """Message in group chat"""

    def __init__(
        self,
        speaker_id: str,
        content: str,
        role: AgentRole,
        turn: int,
    ):
        self.speaker_id = speaker_id
        self.content = content
        self.role = role.value
        self.turn = turn
        self.timestamp = datetime.now().isoformat()
        self.reactions: Dict[str, str] = {}  # Other agents' reactions
        self.citations: List[str] = []  # References to other messages

    def add_reaction(self, reactor_id: str, reaction: str):
        """Add reaction from another agent"""
        self.reactions[reactor_id] = reaction

    def to_dict(self) -> Dict:
        """Serialize message"""
        return {
            "speaker_id": self.speaker_id,
            "content": self.content,
            "role": self.role,
            "turn": self.turn,
            "timestamp": self.timestamp,
            "reactions": self.reactions,
            "citations": self.citations,
        }


class GroupChat:
    """Group chat session with multiple agents"""

    def __init__(
        self,
        chat_id: str,
        topic: str,
        max_agents: int = 3,
        strategy: SpeakerSelection = SpeakerSelection.ROUND_ROBIN,
    ):
        self.chat_id = chat_id
        self.topic = topic
        self.max_agents = max_agents
        self.strategy = strategy
        self.agents: Dict[str, AgentParticipant] = {}
        self.messages: List[GroupChatMessage] = []
        self.turn_order: List[str] = []
        self.current_turn = 0
        self.created_at = datetime.now().isoformat()
        self.consensus: Optional[Dict] = None
        self.debate_status = "active"
        self.halt_reason: Optional[str] = None

    def add_agent(
        self,
        agent_id: str,
        agent_name: str,
        role: AgentRole,
        expertise: Optional[str] = None,
    ) -> bool:
        """Add agent to chat"""
        if len(self.agents) >= self.max_agents:
            return False

        agent = AgentParticipant(
            agent_id=agent_id,
            agent_name=agent_name,
            role=role,
            expertise=expertise,
        )
        self.agents[agent_id] = agent
        self.turn_order.append(agent_id)
        return True

    def add_message(self, speaker_id: str, content: str) -> Optional[GroupChatMessage]:
        """Add message from agent"""
        if speaker_id not in self.agents:
            return None

        agent = self.agents[speaker_id]
        message = GroupChatMessage(
            speaker_id=speaker_id,
            content=content,
            role=agent.role,
            turn=self.current_turn,
        )

        self.messages.append(message)
        agent.has_spoken = True
        agent.turn_count += 1
        agent.last_response = content

        return message

    def select_next_speaker(self) -> Optional[str]:
        """Select next speaker based on strategy"""
        if self.strategy == SpeakerSelection.ROUND_ROBIN:
            # Round-robin: cycle through agents
            if not self.turn_order:
                return None
            speaker = self.turn_order[self.current_turn % len(self.turn_order)]
            return speaker

        elif self.strategy == SpeakerSelection.CONTEXT_AWARE:
            # Context-aware: select agent whose expertise matches
            if not self.messages:
                return self.turn_order[0] if self.turn_order else None

            # Simple heuristic: prefer agent who hasn't spoken recently
            last_speakers = {m.speaker_id for m in self.messages[-3:]}
            available = [a for a in self.turn_order if a not in last_speakers]
            return available[0] if available else self.turn_order[0]

        elif self.strategy == SpeakerSelection.RANDOM:
            import random

            return random.choice(self.turn_order) if self.turn_order else None

        return None

    def advance_turn(self):
        """Move to next turn"""
        self.current_turn += 1

    def detect_consensus(self, threshold: float = 0.7) -> Optional[Dict]:
        """Detect consensus among agents (with hallucination risk warning)"""
        if len(self.messages) < len(self.agents):
            return None

        # Simple consensus detection: check for agreement keywords
        last_round = self.messages[-len(self.agents) :]
        agreement_count = sum(
            1
            for m in last_round
            if any(
                keyword in m.content.lower()
                for keyword in ["agree", "correct", "true", "yes", "confirmed"]
            )
        )

        consensus_reached = agreement_count >= (len(self.agents) * threshold)

        if consensus_reached:
            return {
                "reached": True,
                "agreement_ratio": agreement_count / len(self.agents),
                "turn": self.current_turn,
                "warning": "HALLUCINATED CONSENSUS RISK: Verify agreement is based on facts, not false premises",
                "messages": [m.to_dict() for m in last_round],
            }

        return {"reached": False, "agreement_ratio": agreement_count / len(self.agents)}

    def check_halt_conditions(self) -> bool:
        """Check if debate should halt"""
        # Halt if: consensus reached, max turns exceeded, no progress
        if self.detect_consensus().get("reached"):
            self.halt_reason = "consensus_reached"
            return True

        if self.current_turn >= 10:  # Max 10 turns
            self.halt_reason = "max_turns_exceeded"
            return True

        # Check for repetition (same topic, no new info)
        if len(self.messages) > 6:
            recent = [m.content for m in self.messages[-3:]]
            previous = [m.content for m in self.messages[-6:-3]]
            if recent == previous:
                self.halt_reason = "no_progress"
                return True

        return False

    def get_synthesis(self) -> Dict:
        """Get synthesized view of conversation"""
        synthesis = {
            "chat_id": self.chat_id,
            "topic": self.topic,
            "turns": self.current_turn,
            "participants": list(self.agents.keys()),
            "message_count": len(self.messages),
            "consensus": self.detect_consensus(),
            "key_points": self._extract_key_points(),
            "disagreements": self._extract_disagreements(),
            "final_status": self.debate_status,
            "halt_reason": self.halt_reason,
        }
        return synthesis

    def _extract_key_points(self) -> List[str]:
        """Extract key points from conversation"""
        key_points = []
        for msg in self.messages:
            # Simple heuristic: sentences with "important", "key", "conclude"
            if any(keyword in msg.content.lower() for keyword in ["important", "key", "conclude"]):
                key_points.append(msg.content[:100])
        return key_points[:5]

    def _extract_disagreements(self) -> List[Dict]:
        """Extract points of disagreement"""
        disagreements = []
        for msg in self.messages:
            if any(
                keyword in msg.content.lower()
                for keyword in ["disagree", "but", "however", "contrary", "instead"]
            ):
                disagreements.append({
                    "agent": msg.speaker_id,
                    "statement": msg.content[:100],
                    "turn": msg.turn,
                })
        return disagreements[:5]

    def to_dict(self) -> Dict:
        """Serialize chat"""
        return {
            "chat_id": self.chat_id,
            "topic": self.topic,
            "created_at": self.created_at,
            "max_agents": self.max_agents,
            "strategy": self.strategy.value,
            "agents": {
                aid: {
                    "name": a.agent_name,
                    "role": a.role.value,
                    "expertise": a.expertise,
                    "turn_count": a.turn_count,
                }
                for aid, a in self.agents.items()
            },
            "messages": [m.to_dict() for m in self.messages],
            "turn": self.current_turn,
            "synthesis": self.get_synthesis(),
        }

    def save(self) -> str:
        """Save chat to file"""
        filepath = CHATS_DIR / f"{self.chat_id}.json"
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return str(filepath)


class GroupChatManager:
    """Manage group chat sessions"""

    def __init__(self):
        self.chats: Dict[str, GroupChat] = {}

    def create_chat(
        self,
        chat_id: str,
        topic: str,
        max_agents: int = 3,
        strategy: str = "round_robin",
    ) -> GroupChat:
        """Create new group chat"""
        chat = GroupChat(
            chat_id=chat_id,
            topic=topic,
            max_agents=max_agents,
            strategy=SpeakerSelection(strategy),
        )
        self.chats[chat_id] = chat
        return chat

    def get_chat(self, chat_id: str) -> Optional[GroupChat]:
        """Get chat by ID"""
        return self.chats.get(chat_id)

    def add_message(self, chat_id: str, speaker_id: str, content: str) -> Optional[Dict]:
        """Add message to chat"""
        chat = self.get_chat(chat_id)
        if not chat:
            return None

        msg = chat.add_message(speaker_id, content)
        return msg.to_dict() if msg else None

    def get_next_speaker(self, chat_id: str) -> Optional[str]:
        """Get next speaker"""
        chat = self.get_chat(chat_id)
        if not chat:
            return None

        speaker = chat.select_next_speaker()
        chat.advance_turn()
        return speaker

    def get_synthesis(self, chat_id: str) -> Optional[Dict]:
        """Get chat synthesis"""
        chat = self.get_chat(chat_id)
        return chat.get_synthesis() if chat else None

    def list_chats(self) -> List[str]:
        """List all chat IDs"""
        return list(self.chats.keys())


manager = GroupChatManager()


# MCP Tools (add to memory_server.py)

def create_group_chat(
    chat_id: str,
    topic: str,
    max_agents: int = 3,
    strategy: str = "round_robin",
) -> dict:
    """Create new group chat session"""
    chat = manager.create_chat(chat_id, topic, max_agents, strategy)
    return {"chat_id": chat.chat_id, "topic": chat.topic}


def add_agent_to_chat(
    chat_id: str,
    agent_id: str,
    agent_name: str,
    role: str = "participant",
    expertise: str = None,
) -> dict:
    """Add agent to group chat"""
    chat = manager.get_chat(chat_id)
    if not chat:
        return {"error": "Chat not found"}

    success = chat.add_agent(agent_id, agent_name, AgentRole(role), expertise)
    return {"agent_id": agent_id, "added": success}


def add_message_to_chat(chat_id: str, speaker_id: str, content: str) -> dict:
    """Add message to group chat"""
    msg = manager.add_message(chat_id, speaker_id, content)
    return msg or {"error": "Failed to add message"}


def get_next_speaker(chat_id: str) -> dict:
    """Get next speaker in turn order"""
    speaker = manager.get_next_speaker(chat_id)
    return {"speaker": speaker} if speaker else {"error": "No speakers available"}


def detect_consensus(chat_id: str) -> dict:
    """Check for consensus in chat"""
    synthesis = manager.get_synthesis(chat_id)
    if synthesis:
        return synthesis.get("consensus", {})
    return {"error": "Chat not found"}


def get_chat_synthesis(chat_id: str) -> dict:
    """Get synthesis of group chat"""
    synthesis = manager.get_synthesis(chat_id)
    return synthesis or {"error": "Chat not found"}


def should_halt_debate(chat_id: str) -> dict:
    """Check if debate should halt"""
    chat = manager.get_chat(chat_id)
    if not chat:
        return {"error": "Chat not found"}

    should_halt = chat.check_halt_conditions()
    return {
        "should_halt": should_halt,
        "reason": chat.halt_reason,
        "current_turn": chat.current_turn,
    }


if __name__ == "__main__":
    # Test group chat
    chat = manager.create_chat("test_chat", "How to improve code quality?", 3)

    # Add agents
    chat.add_agent("alice", "Alice", AgentRole.EXPERT, "backend")
    chat.add_agent("bob", "Bob", AgentRole.DEVIL_ADVOCATE, None)
    chat.add_agent("charlie", "Charlie", AgentRole.SYNTHESIZER, "architecture")

    # Simulate conversation
    manager.add_message("test_chat", "alice", "We should add more unit tests")
    speaker = manager.get_next_speaker("test_chat")
    print(f"Next speaker: {speaker}")

    manager.add_message("test_chat", speaker, "But that increases maintenance burden")
    synthesis = manager.get_synthesis("test_chat")
    print("Synthesis:", json.dumps(synthesis, indent=2))
