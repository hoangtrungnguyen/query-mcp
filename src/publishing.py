"""Conversation publishing, sharing, and distribution framework"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import hashlib

PUBLISHING_DIR = Path.home() / ".memory-mcp" / "publishing"
PUBLISHING_DIR.mkdir(exist_ok=True, parents=True)


class ShareLevel(Enum):
    """Access levels for sharing"""
    PRIVATE = "private"  # Only owner
    LINK_ONLY = "link_only"  # Anyone with link
    PUBLIC = "public"  # Searchable, discoverable
    ORGANIZATION = "organization"  # Organization members


class ExportFormat(Enum):
    """Export formats"""
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    WORD = "word"
    PLAIN_TEXT = "plain_text"


class PublicationStatus(Enum):
    """Publication workflow status"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    UNLISTED = "unlisted"


@dataclass
class ShareLink:
    """Link for sharing conversation"""
    link_id: str
    conversation_id: str
    access_token: str
    share_level: ShareLevel
    created_by: str
    created_at: str
    expires_at: Optional[str] = None
    access_count: int = 0
    password_protected: bool = False
    comment_enabled: bool = True

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def is_expired(self) -> bool:
        """Check if link expired"""
        if not self.expires_at:
            return False
        return datetime.fromisoformat(self.expires_at) < datetime.now()

    def to_dict(self) -> Dict:
        """Serialize link"""
        return {
            "link_id": self.link_id,
            "conversation_id": self.conversation_id,
            "share_level": self.share_level.value,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "access_count": self.access_count,
            "comment_enabled": self.comment_enabled,
            "expired": self.is_expired(),
        }


@dataclass
class PublishedVersion:
    """Published version of conversation"""
    version_id: str
    conversation_id: str
    title: str
    description: str
    published_by: str
    published_at: str
    content_hash: str
    status: PublicationStatus
    attribution: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Serialize version"""
        return {
            "version_id": self.version_id,
            "conversation_id": self.conversation_id,
            "title": self.title,
            "description": self.description,
            "published_by": self.published_by,
            "published_at": self.published_at,
            "status": self.status.value,
            "attribution": self.attribution,
            "metadata": self.metadata,
        }


@dataclass
class PublishedComment:
    """Comment on published conversation"""
    comment_id: str
    version_id: str
    author_id: str
    author_name: str
    content: str
    created_at: str = ""
    replies: List[str] = field(default_factory=list)
    likes: int = 0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize comment"""
        return {
            "comment_id": self.comment_id,
            "author": self.author_name,
            "content": self.content,
            "created_at": self.created_at,
            "replies": len(self.replies),
            "likes": self.likes,
        }


class RedactionEngine:
    """Handle selective redaction of sensitive content"""

    REDACTION_PATTERNS = {
        "email": r"[\w\.-]+@[\w\.-]+\.\w+",
        "phone": r"\+?1?\s*\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}",
        "ssn": r"\d{3}-\d{2}-\d{4}",
        "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    }

    @staticmethod
    def identify_sensitive(content: str) -> List[Dict]:
        """Identify sensitive content"""
        import re
        sensitive = []

        for pii_type, pattern in RedactionEngine.REDACTION_PATTERNS.items():
            for match in re.finditer(pattern, content):
                sensitive.append({
                    "type": pii_type,
                    "value": match.group(),
                    "position": match.start(),
                    "length": len(match.group()),
                })

        return sensitive

    @staticmethod
    def redact(content: str, sensitive_items: List[Dict]) -> str:
        """Redact sensitive content"""
        for item in sorted(sensitive_items, key=lambda x: x["position"], reverse=True):
            start = item["position"]
            end = start + item["length"]
            content = content[:start] + f"[{item['type'].upper()}]" + content[end:]

        return content


class PublishingManager:
    """Manage conversation publishing and sharing"""

    def __init__(self):
        self.share_links: Dict[str, ShareLink] = {}
        self.published_versions: Dict[str, PublishedVersion] = {}
        self.comments: Dict[str, PublishedComment] = {}
        self.redaction_engine = RedactionEngine()

    def create_share_link(
        self,
        conversation_id: str,
        created_by: str,
        share_level: ShareLevel,
        expires_in_days: Optional[int] = None,
    ) -> ShareLink:
        """Create share link"""
        link_id = f"link_{hashlib.md5((conversation_id + str(datetime.now())).encode()).hexdigest()[:8]}"
        access_token = hashlib.sha256(link_id.encode()).hexdigest()

        expires_at = None
        if expires_in_days:
            expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()

        link = ShareLink(
            link_id=link_id,
            conversation_id=conversation_id,
            access_token=access_token,
            share_level=share_level,
            created_by=created_by,
            created_at=datetime.now().isoformat(),
            expires_at=expires_at,
        )

        self.share_links[link_id] = link
        return link

    def publish_conversation(
        self,
        conversation_id: str,
        title: str,
        description: str,
        published_by: str,
        content_hash: str,
        status: PublicationStatus = PublicationStatus.PUBLISHED,
    ) -> PublishedVersion:
        """Publish conversation version"""
        version_id = f"v_{len([v for v in self.published_versions.values() if v.conversation_id == conversation_id]) + 1}"

        version = PublishedVersion(
            version_id=version_id,
            conversation_id=conversation_id,
            title=title,
            description=description,
            published_by=published_by,
            published_at=datetime.now().isoformat(),
            content_hash=content_hash,
            status=status,
            attribution={
                "author": published_by,
                "license": "CC-BY-4.0",
                "attribution_required": True,
            },
        )

        self.published_versions[version_id] = version
        return version

    def add_comment(
        self,
        version_id: str,
        author_id: str,
        author_name: str,
        content: str,
    ) -> PublishedComment:
        """Add comment to published version"""
        comment = PublishedComment(
            comment_id=f"comment_{len(self.comments)}",
            version_id=version_id,
            author_id=author_id,
            author_name=author_name,
            content=content,
        )

        self.comments[comment.comment_id] = comment
        return comment

    def prepare_export(
        self,
        conversation_id: str,
        format: ExportFormat,
        include_metadata: bool = True,
        redact_pii: bool = True,
    ) -> Dict[str, Any]:
        """Prepare conversation for export"""
        versions = [
            v for v in self.published_versions.values()
            if v.conversation_id == conversation_id
        ]

        if not versions:
            return {"error": "No published versions"}

        latest = versions[-1]

        # Build export
        export_data = {
            "title": latest.title,
            "description": latest.description,
            "published_by": latest.published_by,
            "published_at": latest.published_at,
            "format": format.value,
        }

        if include_metadata:
            export_data["attribution"] = latest.attribution
            export_data["metadata"] = latest.metadata

        # Add comment count
        version_comments = [
            c for c in self.comments.values()
            if c.version_id == latest.version_id
        ]
        export_data["comment_count"] = len(version_comments)

        return {
            "export_data": export_data,
            "format": format.value,
            "ready": True,
        }

    def get_publication_history(self, conversation_id: str) -> List[Dict]:
        """Get publication history"""
        versions = [
            v for v in self.published_versions.values()
            if v.conversation_id == conversation_id
        ]

        return [v.to_dict() for v in sorted(
            versions,
            key=lambda x: x.published_at,
            reverse=True,
        )]

    def get_sharing_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get sharing summary"""
        links = [
            l for l in self.share_links.values()
            if l.conversation_id == conversation_id
        ]

        versions = self.get_publication_history(conversation_id)

        total_access = sum(l.access_count for l in links)

        return {
            "conversation_id": conversation_id,
            "share_links": len(links),
            "active_links": sum(1 for l in links if not l.is_expired()),
            "total_accesses": total_access,
            "published_versions": len(versions),
            "links": [l.to_dict() for l in links],
        }


# Global manager
publishing_manager = PublishingManager()


# MCP Tools (add to memory_server.py)

def create_share_link(
    conversation_id: str,
    created_by: str,
    share_level: str,
    expires_in_days: int = None,
) -> dict:
    """Create share link"""
    link = publishing_manager.create_share_link(
        conversation_id,
        created_by,
        ShareLevel(share_level),
        expires_in_days,
    )
    return {
        "link_id": link.link_id,
        "access_token": link.access_token,
        "share_level": link.share_level.value,
        "created": True,
    }


def publish_conversation(
    conversation_id: str,
    title: str,
    description: str,
    published_by: str,
    content_hash: str,
) -> dict:
    """Publish conversation"""
    version = publishing_manager.publish_conversation(
        conversation_id,
        title,
        description,
        published_by,
        content_hash,
    )
    return version.to_dict()


def add_published_comment(
    version_id: str,
    author_id: str,
    author_name: str,
    content: str,
) -> dict:
    """Add comment"""
    comment = publishing_manager.add_comment(
        version_id,
        author_id,
        author_name,
        content,
    )
    return comment.to_dict()


def prepare_conversation_export(
    conversation_id: str,
    format: str,
    redact_pii: bool = True,
) -> dict:
    """Prepare export"""
    return publishing_manager.prepare_export(
        conversation_id,
        ExportFormat(format),
        redact_pii=redact_pii,
    )


def get_publication_history(conversation_id: str) -> dict:
    """Get publication history"""
    versions = publishing_manager.get_publication_history(conversation_id)
    return {
        "conversation_id": conversation_id,
        "versions": versions,
        "count": len(versions),
    }


def get_sharing_summary(conversation_id: str) -> dict:
    """Get sharing summary"""
    return publishing_manager.get_sharing_summary(conversation_id)


if __name__ == "__main__":
    # Test publishing
    manager = PublishingManager()

    # Create share link
    link = manager.create_share_link(
        "conv_1",
        "user_1",
        ShareLevel.PUBLIC,
        expires_in_days=7,
    )
    print(f"Share link: {link.link_id}")

    # Publish
    version = manager.publish_conversation(
        "conv_1",
        "Discussion on AI",
        "Conversation about AI safety",
        "user_1",
        "hash_123",
    )
    print(f"Published: {version.version_id}")

    # Add comment
    comment = manager.add_comment(
        version.version_id,
        "user_2",
        "Bob",
        "Great discussion!",
    )
    print(f"Comment: {comment.comment_id}")

    # Get summary
    summary = manager.get_sharing_summary("conv_1")
    print(f"Summary: {json.dumps(summary, indent=2)}")
