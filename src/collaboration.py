"""Real-time collaboration for multi-user conversations"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum

COLLAB_DIR = Path.home() / ".memory-mcp" / "collaboration"
COLLAB_DIR.mkdir(exist_ok=True, parents=True)


class UserRole(Enum):
    """User roles in collaboration"""
    OWNER = "owner"
    EDITOR = "editor"
    COMMENTER = "commenter"
    VIEWER = "viewer"


class PresenceStatus(Enum):
    """User presence states"""
    ONLINE = "online"
    IDLE = "idle"
    OFFLINE = "offline"
    AWAY = "away"


class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    LAST_WRITE_WINS = "last_write_wins"
    OPERATIONAL_TRANSFORM = "operational_transform"
    CRDT = "crdt"  # Conflict-free Replicated Data Type
    MANUAL = "manual"


@dataclass
class UserPresence:
    """Track user presence in session"""
    user_id: str
    username: str
    status: PresenceStatus
    cursor_position: int = 0  # Position in conversation
    last_seen: str = ""
    typing: bool = False
    color: str = "#000000"  # User color for collab UI

    def __post_init__(self):
        if not self.last_seen:
            self.last_seen = datetime.now().isoformat()

    def is_active(self, timeout_minutes: int = 15) -> bool:
        """Check if user is actively present"""
        if self.status == PresenceStatus.OFFLINE:
            return False
        if self.status == PresenceStatus.IDLE:
            idle_time = (datetime.now() - datetime.fromisoformat(self.last_seen)).total_seconds()
            return idle_time < timeout_minutes * 60
        return True

    def to_dict(self) -> Dict:
        """Serialize presence"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "status": self.status.value,
            "cursor_position": self.cursor_position,
            "typing": self.typing,
            "color": self.color,
            "active": self.is_active(),
        }


@dataclass
class Notification:
    """Collaboration notification"""
    notification_id: str
    user_id: str
    event_type: str  # "user_joined", "message_added", "cursor_moved"
    message: str
    actor_user_id: str
    created_at: str = ""
    read: bool = False

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize notification"""
        return {
            "notification_id": self.notification_id,
            "event_type": self.event_type,
            "message": self.message,
            "actor": self.actor_user_id,
            "created_at": self.created_at,
            "read": self.read,
        }


@dataclass
class ConflictResolutionEvent:
    """Recorded conflict resolution"""
    event_id: str
    conflicting_edits: List[Dict]
    resolution_strategy: ConflictResolution
    chosen_edit: str
    rejected_edits: List[str]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize event"""
        return {
            "event_id": self.event_id,
            "resolution_strategy": self.resolution_strategy.value,
            "chosen_edit": self.chosen_edit,
            "rejected_edits": self.rejected_edits,
            "timestamp": self.timestamp,
        }


class CollaborationSession:
    """Session for multi-user collaboration"""

    def __init__(self, session_id: str, conversation_id: str):
        self.session_id = session_id
        self.conversation_id = conversation_id
        self.participants: Dict[str, UserPresence] = {}
        self.permissions: Dict[str, UserRole] = {}
        self.notifications: List[Notification] = []
        self.conflict_history: List[ConflictResolutionEvent] = []
        self.created_at = datetime.now().isoformat()
        self.active = True

    def add_participant(
        self,
        user_id: str,
        username: str,
        role: UserRole,
    ) -> UserPresence:
        """Add user to collaboration session"""
        presence = UserPresence(
            user_id=user_id,
            username=username,
            status=PresenceStatus.ONLINE,
            color=self._assign_color(user_id),
        )

        self.participants[user_id] = presence
        self.permissions[user_id] = role

        # Notify others
        self._broadcast_notification(
            "user_joined",
            f"{username} joined the conversation",
            user_id,
        )

        return presence

    def remove_participant(self, user_id: str) -> bool:
        """Remove user from session"""
        if user_id not in self.participants:
            return False

        username = self.participants[user_id].username
        del self.participants[user_id]
        del self.permissions[user_id]

        self._broadcast_notification(
            "user_left",
            f"{username} left the conversation",
            user_id,
        )

        return True

    def update_presence(
        self,
        user_id: str,
        status: PresenceStatus,
        cursor_position: int = None,
        typing: bool = False,
    ) -> bool:
        """Update user presence"""
        if user_id not in self.participants:
            return False

        presence = self.participants[user_id]
        presence.status = status
        presence.last_seen = datetime.now().isoformat()

        if cursor_position is not None:
            presence.cursor_position = cursor_position

        presence.typing = typing

        return True

    def can_edit(self, user_id: str) -> bool:
        """Check if user can edit"""
        role = self.permissions.get(user_id)
        return role in [UserRole.OWNER, UserRole.EDITOR]

    def can_comment(self, user_id: str) -> bool:
        """Check if user can comment"""
        role = self.permissions.get(user_id)
        return role in [UserRole.OWNER, UserRole.EDITOR, UserRole.COMMENTER]

    def record_conflict(
        self,
        conflicting_edits: List[Dict],
        resolution: ConflictResolution,
        chosen_edit: str,
    ) -> ConflictResolutionEvent:
        """Record conflict resolution"""
        event = ConflictResolutionEvent(
            event_id=f"conflict_{len(self.conflict_history)}",
            conflicting_edits=conflicting_edits,
            resolution_strategy=resolution,
            chosen_edit=chosen_edit,
            rejected_edits=[
                e.get("user_id") for e in conflicting_edits
                if e != chosen_edit
            ],
        )

        self.conflict_history.append(event)

        self._broadcast_notification(
            "conflict_resolved",
            "Concurrent edits resolved automatically",
            "system",
        )

        return event

    def get_active_participants(self) -> List[UserPresence]:
        """Get actively present users"""
        return [p for p in self.participants.values() if p.is_active()]

    def get_unread_notifications(self, user_id: str) -> List[Notification]:
        """Get unread notifications for user"""
        return [
            n for n in self.notifications
            if n.user_id == user_id and not n.read
        ]

    def _broadcast_notification(
        self,
        event_type: str,
        message: str,
        actor_user_id: str,
    ):
        """Send notification to all participants"""
        for user_id in self.participants:
            notification = Notification(
                notification_id=f"notif_{len(self.notifications)}",
                user_id=user_id,
                event_type=event_type,
                message=message,
                actor_user_id=actor_user_id,
            )
            self.notifications.append(notification)

    def _assign_color(self, user_id: str) -> str:
        """Assign color to user"""
        colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
            "#F7DC6F", "#BB8FCE", "#85C1E2",
        ]
        return colors[hash(user_id) % len(colors)]

    def to_dict(self) -> Dict:
        """Serialize session"""
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "active_participants": len(self.get_active_participants()),
            "total_participants": len(self.participants),
            "participants": [p.to_dict() for p in self.participants.values()],
            "notifications_count": len(self.notifications),
            "conflicts_resolved": len(self.conflict_history),
            "created_at": self.created_at,
        }


class CollaborationManager:
    """Manage collaboration sessions"""

    def __init__(self):
        self.sessions: Dict[str, CollaborationSession] = {}
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> session_ids

    def create_session(
        self,
        session_id: str,
        conversation_id: str,
    ) -> CollaborationSession:
        """Create collaboration session"""
        session = CollaborationSession(session_id, conversation_id)
        self.sessions[session_id] = session
        return session

    def join_session(
        self,
        session_id: str,
        user_id: str,
        username: str,
        role: UserRole,
    ) -> Optional[CollaborationSession]:
        """Join existing session"""
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]
        session.add_participant(user_id, username, role)

        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(session_id)

        return session

    def leave_session(self, session_id: str, user_id: str) -> bool:
        """Leave session"""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        success = session.remove_participant(user_id)

        if success and user_id in self.user_sessions:
            self.user_sessions[user_id].discard(session_id)

        return success

    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """Get session status"""
        if session_id not in self.sessions:
            return None

        return self.sessions[session_id].to_dict()

    def get_user_sessions(self, user_id: str) -> List[str]:
        """Get all sessions user is in"""
        return list(self.user_sessions.get(user_id, set()))

    def broadcast_edit(
        self,
        session_id: str,
        user_id: str,
        edit: Dict,
    ) -> bool:
        """Broadcast edit to all participants"""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        if not session.can_edit(user_id):
            return False

        session._broadcast_notification(
            "edit_made",
            f"User made an edit",
            user_id,
        )

        return True


# Global manager
collab_manager = CollaborationManager()


# MCP Tools (add to memory_server.py)

def create_collaboration_session(
    session_id: str,
    conversation_id: str,
) -> dict:
    """Create collaboration session"""
    session = collab_manager.create_session(session_id, conversation_id)
    return {
        "session_id": session.session_id,
        "conversation_id": conversation_id,
        "created": True,
    }


def join_collaboration_session(
    session_id: str,
    user_id: str,
    username: str,
    role: str = "editor",
) -> dict:
    """Join collaboration session"""
    session = collab_manager.join_session(
        session_id,
        user_id,
        username,
        UserRole(role),
    )
    return (
        session.to_dict()
        if session
        else {"error": "Session not found"}
    )


def leave_collaboration_session(session_id: str, user_id: str) -> dict:
    """Leave collaboration session"""
    success = collab_manager.leave_session(session_id, user_id)
    return {"left": success}


def update_user_presence(
    session_id: str,
    user_id: str,
    status: str,
    cursor_position: int = None,
) -> dict:
    """Update user presence"""
    if session_id not in collab_manager.sessions:
        return {"error": "Session not found"}

    session = collab_manager.sessions[session_id]
    success = session.update_presence(
        user_id,
        PresenceStatus(status),
        cursor_position,
    )
    return {"updated": success}


def get_collaboration_session_status(session_id: str) -> dict:
    """Get session status"""
    status = collab_manager.get_session_status(session_id)
    return status or {"error": "Session not found"}


def get_user_notifications(session_id: str, user_id: str) -> dict:
    """Get user notifications"""
    if session_id not in collab_manager.sessions:
        return {"error": "Session not found"}

    session = collab_manager.sessions[session_id]
    notifications = session.get_unread_notifications(user_id)
    return {
        "notifications": [n.to_dict() for n in notifications],
        "count": len(notifications),
    }


if __name__ == "__main__":
    # Test collaboration
    manager = CollaborationManager()

    # Create session
    session = manager.create_session("sess_1", "conv_1")
    print(f"Session created: {session.session_id}")

    # Join users
    session.add_participant("user_1", "Alice", UserRole.OWNER)
    session.add_participant("user_2", "Bob", UserRole.EDITOR)

    # Update presence
    session.update_presence("user_1", PresenceStatus.ONLINE, cursor_position=10)

    # Get status
    status = manager.get_session_status("sess_1")
    print(f"Status: {json.dumps(status, indent=2)}")
