"""MCP Server for Conversation Memory Management"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP(
    "Memory MCP",
    instructions="Manage AI conversation memory (episodic, semantic, working)"
)

MEMORY_DIR = Path.home() / ".memory-mcp"
MEMORY_DIR.mkdir(exist_ok=True)

# Storage locations
EPISODIC_DB = MEMORY_DIR / "episodic.jsonl"  # Conversation logs
SEMANTIC_DB = MEMORY_DIR / "semantic.jsonl"  # Facts, patterns, concepts
WORKING_DB = MEMORY_DIR / "working.json"     # Current session state


class MemoryStore:
    """Base class for memory types"""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list:
        """Load all records from JSONL file"""
        if not self.filepath.exists():
            return []
        with open(self.filepath) as f:
            return [json.loads(line) for line in f if line.strip()]

    def _save(self, records: list):
        """Append record to JSONL"""
        with open(self.filepath, "a") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")


class EpisodicMemory(MemoryStore):
    """Stores conversation episodes (interaction logs)"""

    def __init__(self):
        super().__init__(EPISODIC_DB)

    def store_message(
        self,
        agent_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Store a single message"""
        record = {
            "id": f"{agent_id}_{datetime.now().timestamp()}",
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "metadata": metadata or {},
        }
        self._save([record])
        return record

    def get_messages(self, agent_id: str, limit: int = 10) -> list:
        """Get recent messages for an agent"""
        records = self._load()
        agent_records = [r for r in records if r.get("agent_id") == agent_id]
        return agent_records[-limit:]

    def search(self, agent_id: str, query: str) -> list:
        """Search messages by content"""
        records = self._load()
        agent_records = [r for r in records if r.get("agent_id") == agent_id]
        return [r for r in agent_records if query.lower() in r.get("content", "").lower()]


class SemanticMemory(MemoryStore):
    """Stores facts, patterns, and learned concepts"""

    def __init__(self):
        super().__init__(SEMANTIC_DB)

    def store_fact(
        self, agent_id: str, fact: str, category: str = "general", confidence: float = 1.0
    ) -> dict:
        """Store a learned fact"""
        record = {
            "id": f"{agent_id}_fact_{datetime.now().timestamp()}",
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
            "fact": fact,
            "category": category,
            "confidence": confidence,
        }
        self._save([record])
        return record

    def get_facts(self, agent_id: str, category: str = None) -> list:
        """Get facts for an agent, optionally filtered by category"""
        records = self._load()
        facts = [r for r in records if r.get("agent_id") == agent_id]
        if category:
            facts = [r for r in facts if r.get("category") == category]
        return facts

    def update_confidence(self, fact_id: str, confidence: float):
        """Update confidence in a fact"""
        records = self._load()
        for r in records:
            if r.get("id") == fact_id:
                r["confidence"] = confidence
        with open(self.filepath, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")


class WorkingMemory:
    """Stores current session state"""

    def __init__(self):
        self.filepath = WORKING_DB
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        """Load working state"""
        if not self.filepath.exists():
            return {}
        with open(self.filepath) as f:
            return json.load(f)

    def save(self, state: dict):
        """Save working state"""
        with open(self.filepath, "w") as f:
            json.dump(state, f, indent=2)

    def get_task(self, task_id: str) -> dict:
        """Get current task context"""
        state = self.load()
        return state.get("tasks", {}).get(task_id, {})

    def set_task(self, task_id: str, task_data: dict):
        """Set task context"""
        state = self.load()
        if "tasks" not in state:
            state["tasks"] = {}
        state["tasks"][task_id] = task_data
        self.save(state)


# Initialize memory stores
episodic = EpisodicMemory()
semantic = SemanticMemory()
working = WorkingMemory()


# MCP Tools


@mcp.tool()
def store_episode(agent_id: str, role: str, content: str) -> dict:
    """Store a conversation message in episodic memory"""
    return episodic.store_message(agent_id, role, content)


@mcp.tool()
def get_recent_messages(agent_id: str, limit: int = 10) -> list:
    """Get recent conversation messages for an agent"""
    return episodic.get_messages(agent_id, limit)


@mcp.tool()
def search_conversations(agent_id: str, query: str) -> list:
    """Search past conversations by content"""
    return episodic.search(agent_id, query)


@mcp.tool()
def store_fact(agent_id: str, fact: str, category: str = "general") -> dict:
    """Store a learned fact in semantic memory"""
    return semantic.store_fact(agent_id, fact, category)


@mcp.tool()
def get_facts(agent_id: str, category: Optional[str] = None) -> list:
    """Get learned facts for an agent"""
    return semantic.get_facts(agent_id, category)


@mcp.tool()
def get_task_context(task_id: str) -> dict:
    """Get current task working memory"""
    return working.get_task(task_id)


@mcp.tool()
def set_task_context(task_id: str, context: dict) -> dict:
    """Set task working memory state"""
    working.set_task(task_id, context)
    return {"status": "ok", "task_id": task_id}


@mcp.tool()
def search_conversations_fulltext(agent_id: str, query: str) -> list:
    """Full-text search conversations (Whoosh backend)"""
    from conversation_index import search_conversations_fulltext as search_fts
    return search_fts(agent_id, query)


@mcp.tool()
def fuzzy_search_conversations(agent_id: str, query: str, threshold: float = 0.7) -> list:
    """Fuzzy search message content (typo-tolerant)"""
    from conversation_index import fuzzy_search_conversations as fuzzy_search
    return fuzzy_search(agent_id, query, threshold)


@mcp.tool()
def filter_conversations(
    agent_id: str,
    role: str = None,
    start_date: str = None,
    end_date: str = None,
    tags: list = None,
) -> list:
    """Filter conversations by role, date range, and tags"""
    from conversation_index import filter_conversations as filter_convs
    return filter_convs(agent_id, role, start_date, end_date, tags)


@mcp.tool()
def semantic_search(agent_id: str, query: str, k: int = 5) -> list:
    """Find semantically similar messages using embeddings"""
    from semantic_embeddings import semantic_search as sem_search
    return sem_search(agent_id, query, k)


@mcp.tool()
def cluster_conversations(agent_id: str, min_similarity: float = 0.7) -> list:
    """Cluster messages by semantic similarity"""
    from semantic_embeddings import cluster_conversations as cluster_convs
    return cluster_convs(agent_id, min_similarity)


@mcp.tool()
def build_semantic_index(agent_id: str) -> dict:
    """Build vector index from conversation messages"""
    from semantic_embeddings import build_semantic_index as build_index
    return build_index(agent_id)


@mcp.tool()
def set_shared_context(key: str, value: dict, metadata: dict = None) -> dict:
    """Store value in shared context for multi-agent workflows"""
    from multi_agent_store import set_shared_context as set_ctx
    return set_ctx(key, value, metadata)


@mcp.tool()
def get_shared_context(key: str) -> dict:
    """Retrieve value from shared context"""
    from multi_agent_store import get_shared_context as get_ctx
    return get_ctx(key)


@mcp.tool()
def update_shared_context(key: str, updates: dict) -> dict:
    """Update nested shared context value"""
    from multi_agent_store import update_shared_context as update_ctx
    return update_ctx(key, updates)


@mcp.tool()
def list_shared_context() -> list:
    """List all keys in shared context"""
    from multi_agent_store import list_shared_context as list_ctx
    return list_ctx()


@mcp.tool()
def enqueue_task(
    task_id: str, task_data: dict, priority: int = 0, agent_id: str = None
) -> dict:
    """Enqueue a task for agent coordination"""
    from multi_agent_store import enqueue_task as enqueue
    return enqueue(task_id, task_data, priority, agent_id)


@mcp.tool()
def dequeue_task(agent_id: str) -> dict:
    """Get next task for agent from queue"""
    from multi_agent_store import dequeue_task as dequeue
    return dequeue(agent_id)


@mcp.tool()
def complete_task(task_id: str, result: dict) -> dict:
    """Mark task as complete with result"""
    from multi_agent_store import complete_task as complete
    return complete(task_id, result)


@mcp.tool()
def register_agent(
    agent_id: str, agent_type: str, capabilities: list, metadata: dict = None
) -> dict:
    """Register agent in multi-agent system"""
    from multi_agent_store import register_agent as register
    return register(agent_id, agent_type, capabilities, metadata)


@mcp.tool()
def find_agents(capability: str) -> list:
    """Find agents by capability"""
    from multi_agent_store import find_agents as find
    return find(capability)


@mcp.tool()
def estimate_tokens(text: str) -> int:
    """Estimate token count for text"""
    from memory_compaction import estimate_tokens as est_tokens
    return est_tokens(text)


@mcp.tool()
def summarize_conversation(agent_id: str, limit: int = 50) -> dict:
    """Summarize recent conversation with key facts preserved"""
    from memory_compaction import summarize_conversation as summarize
    return summarize(agent_id, limit)


@mcp.tool()
def archive_old_messages(agent_id: str, days: int = 30) -> dict:
    """Archive messages older than N days to cold storage"""
    from memory_compaction import archive_old_messages as archive
    return archive(agent_id, days)


@mcp.tool()
def compact_conversation(agent_id: str) -> dict:
    """Apply progressive compaction (trim → summarize → archive)"""
    from memory_compaction import compact_conversation as compact
    return compact(agent_id)


@mcp.tool()
def list_archives(agent_id: str) -> list:
    """List all archives for agent"""
    from memory_compaction import list_archives as list_arch
    return list_arch(agent_id)


@mcp.tool()
def retrieve_archive(archive_id: str) -> list:
    """Retrieve messages from archive"""
    from memory_compaction import retrieve_archive as retrieve
    return retrieve(archive_id)


@mcp.tool()
def export_conversation(
    agent_id: str,
    format: str = "json",
    limit: int = 100,
) -> dict:
    """Export conversation in multiple formats (json/jsonl/markdown/csv/html)"""
    from export_audit import export_conversation as export_conv
    return export_conv(agent_id, format, limit)


@mcp.tool()
def get_audit_trail(agent_id: str, days: int = 30) -> list:
    """Get audit trail for agent with all operations logged"""
    from export_audit import get_audit_trail as get_trail
    return get_trail(agent_id, days)


@mcp.tool()
def export_audit_report(agent_id: str) -> str:
    """Export audit report to file"""
    from export_audit import export_audit_report as export_report
    return export_report(agent_id)


@mcp.tool()
def set_retention_policy(data_type: str, days: int, reason: str) -> dict:
    """Set GDPR-compliant retention policy for data type"""
    from export_audit import set_retention_policy as set_policy
    return set_policy(data_type, days, reason)


@mcp.tool()
def get_retention_policy(data_type: str) -> dict:
    """Get retention policy for data type"""
    from export_audit import get_retention_policy as get_policy
    return get_policy(data_type)


@mcp.tool()
def mark_for_deletion(
    data_id: str,
    data_type: str,
    reason: str = "user_request",
) -> dict:
    """Mark data for deletion with audit trail"""
    from export_audit import mark_for_deletion as mark_delete
    return mark_delete(data_id, data_type, reason)


@mcp.tool()
def execute_deletion(data_id: str) -> bool:
    """Execute permanent deletion (irreversible)"""
    from export_audit import execute_deletion as exec_delete
    return exec_delete(data_id)


@mcp.tool()
def create_conversation_graph(graph_id: str, title: str = "") -> dict:
    """Create new conversation graph for branching workflows"""
    from conversation_graph import create_conversation_graph as create_graph
    return create_graph(graph_id, title)


@mcp.tool()
def add_node_to_graph(
    graph_id: str,
    node_id: str,
    agent_id: str,
    node_type: str = "interaction",
    content: str = "",
) -> dict:
    """Add node to conversation graph"""
    from conversation_graph import add_node_to_graph as add_node
    return add_node(graph_id, node_id, agent_id, node_type, content)


@mcp.tool()
def add_edge_to_graph(
    graph_id: str,
    source: str,
    target: str,
    edge_type: str = "sequential",
) -> dict:
    """Add edge between nodes (sequential/conditional/parallel/loop)"""
    from conversation_graph import add_edge_to_graph as add_edge
    return add_edge(graph_id, source, target, edge_type)


@mcp.tool()
def get_graph_stats(graph_id: str) -> dict:
    """Get conversation graph statistics"""
    from conversation_graph import get_graph_stats as get_stats
    return get_stats(graph_id)


@mcp.tool()
def detect_cycles(graph_id: str) -> list:
    """Detect cycles in conversation graph"""
    from conversation_graph import detect_cycles as detect_cyc
    return detect_cyc(graph_id)


@mcp.tool()
def start_trace(trace_id: str, agent_id: str, user_intent: str = "") -> dict:
    """Start new execution trace for observability"""
    from tool_tracking import start_trace as start_tr
    return start_tr(trace_id, agent_id, user_intent)


@mcp.tool()
def end_trace(trace_id: str) -> dict:
    """End trace and save to file"""
    from tool_tracking import end_trace as end_tr
    return end_tr(trace_id)


@mcp.tool()
def add_tool_call(
    trace_id: str,
    tool_name: str,
    input_args: dict,
    output: dict = None,
    error: str = None,
    duration_ms: float = 0,
) -> dict:
    """Add tool call span to trace"""
    from tool_tracking import add_tool_call as add_call
    return add_call(trace_id, tool_name, input_args, output, error, duration_ms)


@mcp.tool()
def get_tool_stats(agent_id: str) -> dict:
    """Get tool statistics and performance metrics"""
    from tool_tracking import get_tool_stats as get_stats
    return get_stats(agent_id)


@mcp.tool()
def get_trace(trace_id: str) -> dict:
    """Get trace details and all spans"""
    from tool_tracking import get_trace as get_tr
    return get_tr(trace_id)


@mcp.tool()
def list_traces(agent_id: str, limit: int = 10) -> list:
    """List recent execution traces for agent"""
    from tool_tracking import list_traces as list_tr
    return list_tr(agent_id, limit)


@mcp.tool()
def register_agent(
    agent_id: str,
    agent_name: str,
    capabilities: list,
    expertise_level: float = 1.0,
) -> dict:
    """Register agent in routing system"""
    from agent_router import register_agent as reg_agent
    return reg_agent(agent_id, agent_name, capabilities, expertise_level)


@mcp.tool()
def route_query(
    query: str,
    required_capability: str = None,
) -> dict:
    """Route query to most appropriate agent"""
    from agent_router import route_query as route
    return route(query, required_capability)


@mcp.tool()
def initiate_handoff(
    source_agent: str,
    target_agent: str = None,
    trigger: str = "completion",
    query: str = None,
) -> dict:
    """Initiate agent handoff with context preservation"""
    from agent_router import initiate_handoff as handoff
    return handoff(source_agent, target_agent, trigger, query)


@mcp.tool()
def complete_handoff(handoff_id: str, output: str = None) -> bool:
    """Complete handoff and save context"""
    from agent_router import complete_handoff as complete
    return complete(handoff_id, output)


@mcp.tool()
def update_confidence(agent_id: str, score: float) -> dict:
    """Update agent confidence score (0.0-1.0)"""
    from agent_router import update_confidence as update_conf
    return update_conf(agent_id, score)


@mcp.tool()
def get_handoff_history(agent_id: str = None) -> list:
    """Get handoff history for agent"""
    from agent_router import get_handoff_history as get_history
    return get_history(agent_id)


@mcp.tool()
def create_group_chat(
    chat_id: str,
    topic: str,
    max_agents: int = 3,
    strategy: str = "round_robin",
) -> dict:
    """Create group chat session for multi-agent debate"""
    from group_chat import create_group_chat as create_chat
    return create_chat(chat_id, topic, max_agents, strategy)


@mcp.tool()
def add_agent_to_chat(
    chat_id: str,
    agent_id: str,
    agent_name: str,
    role: str = "participant",
    expertise: str = None,
) -> dict:
    """Add agent to group chat"""
    from group_chat import add_agent_to_chat as add_agent
    return add_agent(chat_id, agent_id, agent_name, role, expertise)


@mcp.tool()
def add_message_to_chat(chat_id: str, speaker_id: str, content: str) -> dict:
    """Add message to group chat"""
    from group_chat import add_message_to_chat as add_msg
    return add_msg(chat_id, speaker_id, content)


@mcp.tool()
def get_next_speaker(chat_id: str) -> dict:
    """Get next speaker in chat turn order"""
    from group_chat import get_next_speaker as next_speaker
    return next_speaker(chat_id)


@mcp.tool()
def detect_consensus(chat_id: str) -> dict:
    """Detect consensus in group chat (with hallucination warning)"""
    from group_chat import detect_consensus as detect_cons
    return detect_cons(chat_id)


@mcp.tool()
def get_chat_synthesis(chat_id: str) -> dict:
    """Get synthesized summary of group chat"""
    from group_chat import get_chat_synthesis as get_synth
    return get_synth(chat_id)


@mcp.tool()
def should_halt_debate(chat_id: str) -> dict:
    """Check if debate should halt"""
    from group_chat import should_halt_debate as check_halt
    return check_halt(chat_id)


@mcp.tool()
def validate_conversation(
    messages: list,
    level: str = "conversation",
) -> dict:
    """Validate conversation flow and quality"""
    from flow_validation import validate_conversation as validate
    return validate(messages, level)


@mcp.tool()
def validate_and_save(
    validation_id: str,
    messages: list,
    level: str = "conversation",
) -> dict:
    """Validate conversation and save report"""
    from flow_validation import validate_and_save as validate_save
    return validate_save(validation_id, messages, level)


@mcp.tool()
def check_context_loss(messages: list) -> dict:
    """Check if conversation lost earlier context"""
    from flow_validation import check_context_loss as check_loss
    return check_loss(messages)


@mcp.tool()
def detect_conversation_loops(messages: list) -> dict:
    """Detect repetitive loops in conversation"""
    from flow_validation import detect_conversation_loops as detect_loops
    return detect_loops(messages)


@mcp.tool()
def validate_factual_grounding(message: str) -> dict:
    """Check if message is factually grounded"""
    from flow_validation import validate_factual_grounding as validate_facts
    return validate_facts(message)


@mcp.tool()
def add_conversation_to_analytics(
    conversation_id: str,
    agent_id: str,
    messages: list,
) -> dict:
    """Add conversation to analytics system"""
    from analytics import add_conversation_to_analytics as add_conv_analytics
    return add_conv_analytics(conversation_id, agent_id, messages)


@mcp.tool()
def get_agent_dashboard(agent_id: str) -> dict:
    """Get analytics dashboard for agent"""
    from analytics import get_agent_dashboard as get_dash
    return get_dash(agent_id)


@mcp.tool()
def get_system_dashboard() -> dict:
    """Get system-wide analytics dashboard"""
    from analytics import get_system_dashboard as get_sys_dash
    return get_sys_dash()


@mcp.tool()
def get_agent_analytics(agent_id: str) -> dict:
    """Get detailed analytics for agent"""
    from analytics import get_agent_analytics as get_analytics
    return get_analytics(agent_id)


@mcp.tool()
def get_trend_analysis(agent_id: str, days: int = 7) -> dict:
    """Get performance trends for agent"""
    from analytics import get_trend_analysis as get_trends
    return get_trends(agent_id, days)


@mcp.tool()
def record_agent_metric(
    agent_id: str,
    metric_type: str,
    value: float,
    metadata: dict = None,
) -> dict:
    """Record metric for agent"""
    from analytics import record_agent_metric as record_metric
    return record_metric(agent_id, metric_type, value, metadata)


@mcp.tool()
def export_dashboard(agent_id: str = None) -> str:
    """Export dashboard to file"""
    from analytics import export_dashboard as export_dash
    return export_dash(agent_id)


def run():
    """Start the MCP server"""
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(mcp.app, host="127.0.0.1", port=8001)


if __name__ == "__main__":
    run()
