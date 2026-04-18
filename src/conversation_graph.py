"""Conversation graph model for branching, threading, and workflow orchestration"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

GRAPHS_DIR = Path.home() / ".memory-mcp" / "graphs"
GRAPHS_DIR.mkdir(exist_ok=True, parents=True)


class EdgeType(Enum):
    """Types of conversation edges"""
    SEQUENTIAL = "sequential"  # Linear progression
    CONDITIONAL = "conditional"  # Branch based on condition
    PARALLEL = "parallel"  # Multiple paths simultaneously
    LOOP = "loop"  # Circular reference


class ConversationNode:
    """Node in conversation graph"""

    def __init__(
        self,
        node_id: str,
        agent_id: str,
        node_type: str = "interaction",  # interaction, decision, tool_call
        content: str = "",
        metadata: Optional[Dict] = None,
    ):
        self.id = node_id
        self.agent_id = agent_id
        self.type = node_type
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
        self.incoming_edges: List[str] = []  # parent node IDs
        self.outgoing_edges: List[str] = []  # child node IDs
        self.state: Dict = {}  # node-specific state

    def to_dict(self) -> Dict:
        """Serialize node"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "incoming_edges": self.incoming_edges,
            "outgoing_edges": self.outgoing_edges,
            "state": self.state,
        }

    @classmethod
    def from_dict(cls, data: Dict):
        """Deserialize node"""
        node = cls(
            node_id=data["id"],
            agent_id=data["agent_id"],
            node_type=data.get("type", "interaction"),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
        )
        node.timestamp = data.get("timestamp", datetime.now().isoformat())
        node.incoming_edges = data.get("incoming_edges", [])
        node.outgoing_edges = data.get("outgoing_edges", [])
        node.state = data.get("state", {})
        return node


class ConversationEdge:
    """Edge between nodes"""

    def __init__(
        self,
        source: str,
        target: str,
        edge_type: EdgeType = EdgeType.SEQUENTIAL,
        condition: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        self.source = source
        self.target = target
        self.type = edge_type
        self.condition = condition  # For conditional edges: "state.key == value"
        self.metadata = metadata or {}
        self.weight = 1  # For prioritization

    def to_dict(self) -> Dict:
        """Serialize edge"""
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type.value,
            "condition": self.condition,
            "metadata": self.metadata,
            "weight": self.weight,
        }

    @classmethod
    def from_dict(cls, data: Dict):
        """Deserialize edge"""
        return cls(
            source=data["source"],
            target=data["target"],
            edge_type=EdgeType(data.get("type", "sequential")),
            condition=data.get("condition"),
            metadata=data.get("metadata", {}),
        )


class ConversationGraph:
    """Directed graph model for agent conversations"""

    def __init__(self, graph_id: str, title: str = ""):
        self.id = graph_id
        self.title = title
        self.nodes: Dict[str, ConversationNode] = {}
        self.edges: List[ConversationEdge] = []
        self.root_node: Optional[str] = None
        self.current_node: Optional[str] = None
        self.created_at = datetime.now().isoformat()

    def add_node(self, node: ConversationNode) -> str:
        """Add node to graph"""
        self.nodes[node.id] = node

        if not self.root_node:
            self.root_node = node.id
            self.current_node = node.id

        return node.id

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType = EdgeType.SEQUENTIAL,
        condition: Optional[str] = None,
    ) -> ConversationEdge:
        """Add edge between nodes"""
        if source not in self.nodes or target not in self.nodes:
            raise ValueError("Source and target nodes must exist")

        edge = ConversationEdge(source, target, edge_type, condition)
        self.edges.append(edge)

        # Update node references
        self.nodes[source].outgoing_edges.append(target)
        self.nodes[target].incoming_edges.append(source)

        return edge

    def get_next_nodes(self, node_id: str) -> List[str]:
        """Get possible next nodes from current node"""
        return self.nodes[node_id].outgoing_edges

    def traverse(self, node_id: str) -> List[ConversationNode]:
        """Get path from root to node"""
        path = []
        current = node_id

        while current:
            if current in self.nodes:
                path.insert(0, self.nodes[current])
                # Get parent (incoming edge)
                incoming = self.nodes[current].incoming_edges
                current = incoming[0] if incoming else None
            else:
                break

        return path

    def get_branch_paths(self, node_id: str) -> List[List[str]]:
        """Get all possible paths from node to leaves"""
        paths = []

        def dfs(current: str, path: List[str]):
            path.append(current)
            next_nodes = self.get_next_nodes(current)

            if not next_nodes:  # Leaf node
                paths.append(path.copy())
            else:
                for next_node in next_nodes:
                    dfs(next_node, path)

            path.pop()

        dfs(node_id, [])
        return paths

    def detect_cycles(self) -> List[List[str]]:
        """Detect cycles in graph"""
        cycles = []

        def has_cycle(node: str, visited: set, rec_stack: set, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for next_node in self.get_next_nodes(node):
                if next_node not in visited:
                    if has_cycle(next_node, visited, rec_stack, path):
                        return True
                elif next_node in rec_stack:
                    cycle_start = path.index(next_node)
                    cycles.append(path[cycle_start:] + [next_node])
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        visited = set()
        for node_id in self.nodes:
            if node_id not in visited:
                has_cycle(node_id, visited, set(), [])

        return cycles

    def get_stats(self) -> Dict:
        """Get graph statistics"""
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "has_cycles": len(self.detect_cycles()) > 0,
            "max_depth": self._calculate_max_depth(),
            "branching_factor": self._calculate_branching_factor(),
        }

    def _calculate_max_depth(self) -> int:
        """Calculate maximum depth from root"""
        if not self.root_node:
            return 0

        max_depth = 0

        def dfs(node: str, depth: int):
            nonlocal max_depth
            max_depth = max(max_depth, depth)
            for next_node in self.get_next_nodes(node):
                dfs(next_node, depth + 1)

        dfs(self.root_node, 0)
        return max_depth

    def _calculate_branching_factor(self) -> float:
        """Calculate average branching factor"""
        if not self.nodes:
            return 0.0

        total_outgoing = sum(len(n.outgoing_edges) for n in self.nodes.values())
        return total_outgoing / len(self.nodes) if self.nodes else 0.0

    def to_dict(self) -> Dict:
        """Serialize graph"""
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "root_node": self.root_node,
            "current_node": self.current_node,
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "edges": [edge.to_dict() for edge in self.edges],
        }

    @classmethod
    def from_dict(cls, data: Dict):
        """Deserialize graph"""
        graph = cls(data["id"], data.get("title", ""))
        graph.created_at = data.get("created_at")
        graph.root_node = data.get("root_node")
        graph.current_node = data.get("current_node")

        # Load nodes
        for node_data in data.get("nodes", {}).values():
            node = ConversationNode.from_dict(node_data)
            graph.nodes[node.id] = node

        # Load edges
        for edge_data in data.get("edges", []):
            edge = ConversationEdge.from_dict(edge_data)
            graph.edges.append(edge)

        return graph

    def save(self) -> str:
        """Save graph to file"""
        filepath = GRAPHS_DIR / f"{self.id}.json"
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return str(filepath)

    @classmethod
    def load(cls, graph_id: str) -> Optional["ConversationGraph"]:
        """Load graph from file"""
        filepath = GRAPHS_DIR / f"{graph_id}.json"
        if not filepath.exists():
            return None

        with open(filepath) as f:
            data = json.load(f)
        return cls.from_dict(data)


class ConversationThread:
    """Thread represents a conversation branch"""

    def __init__(self, thread_id: str, graph_id: str):
        self.id = thread_id
        self.graph_id = graph_id
        self.messages: List[Dict] = []
        self.current_node: Optional[str] = None
        self.state: Dict = {}  # Shared state across thread
        self.created_at = datetime.now().isoformat()

    def add_message(
        self,
        role: str,
        content: str,
        node_id: Optional[str] = None,
    ) -> Dict:
        """Add message to thread"""
        message = {
            "id": f"{self.id}_msg_{len(self.messages)}",
            "role": role,
            "content": content,
            "node_id": node_id,
            "timestamp": datetime.now().isoformat(),
        }
        self.messages.append(message)
        self.current_node = node_id
        return message

    def get_context(self) -> Dict:
        """Get thread context for agent"""
        return {
            "thread_id": self.id,
            "messages": self.messages[-10:],  # Last 10 messages
            "state": self.state,
            "current_node": self.current_node,
        }

    def to_dict(self) -> Dict:
        """Serialize thread"""
        return {
            "id": self.id,
            "graph_id": self.graph_id,
            "messages": self.messages,
            "current_node": self.current_node,
            "state": self.state,
            "created_at": self.created_at,
        }


# Global instance manager
class GraphManager:
    """Manage conversation graphs"""

    @staticmethod
    def create_graph(graph_id: str, title: str = "") -> ConversationGraph:
        """Create new graph"""
        return ConversationGraph(graph_id, title)

    @staticmethod
    def save_graph(graph: ConversationGraph) -> str:
        """Save graph"""
        return graph.save()

    @staticmethod
    def load_graph(graph_id: str) -> Optional[ConversationGraph]:
        """Load graph"""
        return ConversationGraph.load(graph_id)

    @staticmethod
    def list_graphs() -> List[str]:
        """List all saved graphs"""
        return [f.stem for f in GRAPHS_DIR.glob("*.json")]


# MCP Tools (add to memory_server.py)

def create_conversation_graph(graph_id: str, title: str = "") -> dict:
    """Create new conversation graph"""
    graph = GraphManager.create_graph(graph_id, title)
    GraphManager.save_graph(graph)
    return {"graph_id": graph.id, "title": graph.title}


def add_node_to_graph(
    graph_id: str,
    node_id: str,
    agent_id: str,
    node_type: str = "interaction",
    content: str = "",
) -> dict:
    """Add node to conversation graph"""
    graph = GraphManager.load_graph(graph_id)
    if not graph:
        return {"error": "Graph not found"}

    node = ConversationNode(node_id, agent_id, node_type, content)
    graph.add_node(node)
    GraphManager.save_graph(graph)
    return node.to_dict()


def add_edge_to_graph(
    graph_id: str,
    source: str,
    target: str,
    edge_type: str = "sequential",
) -> dict:
    """Add edge (connection) between nodes"""
    graph = GraphManager.load_graph(graph_id)
    if not graph:
        return {"error": "Graph not found"}

    edge = graph.add_edge(source, target, EdgeType(edge_type))
    GraphManager.save_graph(graph)
    return edge.to_dict()


def get_graph_stats(graph_id: str) -> dict:
    """Get conversation graph statistics"""
    graph = GraphManager.load_graph(graph_id)
    if not graph:
        return {"error": "Graph not found"}
    return graph.get_stats()


def detect_cycles(graph_id: str) -> list:
    """Detect cycles in conversation graph"""
    graph = GraphManager.load_graph(graph_id)
    if not graph:
        return []
    return graph.detect_cycles()


if __name__ == "__main__":
    # Test graph creation
    graph = ConversationGraph("test_graph", "Test Conversation")

    # Add nodes
    node1 = ConversationNode("node_1", "user", "interaction", "Hello")
    node2 = ConversationNode("node_2", "agent_1", "interaction", "Hi there!")
    node3 = ConversationNode("node_3", "user", "decision", "Ask question")
    node4a = ConversationNode("node_4a", "agent_2", "tool_call", "Search")
    node4b = ConversationNode("node_4b", "agent_3", "tool_call", "Calculate")

    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_node(node3)
    graph.add_node(node4a)
    graph.add_node(node4b)

    # Add edges
    graph.add_edge("node_1", "node_2", EdgeType.SEQUENTIAL)
    graph.add_edge("node_2", "node_3", EdgeType.SEQUENTIAL)
    graph.add_edge("node_3", "node_4a", EdgeType.PARALLEL)
    graph.add_edge("node_3", "node_4b", EdgeType.PARALLEL)

    # Get stats
    print("Graph Stats:", graph.get_stats())
    print("Cycles:", graph.detect_cycles())
    print("Branch paths from node_3:", graph.get_branch_paths("node_3"))
