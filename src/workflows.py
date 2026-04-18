"""Conversation workflow automation with templates and state machines"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

WORKFLOWS_DIR = Path.home() / ".memory-mcp" / "workflows"
WORKFLOWS_DIR.mkdir(exist_ok=True, parents=True)


class NodeType(Enum):
    """Workflow node types"""
    START = "start"
    END = "end"
    AGENT_RESPONSE = "agent_response"  # Agent generates response
    CONDITION = "condition"  # Branching logic
    ACTION = "action"  # Execute external action
    WAIT = "wait"  # Wait for user input
    LOOP = "loop"  # Repeat
    MERGE = "merge"  # Join paths


class TransitionType(Enum):
    """Edge types between nodes"""
    DEFAULT = "default"
    CONDITIONAL = "conditional"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class WorkflowNode:
    """Single node in workflow"""
    node_id: str
    node_type: NodeType
    name: str
    description: str
    config: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Serialize node"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "description": self.description,
            "config": self.config,
            "inputs": self.inputs,
            "outputs": self.outputs,
        }


@dataclass
class WorkflowTransition:
    """Edge between workflow nodes"""
    transition_id: str
    source_node_id: str
    target_node_id: str
    transition_type: TransitionType
    condition: Optional[Callable[[], bool]] = None  # For conditional transitions
    label: str = ""

    def to_dict(self) -> Dict:
        """Serialize (without callable)"""
        return {
            "transition_id": self.transition_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "transition_type": self.transition_type.value,
            "label": self.label,
        }


@dataclass
class WorkflowTemplate:
    """Reusable workflow pattern"""
    template_id: str
    name: str
    description: str
    nodes: Dict[str, WorkflowNode] = field(default_factory=dict)
    transitions: Dict[str, WorkflowTransition] = field(default_factory=dict)
    input_params: Dict[str, str] = field(default_factory=dict)
    output_params: Dict[str, str] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize template"""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "transitions": [t.to_dict() for t in self.transitions.values()],
            "input_params": self.input_params,
            "output_params": self.output_params,
            "created_at": self.created_at,
        }


@dataclass
class WorkflowExecution:
    """Instance of workflow execution"""
    execution_id: str
    template_id: str
    status: str  # "running", "completed", "failed", "paused"
    current_node_id: str
    context: Dict[str, Any] = field(default_factory=dict)
    visited_nodes: List[str] = field(default_factory=list)
    execution_log: List[Dict] = field(default_factory=list)
    created_at: str = ""
    completed_at: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize execution"""
        return {
            "execution_id": self.execution_id,
            "template_id": self.template_id,
            "status": self.status,
            "current_node_id": self.current_node_id,
            "context": self.context,
            "visited_nodes": self.visited_nodes,
            "execution_log": self.execution_log[-50:],  # Last 50
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class WorkflowEngine:
    """Execute workflows"""

    def __init__(self):
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.executions: Dict[str, WorkflowExecution] = {}

    def create_template(
        self,
        template_id: str,
        name: str,
        description: str,
    ) -> WorkflowTemplate:
        """Create new workflow template"""
        template = WorkflowTemplate(
            template_id=template_id,
            name=name,
            description=description,
        )
        self.templates[template_id] = template
        return template

    def add_node(
        self,
        template_id: str,
        node: WorkflowNode,
    ) -> bool:
        """Add node to template"""
        if template_id not in self.templates:
            return False

        self.templates[template_id].nodes[node.node_id] = node
        return True

    def add_transition(
        self,
        template_id: str,
        transition: WorkflowTransition,
    ) -> bool:
        """Add transition to template"""
        if template_id not in self.templates:
            return False

        template = self.templates[template_id]
        if (
            transition.source_node_id not in template.nodes
            or transition.target_node_id not in template.nodes
        ):
            return False

        template.transitions[transition.transition_id] = transition
        return True

    def start_execution(
        self,
        execution_id: str,
        template_id: str,
        initial_context: Optional[Dict] = None,
    ) -> Optional[WorkflowExecution]:
        """Start workflow execution"""
        if template_id not in self.templates:
            return None

        template = self.templates[template_id]

        # Find start node
        start_node = None
        for node in template.nodes.values():
            if node.node_type == NodeType.START:
                start_node = node
                break

        if not start_node:
            return None

        execution = WorkflowExecution(
            execution_id=execution_id,
            template_id=template_id,
            status="running",
            current_node_id=start_node.node_id,
            context=initial_context or {},
        )

        self.executions[execution_id] = execution
        execution.visited_nodes.append(start_node.node_id)

        return execution

    def transition_to_next(
        self,
        execution_id: str,
    ) -> Optional[str]:
        """Move to next node in workflow"""
        if execution_id not in self.executions:
            return None

        execution = self.executions[execution_id]
        template = self.templates[execution.template_id]
        current_node_id = execution.current_node_id

        # Find applicable transition
        next_node_id = None
        for transition in template.transitions.values():
            if transition.source_node_id == current_node_id:
                if transition.transition_type == TransitionType.CONDITIONAL:
                    if transition.condition and transition.condition():
                        next_node_id = transition.target_node_id
                        break
                else:
                    next_node_id = transition.target_node_id
                    break

        if not next_node_id:
            return None

        # Update execution
        execution.current_node_id = next_node_id
        execution.visited_nodes.append(next_node_id)

        # Check if end
        next_node = template.nodes[next_node_id]
        if next_node.node_type == NodeType.END:
            execution.status = "completed"
            execution.completed_at = datetime.now().isoformat()

        execution.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "node_id": next_node_id,
            "node_name": next_node.name,
        })

        return next_node_id

    def pause_execution(self, execution_id: str) -> bool:
        """Pause workflow"""
        if execution_id not in self.executions:
            return False

        self.executions[execution_id].status = "paused"
        return True

    def resume_execution(self, execution_id: str) -> bool:
        """Resume paused workflow"""
        if execution_id not in self.executions:
            return False

        execution = self.executions[execution_id]
        if execution.status != "paused":
            return False

        execution.status = "running"
        return True

    def get_execution_status(self, execution_id: str) -> Optional[Dict]:
        """Get execution status"""
        if execution_id not in self.executions:
            return None

        execution = self.executions[execution_id]
        return execution.to_dict()

    def save_template(self, template_id: str) -> str:
        """Save template to disk"""
        if template_id not in self.templates:
            return ""

        template = self.templates[template_id]
        filepath = WORKFLOWS_DIR / f"{template_id}_template.json"

        with open(filepath, "w") as f:
            json.dump(template.to_dict(), f, indent=2)

        return str(filepath)


# Global engine
workflow_engine = WorkflowEngine()


# MCP Tools (add to memory_server.py)

def create_workflow_template(
    template_id: str,
    name: str,
    description: str,
) -> dict:
    """Create workflow template"""
    template = workflow_engine.create_template(template_id, name, description)
    return {
        "template_id": template.template_id,
        "name": template.name,
        "created": True,
    }


def add_workflow_node(
    template_id: str,
    node_id: str,
    node_type: str,
    name: str,
    description: str,
    config: dict = None,
) -> dict:
    """Add node to workflow"""
    node = WorkflowNode(
        node_id=node_id,
        node_type=NodeType(node_type),
        name=name,
        description=description,
        config=config or {},
    )
    success = workflow_engine.add_node(template_id, node)
    return {"node_id": node_id, "added": success}


def start_workflow_execution(
    execution_id: str,
    template_id: str,
    context: dict = None,
) -> dict:
    """Start workflow execution"""
    execution = workflow_engine.start_execution(execution_id, template_id, context)
    return (
        execution.to_dict()
        if execution
        else {"error": "Template not found"}
    )


def transition_workflow(execution_id: str) -> dict:
    """Move to next step in workflow"""
    next_node = workflow_engine.transition_to_next(execution_id)
    if next_node:
        return {"next_node_id": next_node, "transitioned": True}
    return {"transitioned": False, "error": "No next node"}


def get_workflow_status(execution_id: str) -> dict:
    """Get workflow execution status"""
    status = workflow_engine.get_execution_status(execution_id)
    return status or {"error": "Execution not found"}


if __name__ == "__main__":
    # Test workflows
    engine = WorkflowEngine()

    # Create template
    template = engine.create_template(
        "support_flow",
        "Customer Support Flow",
        "Template for support conversations",
    )

    # Add nodes
    start = WorkflowNode(
        "n_start",
        NodeType.START,
        "Start",
        "Begin support conversation",
    )
    engine.add_node(template.template_id, start)

    response = WorkflowNode(
        "n_response",
        NodeType.AGENT_RESPONSE,
        "Agent Response",
        "Agent provides initial response",
        config={"prompt": "How can I help?"},
    )
    engine.add_node(template.template_id, response)

    end = WorkflowNode(
        "n_end",
        NodeType.END,
        "End",
        "End conversation",
    )
    engine.add_node(template.template_id, end)

    # Add transitions
    t1 = WorkflowTransition(
        "t1",
        "n_start",
        "n_response",
        TransitionType.DEFAULT,
    )
    engine.add_transition(template.template_id, t1)

    t2 = WorkflowTransition(
        "t2",
        "n_response",
        "n_end",
        TransitionType.DEFAULT,
    )
    engine.add_transition(template.template_id, t2)

    # Execute
    execution = engine.start_execution("exec_1", template.template_id)
    print(f"Started execution: {execution.execution_id}")

    # Progress
    next_node = engine.transition_to_next("exec_1")
    print(f"Next node: {next_node}")

    # Status
    status = engine.get_execution_status("exec_1")
    print(f"Status: {json.dumps(status, indent=2)}")
