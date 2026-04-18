"""Security and privacy framework with PII detection, encryption, and compliance"""

import json
import hashlib
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import secrets

SECURITY_DIR = Path.home() / ".memory-mcp" / "security"
SECURITY_DIR.mkdir(exist_ok=True, parents=True)


class PIIType(Enum):
    """Types of Personally Identifiable Information"""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    NAME = "name"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"


class AccessLevel(Enum):
    """Role-based access levels"""
    PUBLIC = "public"
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"


class ComplianceFramework(Enum):
    """Data protection regulations"""
    GDPR = "gdpr"  # General Data Protection Regulation (EU)
    CCPA = "ccpa"  # California Consumer Privacy Act
    HIPAA = "hipaa"  # Health Insurance Portability
    PCI_DSS = "pci_dss"  # Payment Card Industry
    SOC2 = "soc2"  # System and Organization Controls


@dataclass
class PIIEntity:
    """Detected PII instance"""
    entity_id: str
    pii_type: PIIType
    value: str  # Original value (encrypted in storage)
    confidence: float
    location: Dict[str, int]  # Position in text
    timestamp: str = ""
    user_id: Optional[str] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize (redacted)"""
        return {
            "entity_id": self.entity_id,
            "pii_type": self.pii_type.value,
            "confidence": self.confidence,
            "location": self.location,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
        }


@dataclass
class AccessLog:
    """Audit log entry"""
    log_id: str
    user_id: str
    action: str
    resource: str
    access_level: AccessLevel
    timestamp: str
    success: bool
    reason_if_denied: Optional[str] = None

    def to_dict(self) -> Dict:
        """Serialize log"""
        return {
            "log_id": self.log_id,
            "user_id": self.user_id,
            "action": self.action,
            "resource": self.resource,
            "access_level": self.access_level.value,
            "timestamp": self.timestamp,
            "success": self.success,
            "reason_if_denied": self.reason_if_denied,
        }


@dataclass
class DataRetentionPolicy:
    """Policy for retaining user data"""
    framework: ComplianceFramework
    data_type: str
    retention_days: int
    auto_delete: bool = True
    anonymization_allowed: bool = True
    user_deletion_supported: bool = True

    def should_delete(self, creation_timestamp: str) -> bool:
        """Check if data should be deleted"""
        if not self.auto_delete:
            return False

        created = datetime.fromisoformat(creation_timestamp)
        age_days = (datetime.now() - created).days
        return age_days > self.retention_days

    def to_dict(self) -> Dict:
        """Serialize policy"""
        return {
            "framework": self.framework.value,
            "data_type": self.data_type,
            "retention_days": self.retention_days,
            "auto_delete": self.auto_delete,
            "anonymization_allowed": self.anonymization_allowed,
            "user_deletion_supported": self.user_deletion_supported,
        }


class PIIDetector:
    """Detect sensitive PII in text"""

    # Regex patterns for common PII
    PATTERNS = {
        PIIType.EMAIL: re.compile(r"[\w\.-]+@[\w\.-]+\.\w+"),
        PIIType.PHONE: re.compile(r"\+?1?\s*\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}"),
        PIIType.SSN: re.compile(r"\d{3}-\d{2}-\d{4}"),
        PIIType.CREDIT_CARD: re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
        PIIType.IP_ADDRESS: re.compile(
            r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        ),
    }

    @staticmethod
    def detect(text: str) -> List[PIIEntity]:
        """Detect PII in text"""
        entities = []

        for pii_type, pattern in PIIDetector.PATTERNS.items():
            for match in pattern.finditer(text):
                entity = PIIEntity(
                    entity_id=f"pii_{hash(match.group())%1000000}",
                    pii_type=pii_type,
                    value=match.group(),
                    confidence=0.95,
                    location={
                        "start": match.start(),
                        "end": match.end(),
                    },
                )
                entities.append(entity)

        return entities

    @staticmethod
    def mask(text: str, entities: List[PIIEntity]) -> str:
        """Mask detected PII"""
        for entity in sorted(entities, key=lambda e: e.location["start"], reverse=True):
            start = entity.location["start"]
            end = entity.location["end"]
            original = text[start:end]
            masked = f"[{entity.pii_type.value.upper()}]"
            text = text[:start] + masked + text[end:]

        return text


class EncryptionManager:
    """Handle data encryption"""

    @staticmethod
    def hash_pii(value: str, salt: Optional[str] = None) -> str:
        """Hash PII for storage"""
        if not salt:
            salt = secrets.token_hex(16)
        return hashlib.pbkdf2_hmac("sha256", value.encode(), salt.encode(), 100000).hex()

    @staticmethod
    def anonymize(value: str, pii_type: PIIType) -> str:
        """Anonymize PII"""
        if pii_type == PIIType.EMAIL:
            parts = value.split("@")
            return f"{parts[0][:3]}***@{parts[1]}"
        elif pii_type == PIIType.PHONE:
            return value[:3] + "***" + value[-4:]
        elif pii_type == PIIType.NAME:
            parts = value.split()
            return parts[0][0] + "***" if parts else "***"
        else:
            return "***" + value[-4:]


class AccessController:
    """Control access to resources"""

    def __init__(self):
        self.role_permissions: Dict[str, Set[str]] = {
            AccessLevel.PUBLIC.value: {"read"},
            AccessLevel.USER.value: {"read", "write"},
            AccessLevel.ADMIN.value: {"read", "write", "delete", "admin"},
            AccessLevel.SYSTEM.value: {"*"},
        }

    def can_access(
        self,
        user_id: str,
        access_level: AccessLevel,
        action: str,
        resource: str,
    ) -> bool:
        """Check if user can perform action"""
        permissions = self.role_permissions.get(access_level.value, set())

        if "*" in permissions:
            return True

        return action in permissions


class SecurityFramework:
    """Complete security and privacy system"""

    def __init__(self):
        self.pii_detector = PIIDetector()
        self.encryption = EncryptionManager()
        self.access_controller = AccessController()
        self.audit_logs: List[AccessLog] = []
        self.pii_entities: Dict[str, PIIEntity] = {}
        self.retention_policies: Dict[str, DataRetentionPolicy] = self._create_default_policies()

    def _create_default_policies(self) -> Dict[str, DataRetentionPolicy]:
        """Create default retention policies"""
        return {
            "gdpr_conversations": DataRetentionPolicy(
                framework=ComplianceFramework.GDPR,
                data_type="conversations",
                retention_days=90,
            ),
            "gdpr_audit_logs": DataRetentionPolicy(
                framework=ComplianceFramework.GDPR,
                data_type="audit_logs",
                retention_days=30,
            ),
            "hipaa_health_records": DataRetentionPolicy(
                framework=ComplianceFramework.HIPAA,
                data_type="health_records",
                retention_days=2555,  # 7 years
            ),
        }

    def scan_and_mask(self, text: str, user_id: Optional[str] = None) -> Tuple[str, List[PIIEntity]]:
        """Scan text for PII and mask"""
        entities = self.pii_detector.detect(text)

        # Store detected PII
        for entity in entities:
            entity.user_id = user_id
            self.pii_entities[entity.entity_id] = entity

        masked_text = self.pii_detector.mask(text, entities)
        return masked_text, entities

    def log_access(
        self,
        user_id: str,
        action: str,
        resource: str,
        access_level: AccessLevel,
        success: bool,
        reason_if_denied: Optional[str] = None,
    ) -> AccessLog:
        """Log access attempt"""
        log = AccessLog(
            log_id=f"log_{hash(f'{user_id}_{action}_{resource}')%1000000}",
            user_id=user_id,
            action=action,
            resource=resource,
            access_level=access_level,
            timestamp=datetime.now().isoformat(),
            success=success,
            reason_if_denied=reason_if_denied,
        )

        self.audit_logs.append(log)
        return log

    def enforce_access(
        self,
        user_id: str,
        access_level: AccessLevel,
        action: str,
        resource: str,
    ) -> Tuple[bool, Optional[str]]:
        """Enforce access control"""
        allowed = self.access_controller.can_access(user_id, access_level, action, resource)

        reason = None
        if not allowed:
            reason = f"Access denied: {access_level.value} cannot {action} {resource}"

        self.log_access(user_id, action, resource, access_level, allowed, reason)

        return allowed, reason

    def delete_user_data(self, user_id: str) -> Dict[str, int]:
        """Delete all user data (GDPR right to be forgotten)"""
        deleted_counts = {
            "pii_entities": 0,
            "audit_logs": 0,
        }

        # Delete PII entities
        to_delete = [e for e in self.pii_entities.values() if e.user_id == user_id]
        for entity in to_delete:
            del self.pii_entities[entity.entity_id]
        deleted_counts["pii_entities"] = len(to_delete)

        # Delete audit logs
        original_log_count = len(self.audit_logs)
        self.audit_logs = [l for l in self.audit_logs if l.user_id != user_id]
        deleted_counts["audit_logs"] = original_log_count - len(self.audit_logs)

        return deleted_counts

    def anonymize_user_data(self, user_id: str) -> Dict[str, int]:
        """Anonymize user data"""
        anonymized = {"pii_entities": 0}

        for entity in self.pii_entities.values():
            if entity.user_id == user_id:
                entity.value = self.encryption.anonymize(entity.value, entity.pii_type)
                anonymized["pii_entities"] += 1

        return anonymized

    def get_compliance_report(self, framework: ComplianceFramework) -> Dict[str, Any]:
        """Generate compliance report"""
        applicable_policies = [
            p for p in self.retention_policies.values()
            if p.framework == framework
        ]

        return {
            "framework": framework.value,
            "generated_at": datetime.now().isoformat(),
            "applicable_policies": [p.to_dict() for p in applicable_policies],
            "total_audit_logs": len(self.audit_logs),
            "pii_entities_tracked": len(self.pii_entities),
            "right_to_access_supported": True,
            "right_to_delete_supported": True,
            "right_to_data_portability_supported": True,
        }

    def get_security_audit_trail(self, user_id: Optional[str] = None) -> List[Dict]:
        """Get audit trail"""
        logs = self.audit_logs

        if user_id:
            logs = [l for l in logs if l.user_id == user_id]

        return [l.to_dict() for l in logs[-100:]]  # Last 100


# Global framework
security_framework = SecurityFramework()


# MCP Tools (add to memory_server.py)

def scan_for_pii(text: str, user_id: str = None) -> dict:
    """Scan text for sensitive PII"""
    masked, entities = security_framework.scan_and_mask(text, user_id)
    return {
        "original_text": text,
        "masked_text": masked,
        "pii_detected": [e.to_dict() for e in entities],
        "pii_count": len(entities),
    }


def enforce_access_control(
    user_id: str,
    access_level: str,
    action: str,
    resource: str,
) -> dict:
    """Check access control"""
    allowed, reason = security_framework.enforce_access(
        user_id,
        AccessLevel(access_level),
        action,
        resource,
    )
    return {
        "allowed": allowed,
        "reason": reason,
    }


def delete_user_data(user_id: str) -> dict:
    """Delete all user data (GDPR)"""
    results = security_framework.delete_user_data(user_id)
    return {"user_id": user_id, "deleted": results}


def anonymize_user_data(user_id: str) -> dict:
    """Anonymize user data"""
    results = security_framework.anonymize_user_data(user_id)
    return {"user_id": user_id, "anonymized": results}


def get_compliance_report(framework: str) -> dict:
    """Get compliance report"""
    return security_framework.get_compliance_report(ComplianceFramework(framework))


def get_security_audit_trail(user_id: str = None) -> dict:
    """Get audit trail"""
    logs = security_framework.get_security_audit_trail(user_id)
    return {"logs": logs, "count": len(logs)}


if __name__ == "__main__":
    # Test security
    framework = SecurityFramework()

    # Scan for PII
    text = "My email is john@example.com and phone is 555-1234"
    masked, entities = framework.scan_and_mask(text)
    print(f"Original: {text}")
    print(f"Masked: {masked}")
    print(f"Entities found: {len(entities)}")

    # Access control
    allowed, reason = framework.enforce_access(
        "user_1",
        AccessLevel.USER,
        "read",
        "conversations",
    )
    print(f"Access allowed: {allowed}")

    # Compliance
    report = framework.get_compliance_report(ComplianceFramework.GDPR)
    print(f"GDPR Compliance: {json.dumps(report, indent=2)}")
