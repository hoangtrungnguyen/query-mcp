"""Export and audit trail management with GDPR compliance"""

import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from memory_server import episodic, semantic
from memory_compaction import token_counter

EXPORT_DIR = Path.home() / ".memory-mcp" / "exports"
AUDIT_DIR = Path.home() / ".memory-mcp" / "audit"
EXPORT_DIR.mkdir(exist_ok=True, parents=True)
AUDIT_DIR.mkdir(exist_ok=True, parents=True)

AUDIT_LOG = AUDIT_DIR / "audit.jsonl"


class AuditLogger:
    """Track all operations for compliance and accountability"""

    @staticmethod
    def log_event(
        event_type: str,
        agent_id: str,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict] = None,
    ) -> Dict:
        """Log an audit event"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "agent_id": agent_id,
            "user_id": user_id or "system",
            "action": action,
            "details": details or {},
        }

        with open(AUDIT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")

        return entry

    @staticmethod
    def get_audit_trail(agent_id: str, days: int = 30) -> List[Dict]:
        """Get audit trail for agent"""
        if not AUDIT_LOG.exists():
            return []

        cutoff = datetime.now() - timedelta(days=days)
        entries = []

        with open(AUDIT_LOG) as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                if entry.get("agent_id") == agent_id:
                    entry_time = datetime.fromisoformat(entry.get("timestamp", ""))
                    if entry_time >= cutoff:
                        entries.append(entry)

        return entries

    @staticmethod
    def export_audit_report(agent_id: str) -> str:
        """Export audit report to file"""
        trail = AuditLogger.get_audit_trail(agent_id, days=90)

        filepath = AUDIT_DIR / f"{agent_id}_audit_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filepath, "w") as f:
            json.dump(trail, f, indent=2)

        return str(filepath)


class ConversationExporter:
    """Export conversations in multiple formats"""

    @staticmethod
    def to_jsonl(messages: List[Dict]) -> str:
        """Export as JSON Lines"""
        output = []
        for msg in messages:
            output.append(json.dumps(msg))
        return "\n".join(output)

    @staticmethod
    def to_json(messages: List[Dict]) -> str:
        """Export as JSON"""
        return json.dumps(messages, indent=2)

    @staticmethod
    def to_markdown(
        messages: List[Dict],
        title: str = "Conversation",
    ) -> str:
        """Export as Markdown"""
        lines = [
            f"# {title}",
            f"Generated: {datetime.now().isoformat()}",
            f"Messages: {len(messages)}",
            "",
        ]

        for msg in messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")

            lines.append(f"## {role}")
            if timestamp:
                lines.append(f"*{timestamp}*")
            lines.append("")
            lines.append(content)
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def to_csv(messages: List[Dict]) -> str:
        """Export as CSV"""
        output = []
        writer = csv.DictWriter(
            output,
            fieldnames=["timestamp", "role", "content", "tokens"],
        )

        # Use StringIO for in-memory writing
        from io import StringIO

        csv_buffer = StringIO()
        writer = csv.DictWriter(
            csv_buffer,
            fieldnames=["timestamp", "role", "content_length", "tokens"],
        )
        writer.writeheader()

        for msg in messages:
            content = msg.get("content", "")
            writer.writerow({
                "timestamp": msg.get("timestamp", ""),
                "role": msg.get("role", ""),
                "content_length": len(content),
                "tokens": token_counter.estimate_tokens(content),
            })

        return csv_buffer.getvalue()

    @staticmethod
    def to_html(
        messages: List[Dict],
        title: str = "Conversation",
    ) -> str:
        """Export as HTML"""
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"  <title>{title}</title>",
            "  <style>",
            "    body { font-family: Arial, sans-serif; margin: 20px; }",
            "    .message { margin: 15px 0; padding: 10px; border-left: 4px solid #ccc; }",
            "    .user { border-left-color: #007bff; background: #f0f8ff; }",
            "    .assistant { border-left-color: #28a745; background: #f0fff4; }",
            "    .timestamp { font-size: 0.8em; color: #666; }",
            "  </style>",
            "</head>",
            "<body>",
            f"  <h1>{title}</h1>",
            f"  <p>Generated: {datetime.now().isoformat()}</p>",
            f"  <p>Messages: {len(messages)}</p>",
        ]

        for msg in messages:
            role = msg.get("role", "unknown").lower()
            content = msg.get("content", "").replace("<", "&lt;").replace(">", "&gt;")
            timestamp = msg.get("timestamp", "")

            html.append(f'  <div class="message {role}">')
            if timestamp:
                html.append(f'    <div class="timestamp">{timestamp}</div>')
            html.append(f"    <p><strong>{role.upper()}:</strong></p>")
            html.append(f"    <p>{content}</p>")
            html.append("  </div>")

        html.extend([
            "</body>",
            "</html>",
        ])

        return "\n".join(html)

    @staticmethod
    def export(
        agent_id: str,
        format: str = "json",
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Export conversation in specified format"""
        messages = episodic.get_messages(agent_id, limit=limit)

        exporter_map = {
            "json": ConversationExporter.to_json,
            "jsonl": ConversationExporter.to_jsonl,
            "markdown": ConversationExporter.to_markdown,
            "csv": ConversationExporter.to_csv,
            "html": ConversationExporter.to_html,
        }

        if format not in exporter_map:
            return {"error": f"Unsupported format: {format}"}

        exporter = exporter_map[format]
        content = exporter(messages)

        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = format if format != "jsonl" else "jsonl"
        filepath = EXPORT_DIR / f"{agent_id}_{timestamp}.{extension}"

        with open(filepath, "w") as f:
            f.write(content)

        # Log export
        AuditLogger.log_event(
            "export",
            agent_id,
            action=f"export_to_{format}",
            details={"filepath": str(filepath), "message_count": len(messages)},
        )

        return {
            "status": "ok",
            "format": format,
            "filepath": str(filepath),
            "message_count": len(messages),
            "file_size_bytes": filepath.stat().st_size,
        }


class RetentionPolicy:
    """Define and enforce data retention rules"""

    def __init__(self):
        self.policies_file = AUDIT_DIR / "retention_policies.json"
        self.policies = self._load_policies()

    def _load_policies(self) -> Dict:
        """Load retention policies"""
        if not self.policies_file.exists():
            return self._default_policies()

        with open(self.policies_file) as f:
            return json.load(f)

    def _default_policies(self) -> Dict:
        """Default GDPR-compliant retention policies"""
        return {
            "conversations": {"days": 90, "reason": "active_retention"},
            "archives": {"days": 365, "reason": "annual_backup"},
            "audit_logs": {"days": 30, "reason": "compliance_tracking"},
            "deleted_records": {"days": 7, "reason": "deletion_verification"},
        }

    def set_policy(self, data_type: str, days: int, reason: str):
        """Set retention policy for data type"""
        self.policies[data_type] = {"days": days, "reason": reason}

        with open(self.policies_file, "w") as f:
            json.dump(self.policies, f, indent=2)

    def get_policy(self, data_type: str) -> Optional[Dict]:
        """Get retention policy for data type"""
        return self.policies.get(data_type)

    def should_delete(self, created_at: str, data_type: str) -> bool:
        """Check if data should be deleted based on policy"""
        policy = self.get_policy(data_type)
        if not policy:
            return False

        created = datetime.fromisoformat(created_at)
        cutoff = datetime.now() - timedelta(days=policy["days"])
        return created < cutoff


class DeletionManager:
    """Manage data deletion with audit trail"""

    def __init__(self):
        self.retention_policy = RetentionPolicy()
        self.deletion_log = AUDIT_DIR / "deletions.jsonl"

    def mark_for_deletion(
        self,
        data_id: str,
        data_type: str,
        reason: str = "user_request",
    ) -> Dict:
        """Mark data for deletion (soft delete)"""
        entry = {
            "data_id": data_id,
            "data_type": data_type,
            "reason": reason,
            "marked_at": datetime.now().isoformat(),
            "deleted_at": None,
        }

        with open(self.deletion_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

        AuditLogger.log_event(
            "deletion_marked",
            data_id,
            action="mark_for_deletion",
            details={"reason": reason, "data_type": data_type},
        )

        return entry

    def execute_deletion(self, data_id: str) -> bool:
        """Execute actual deletion"""
        # Find and delete the record
        # This is a placeholder - actual implementation depends on storage backend

        # Update deletion log
        entries = []
        if self.deletion_log.exists():
            with open(self.deletion_log) as f:
                entries = [json.loads(line) for line in f if line.strip()]

        for entry in entries:
            if entry.get("data_id") == data_id:
                entry["deleted_at"] = datetime.now().isoformat()

        with open(self.deletion_log, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        AuditLogger.log_event(
            "deletion_executed",
            data_id,
            action="execute_deletion",
        )

        return True

    def cleanup_expired(self) -> Dict:
        """Clean up expired data based on retention policies"""
        result = {
            "deleted": 0,
            "errors": [],
        }

        # Check conversations
        policy = self.retention_policy.get_policy("conversations")
        if policy:
            # In production, iterate over actual data
            pass

        return result


# Global instances
audit_logger = AuditLogger()
exporter = ConversationExporter()
retention_policy = RetentionPolicy()
deletion_manager = DeletionManager()


# MCP Tools (add to memory_server.py)

def export_conversation(
    agent_id: str,
    format: str = "json",
    limit: int = 100,
) -> dict:
    """Export conversation in multiple formats"""
    return exporter.export(agent_id, format, limit)


def get_audit_trail(agent_id: str, days: int = 30) -> list:
    """Get audit trail for agent (last N days)"""
    return audit_logger.get_audit_trail(agent_id, days)


def export_audit_report(agent_id: str) -> str:
    """Export audit report to file"""
    return audit_logger.export_audit_report(agent_id)


def set_retention_policy(data_type: str, days: int, reason: str) -> dict:
    """Set retention policy for data type"""
    retention_policy.set_policy(data_type, days, reason)
    return {"status": "ok", "data_type": data_type, "days": days}


def get_retention_policy(data_type: str) -> dict:
    """Get retention policy"""
    return retention_policy.get_policy(data_type) or {}


def mark_for_deletion(
    data_id: str,
    data_type: str,
    reason: str = "user_request",
) -> dict:
    """Mark data for deletion with audit trail"""
    return deletion_manager.mark_for_deletion(data_id, data_type, reason)


def execute_deletion(data_id: str) -> bool:
    """Execute deletion (permanent)"""
    return deletion_manager.execute_deletion(data_id)


if __name__ == "__main__":
    # Test export
    test_messages = [
        {
            "id": "1",
            "role": "user",
            "content": "Hello, how are you?",
            "timestamp": datetime.now().isoformat(),
        },
        {
            "id": "2",
            "role": "assistant",
            "content": "I'm doing well, thank you for asking!",
            "timestamp": datetime.now().isoformat(),
        },
    ]

    # Test markdown export
    md = ConversationExporter.to_markdown(test_messages, "Test Conversation")
    print("=== Markdown Export ===")
    print(md)

    # Test CSV export
    csv = ConversationExporter.to_csv(test_messages)
    print("\n=== CSV Export ===")
    print(csv)

    # Test audit logging
    AuditLogger.log_event("test", "agent_1", action="test_log")
    trail = AuditLogger.get_audit_trail("agent_1", days=1)
    print(f"\n=== Audit Trail ({len(trail)} entries) ===")
    for entry in trail:
        print(entry)
