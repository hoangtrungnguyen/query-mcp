"""Shared context store for multi-agent coordination"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from threading import RLock

SHARED_CONTEXT_DIR = Path.home() / ".memory-mcp" / "shared-context"
SHARED_CONTEXT_DIR.mkdir(exist_ok=True, parents=True)


class ContextStore:
    """Thread-safe shared context store for multi-agent coordination"""

    def __init__(self, namespace: str = "default"):
        """
        Initialize context store with namespace for access control.
        Namespaces isolate agent contexts while allowing selective sharing.
        """
        self.namespace = namespace
        self.store_dir = SHARED_CONTEXT_DIR / namespace
        self.store_dir.mkdir(exist_ok=True, parents=True)
        self.lock = RLock()
        self.memory = {}  # In-memory cache

    def _get_filepath(self, key: str) -> Path:
        """Get safe filepath for a key"""
        # Sanitize key to prevent path traversal
        safe_key = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
        return self.store_dir / f"{safe_key}.json"

    def set(self, key: str, value: Any, metadata: Optional[Dict] = None) -> Dict:
        """Store a value in shared context"""
        with self.lock:
            record = {
                "namespace": self.namespace,
                "key": key,
                "value": value,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
            }

            filepath = self._get_filepath(key)
            with open(filepath, "w") as f:
                json.dump(record, f, indent=2)

            self.memory[key] = record
            return record

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from shared context"""
        with self.lock:
            if key in self.memory:
                return self.memory[key]["value"]

            filepath = self._get_filepath(key)
            if filepath.exists():
                with open(filepath) as f:
                    record = json.load(f)
                    self.memory[key] = record
                    return record["value"]

            return None

    def get_full(self, key: str) -> Optional[Dict]:
        """Get full record including metadata"""
        with self.lock:
            if key in self.memory:
                return self.memory[key]

            filepath = self._get_filepath(key)
            if filepath.exists():
                with open(filepath) as f:
                    record = json.load(f)
                    self.memory[key] = record
                    return record

            return None

    def list_keys(self) -> List[str]:
        """List all keys in this namespace"""
        with self.lock:
            files = list(self.store_dir.glob("*.json"))
            return [f.stem for f in files]

    def delete(self, key: str) -> bool:
        """Delete a value from shared context"""
        with self.lock:
            filepath = self._get_filepath(key)
            if filepath.exists():
                filepath.unlink()
                if key in self.memory:
                    del self.memory[key]
                return True
            return False

    def update(self, key: str, updates: Dict) -> Optional[Dict]:
        """Update nested value (merge dicts)"""
        with self.lock:
            current = self.get_full(key)
            if current is None:
                return None

            # Merge updates
            if isinstance(current["value"], dict):
                current["value"].update(updates)
            else:
                return None

            current["timestamp"] = datetime.now().isoformat()
            filepath = self._get_filepath(key)
            with open(filepath, "w") as f:
                json.dump(current, f, indent=2)

            self.memory[key] = current
            return current


class TaskQueue:
    """Task queue for agent coordination"""

    def __init__(self, namespace: str = "tasks"):
        self.store = ContextStore(namespace)
        self.queue_file = self.store.store_dir / "queue.jsonl"

    def enqueue(
        self,
        task_id: str,
        task_data: Dict,
        priority: int = 0,
        agent_id: Optional[str] = None,
    ) -> Dict:
        """Add task to queue"""
        task = {
            "id": task_id,
            "data": task_data,
            "priority": priority,
            "status": "pending",
            "assigned_to": agent_id,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
        }

        with open(self.queue_file, "a") as f:
            f.write(json.dumps(task) + "\n")

        return task

    def dequeue(self, agent_id: str) -> Optional[Dict]:
        """Get next task for agent"""
        if not self.queue_file.exists():
            return None

        tasks = []
        with open(self.queue_file) as f:
            tasks = [json.loads(line) for line in f if line.strip()]

        # Find next pending task (highest priority)
        pending = [t for t in tasks if t["status"] == "pending"]
        if not pending:
            return None

        task = max(pending, key=lambda t: t["priority"])
        task["status"] = "in_progress"
        task["assigned_to"] = agent_id
        task["started_at"] = datetime.now().isoformat()

        self._rewrite_queue(tasks)
        return task

    def complete_task(self, task_id: str, result: Any) -> Optional[Dict]:
        """Mark task as complete"""
        if not self.queue_file.exists():
            return None

        tasks = []
        with open(self.queue_file) as f:
            tasks = [json.loads(line) for line in f if line.strip()]

        for task in tasks:
            if task["id"] == task_id:
                task["status"] = "completed"
                task["completed_at"] = datetime.now().isoformat()
                task["result"] = result
                self._rewrite_queue(tasks)
                return task

        return None

    def _rewrite_queue(self, tasks: List[Dict]):
        """Rewrite entire queue"""
        with open(self.queue_file, "w") as f:
            for task in tasks:
                f.write(json.dumps(task) + "\n")

    def get_status(self, task_id: str) -> Optional[str]:
        """Get task status"""
        if not self.queue_file.exists():
            return None

        with open(self.queue_file) as f:
            for line in f:
                task = json.loads(line)
                if task["id"] == task_id:
                    return task["status"]

        return None


class AgentRegistry:
    """Registry for agent metadata and coordination"""

    def __init__(self):
        self.store = ContextStore("agents")

    def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: List[str],
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Register an agent in the system"""
        agent_info = {
            "id": agent_id,
            "type": agent_type,
            "capabilities": capabilities,
            "status": "active",
            "registered_at": datetime.now().isoformat(),
            "last_heartbeat": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        self.store.set(agent_id, agent_info)
        return agent_info

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Get agent info"""
        return self.store.get(agent_id)

    def list_agents(self) -> List[Dict]:
        """List all registered agents"""
        agents = []
        for key in self.store.list_keys():
            agent = self.store.get(key)
            if agent:
                agents.append(agent)
        return agents

    def find_agents_by_capability(self, capability: str) -> List[Dict]:
        """Find agents with specific capability"""
        agents = []
        for agent in self.list_agents():
            if capability in agent.get("capabilities", []):
                agents.append(agent)
        return agents

    def update_heartbeat(self, agent_id: str):
        """Update agent heartbeat"""
        agent = self.store.get_full(agent_id)
        if agent:
            agent["value"]["last_heartbeat"] = datetime.now().isoformat()
            self.store.set(agent_id, agent["value"], agent["metadata"])


# Global instances
context_store = ContextStore("workflow")
task_queue = TaskQueue("tasks")
agent_registry = AgentRegistry()


# MCP Tools (add to memory_server.py)

def set_shared_context(key: str, value: dict, metadata: dict = None) -> dict:
    """Store value in shared context"""
    return context_store.set(key, value, metadata)


def get_shared_context(key: str) -> dict:
    """Retrieve value from shared context"""
    return context_store.get(key)


def update_shared_context(key: str, updates: dict) -> dict:
    """Update nested shared context"""
    return context_store.update(key, updates)


def list_shared_context() -> list:
    """List all keys in shared context"""
    return context_store.list_keys()


def enqueue_task(
    task_id: str, task_data: dict, priority: int = 0, agent_id: str = None
) -> dict:
    """Enqueue a task for agents"""
    return task_queue.enqueue(task_id, task_data, priority, agent_id)


def dequeue_task(agent_id: str) -> dict:
    """Get next task for agent"""
    return task_queue.dequeue(agent_id)


def complete_task(task_id: str, result: dict) -> dict:
    """Complete a task"""
    return task_queue.complete_task(task_id, result)


def register_agent(
    agent_id: str, agent_type: str, capabilities: list, metadata: dict = None
) -> dict:
    """Register agent in multi-agent system"""
    return agent_registry.register_agent(agent_id, agent_type, capabilities, metadata)


def find_agents(capability: str) -> list:
    """Find agents by capability"""
    return agent_registry.find_agents_by_capability(capability)


if __name__ == "__main__":
    # Test multi-agent coordination
    store = ContextStore("test")

    # Set shared state
    store.set("workflow_state", {"progress": 0, "stage": "init"})
    store.set("agent_config", {"timeout": 30, "retry": 3})

    # Get values
    print("Workflow state:", store.get("workflow_state"))
    print("Agent config:", store.get("agent_config"))

    # Update nested
    store.update("workflow_state", {"progress": 50, "stage": "processing"})
    print("Updated state:", store.get("workflow_state"))

    # Task queue
    queue = TaskQueue()
    queue.enqueue("task1", {"action": "analyze", "data": "..."}, priority=1)
    queue.enqueue("task2", {"action": "process", "data": "..."}, priority=0)

    task = queue.dequeue("agent_1")
    print("Dequeued task:", task)

    # Agent registry
    registry = AgentRegistry()
    registry.register_agent("analyzer", "text_processor", ["analyze", "summarize"])
    registry.register_agent("executor", "task_runner", ["execute", "monitor"])

    agents = registry.find_agents_by_capability("analyze")
    print("Agents with 'analyze':", agents)
