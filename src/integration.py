"""Integration framework for external APIs, CRM, ERP, and third-party platforms"""

import json
import hmac
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

INTEGRATION_DIR = Path.home() / ".memory-mcp" / "integrations"
INTEGRATION_DIR.mkdir(exist_ok=True, parents=True)


class IntegrationPlatform(Enum):
    """Supported external platforms"""
    SALESFORCE = "salesforce"  # CRM
    HUBSPOT = "hubspot"  # CRM/Marketing
    SLACK = "slack"  # Communication
    JIRA = "jira"  # Issue tracking
    STRIPE = "stripe"  # Payment
    TWILIO = "twilio"  # Communications
    GITHUB = "github"  # Repository
    NOTION = "notion"  # Knowledge base
    ZAPIER = "zapier"  # Automation
    CUSTOM = "custom"  # Custom API


class AuthType(Enum):
    """Authentication mechanisms"""
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC_AUTH = "basic_auth"
    JWT = "jwt"
    WEBHOOK_SECRET = "webhook_secret"


class TransactionStatus(Enum):
    """Transaction lifecycle states"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    TIMEOUT = "timeout"


@dataclass
class AuthCredential:
    """Authentication credential"""
    auth_type: AuthType
    token: str
    expires_at: Optional[str] = None
    refresh_token: Optional[str] = None
    scopes: List[str] = None

    def __post_init__(self):
        if self.scopes is None:
            self.scopes = []

    def is_expired(self) -> bool:
        """Check if credential expired"""
        if not self.expires_at:
            return False
        return datetime.fromisoformat(self.expires_at) < datetime.now()

    def to_dict(self) -> Dict:
        """Serialize (without sensitive data)"""
        return {
            "auth_type": self.auth_type.value,
            "expires_at": self.expires_at,
            "scopes": self.scopes,
            "expired": self.is_expired(),
        }


@dataclass
class IntegrationTransaction:
    """Tracked external transaction"""
    transaction_id: str
    platform: IntegrationPlatform
    action: str
    status: TransactionStatus
    request_data: Dict[str, Any]
    response_data: Optional[Dict] = None
    error: Optional[str] = None
    created_at: str = ""
    completed_at: Optional[str] = None
    duration_ms: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize transaction"""
        return {
            "transaction_id": self.transaction_id,
            "platform": self.platform.value,
            "action": self.action,
            "status": self.status.value,
            "request_data": self.request_data,
            "response_data": self.response_data,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
        }


class PlatformAdapter(ABC):
    """Base adapter for platform integration"""

    def __init__(self, platform: IntegrationPlatform, credentials: AuthCredential):
        self.platform = platform
        self.credentials = credentials
        self.base_url: str = ""

    @abstractmethod
    def validate_credentials(self) -> bool:
        """Check if credentials are valid"""
        pass

    @abstractmethod
    def execute_action(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute action on platform"""
        pass

    @abstractmethod
    def handle_webhook(self, payload: Dict[str, Any]) -> bool:
        """Handle incoming webhook"""
        pass


class SalesforceAdapter(PlatformAdapter):
    """Salesforce CRM integration"""

    def __init__(self, credentials: AuthCredential):
        super().__init__(IntegrationPlatform.SALESFORCE, credentials)
        self.base_url = "https://api.salesforce.com/v60.0"

    def validate_credentials(self) -> bool:
        """Validate Salesforce token"""
        return self.credentials.auth_type == AuthType.OAUTH2 and not self.credentials.is_expired()

    def execute_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Salesforce action"""
        # Simulated execution
        if action == "create_contact":
            return {"id": "001D000000IRFmaIAF", "success": True}
        elif action == "update_opportunity":
            return {"id": params.get("id"), "updated": True}
        else:
            return {"error": f"Unknown action: {action}"}

    def handle_webhook(self, payload: Dict[str, Any]) -> bool:
        """Handle Salesforce webhook"""
        return payload.get("event") in ["created", "updated"]


class SlackAdapter(PlatformAdapter):
    """Slack communication integration"""

    def __init__(self, credentials: AuthCredential):
        super().__init__(IntegrationPlatform.SLACK, credentials)
        self.base_url = "https://slack.com/api"

    def validate_credentials(self) -> bool:
        """Validate Slack token"""
        return (
            self.credentials.auth_type == AuthType.API_KEY
            and self.credentials.token.startswith("xoxb-")
        )

    def execute_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Slack action"""
        if action == "send_message":
            return {"ok": True, "ts": "1503435956.000247"}
        elif action == "create_channel":
            return {"ok": True, "channel": {"id": "C1234567890"}}
        else:
            return {"ok": False, "error": f"Unknown action: {action}"}

    def handle_webhook(self, payload: Dict[str, Any]) -> bool:
        """Verify and handle Slack webhook"""
        # In real implementation, verify webhook signature
        return payload.get("type") == "url_verification"


class CustomAPIAdapter(PlatformAdapter):
    """Generic custom API adapter"""

    def __init__(self, credentials: AuthCredential, base_url: str):
        super().__init__(IntegrationPlatform.CUSTOM, credentials)
        self.base_url = base_url

    def validate_credentials(self) -> bool:
        """Validate API key"""
        return bool(self.credentials.token)

    def execute_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute custom API call"""
        endpoint = f"{self.base_url}/{action}"
        headers = self._build_headers()
        # Simulated request
        return {"status": "ok", "endpoint": endpoint}

    def handle_webhook(self, payload: Dict[str, Any]) -> bool:
        """Verify webhook with secret"""
        if self.credentials.auth_type != AuthType.WEBHOOK_SECRET:
            return False

        signature = payload.get("signature", "")
        body = json.dumps(payload.get("data", {}))
        expected = hmac.new(
            self.credentials.token.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with auth"""
        headers = {"Content-Type": "application/json"}

        if self.credentials.auth_type == AuthType.API_KEY:
            headers["Authorization"] = f"Bearer {self.credentials.token}"
        elif self.credentials.auth_type == AuthType.OAUTH2:
            headers["Authorization"] = f"Bearer {self.credentials.token}"

        return headers


class IntegrationManager:
    """Manage platform integrations"""

    def __init__(self):
        self.adapters: Dict[str, PlatformAdapter] = {}
        self.transactions: List[IntegrationTransaction] = []
        self.webhooks: Dict[str, Callable] = {}

    def register_platform(
        self,
        platform: IntegrationPlatform,
        credentials: AuthCredential,
        custom_base_url: Optional[str] = None,
    ) -> bool:
        """Register platform integration"""
        try:
            if platform == IntegrationPlatform.SALESFORCE:
                adapter = SalesforceAdapter(credentials)
            elif platform == IntegrationPlatform.SLACK:
                adapter = SlackAdapter(credentials)
            elif platform == IntegrationPlatform.CUSTOM:
                if not custom_base_url:
                    return False
                adapter = CustomAPIAdapter(credentials, custom_base_url)
            else:
                return False

            if not adapter.validate_credentials():
                return False

            self.adapters[platform.value] = adapter
            return True

        except Exception:
            return False

    def execute_action(
        self,
        platform: IntegrationPlatform,
        action: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute action on platform"""
        if platform.value not in self.adapters:
            return {"error": "Platform not registered"}

        adapter = self.adapters[platform.value]
        transaction_id = f"txn_{platform.value}_{action}_{int(datetime.now().timestamp())}"

        transaction = IntegrationTransaction(
            transaction_id=transaction_id,
            platform=platform,
            action=action,
            status=TransactionStatus.IN_PROGRESS,
            request_data=params,
        )

        try:
            start_time = datetime.now()
            response = adapter.execute_action(action, params)
            duration = (datetime.now() - start_time).total_seconds() * 1000

            transaction.status = TransactionStatus.COMPLETED
            transaction.response_data = response
            transaction.completed_at = datetime.now().isoformat()
            transaction.duration_ms = duration

        except Exception as e:
            transaction.status = TransactionStatus.FAILED
            transaction.error = str(e)
            transaction.completed_at = datetime.now().isoformat()

        self.transactions.append(transaction)
        return transaction.to_dict()

    def register_webhook(
        self,
        platform: IntegrationPlatform,
        handler: Callable[[Dict], None],
    ):
        """Register webhook handler"""
        self.webhooks[platform.value] = handler

    def process_webhook(
        self,
        platform: IntegrationPlatform,
        payload: Dict[str, Any],
    ) -> bool:
        """Process incoming webhook"""
        if platform.value not in self.adapters:
            return False

        adapter = self.adapters[platform.value]

        if not adapter.handle_webhook(payload):
            return False

        if platform.value in self.webhooks:
            try:
                self.webhooks[platform.value](payload)
            except Exception:
                return False

        return True

    def get_transaction_history(
        self,
        platform: Optional[IntegrationPlatform] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """Get transaction history"""
        transactions = self.transactions

        if platform:
            transactions = [t for t in transactions if t.platform == platform]

        return [t.to_dict() for t in transactions[-limit:]]

    def rollback_transaction(self, transaction_id: str) -> bool:
        """Attempt to rollback transaction"""
        transaction = None
        for t in self.transactions:
            if t.transaction_id == transaction_id:
                transaction = t
                break

        if not transaction or transaction.status != TransactionStatus.COMPLETED:
            return False

        # Simulate rollback
        transaction.status = TransactionStatus.ROLLED_BACK
        return True

    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of all integrations"""
        return {
            "registered_platforms": list(self.adapters.keys()),
            "total_transactions": len(self.transactions),
            "successful_transactions": sum(
                1 for t in self.transactions
                if t.status == TransactionStatus.COMPLETED
            ),
            "failed_transactions": sum(
                1 for t in self.transactions
                if t.status == TransactionStatus.FAILED
            ),
            "platform_details": {
                platform: {"registered": True, "webhook_handler": platform in self.webhooks}
                for platform in self.adapters.keys()
            },
        }


# Global manager
integration_manager = IntegrationManager()


# MCP Tools (add to memory_server.py)

def register_platform_integration(
    platform: str,
    auth_type: str,
    token: str,
    custom_base_url: str = None,
) -> dict:
    """Register external platform integration"""
    credentials = AuthCredential(
        auth_type=AuthType(auth_type),
        token=token,
    )
    success = integration_manager.register_platform(
        IntegrationPlatform(platform),
        credentials,
        custom_base_url,
    )
    return {"platform": platform, "registered": success}


def execute_platform_action(
    platform: str,
    action: str,
    params: dict,
) -> dict:
    """Execute action on integrated platform"""
    return integration_manager.execute_action(
        IntegrationPlatform(platform),
        action,
        params,
    )


def process_incoming_webhook(
    platform: str,
    payload: dict,
) -> dict:
    """Process webhook from platform"""
    success = integration_manager.process_webhook(
        IntegrationPlatform(platform),
        payload,
    )
    return {"platform": platform, "processed": success}


def get_integration_transaction_history(platform: str = None) -> dict:
    """Get transaction history"""
    transactions = integration_manager.get_transaction_history(
        IntegrationPlatform(platform) if platform else None
    )
    return {"transactions": transactions}


def get_integration_status() -> dict:
    """Get overall integration status"""
    return integration_manager.get_integration_status()


if __name__ == "__main__":
    # Test integration
    manager = IntegrationManager()

    # Register Slack
    slack_cred = AuthCredential(
        auth_type=AuthType.API_KEY,
        token="YOUR_SLACK_BOT_TOKEN",
    )
    success = manager.register_platform(IntegrationPlatform.SLACK, slack_cred)
    print(f"Slack registered: {success}")

    # Execute action
    result = manager.execute_action(
        IntegrationPlatform.SLACK,
        "send_message",
        {"channel": "C123456", "text": "Hello from agent"},
    )
    print(f"Message sent: {result}")

    # Get status
    status = manager.get_integration_status()
    print(f"Integration status: {json.dumps(status, indent=2)}")
