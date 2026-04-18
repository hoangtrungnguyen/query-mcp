# Cycle 14: Conversation Intelligence (Epics 69-73)

## Epic 69: Agent-to-Agent Conversation Protocol
**File:** `agent_conversation.py`
**Purpose:** Enable multi-agent conversation with messaging, handoffs, and role management
**Core Classes:**
- `AgentRole` (Enum): INITIATOR, RESPONDER, MEDIATOR, OBSERVER
- `MessageType` (Enum): REQUEST, RESPONSE, CLARIFICATION, AGREEMENT, REJECTION, HANDOFF, STATUS
- `HandoffReason` (Enum): EXPERTISE, BLOCKED, SPECIALIZATION, OVERLOAD, USER_REQUEST
- `AgentMessage`: Message with sender, receiver, type, content, context, confidence
- `Handoff`: Handoff record with from/to agents, reason, transferred context
- `AgentConversationState`: Conversation state with agents, current speaker, messages, handoffs, goal
- `AgentConversationManager`: Manages agent registries, conversations, messaging
- `AgentRole`: INITIATOR (starts), RESPONDER (replies), MEDIATOR (facilitates), OBSERVER (monitors)

## Epic 70: Goal Introspection and Assumption Tracking
**File:** `goal_introspection.py`
**Purpose:** Diagnose goal failures through assumption and decision tracking
**Core Classes:**
- `GoalStatus` (Enum): PENDING, IN_PROGRESS, ACHIEVED, FAILED, ABANDONED
- `BlockingIssue` (Enum): MISSING_INFORMATION, USER_DISAGREEMENT, TECHNICAL_LIMITATION, CONTEXT_MISMATCH, ASSUMPTION_VIOLATION, RESOURCE_CONSTRAINT
- `AssumptionTrack`: Assumption with statement, confidence, violation detection
- `DecisionPoint`: Key decision with options, chosen option, reasoning, confidence
- `GoalPath`: Goal journey with assumptions, decisions, issues, recovery suggestions
- `AssumptionValidator`: Detects assumption violations via evidence contradiction
- `GoalIntrospectionEngine`: Tracks goals, assumptions, decisions; diagnoses failures
- **Recovery:** Identifies violated assumptions, low-confidence decisions, missing info

## Epic 71: Context Persistence and Compression
**File:** `context_persistence.py`
**Purpose:** Compress context across deep conversations to preserve critical information
**Core Classes:**
- `ImportanceLevel` (Enum): CRITICAL, HIGH, MEDIUM, LOW
- `CompressionStrategy` (Enum): SUMMARIZE, EXTRACT, ABSTRACT, ELIMINATE
- `ContextElement`: Element with type, importance, reference count, last used turn
- `ContextCache`: Collection of elements with token tracking and compression state
- `ContextCompressor`: Compresses elements by importance; keeps 70% (summarize) to 0% (eliminate)
- `ContextManager`: Manages element caching, compression, recovery
- **Token Est.:** ~4 characters per token
- **Recovery:** Reconstruct context at specific turn by selecting pre-turn elements

## Epic 72: Adaptive Clarification Learning
**File:** `adaptive_clarification.py`
**Purpose:** Learn which clarification styles work best for individual users
**Core Classes:**
- `ClarificationStyle` (Enum): DIRECTIVE, SUGGESTIVE, EXPLORATORY, EXAMPLE_BASED, CONFIRMATION
- `ClarificationAttempt`: Question asked with style, outcome, clarity improvement
- `StylePreference`: Per-style success rate and confidence (sqrt-based confidence growth)
- `AdaptiveProfile`: User profile with style preferences, preferred style, avoid styles, per-topic strategies
- `AdaptiveClarificationEngine`: Records attempts, learns preferences, recommends styles
- **Learning:** Success rate tracking, per-topic strategy specialization (e.g., "functions" → EXAMPLE_BASED)
- **Avoid Styles:** Identified when success <40% and confidence >30%

## Epic 73: Dialogue Equilibrium Detection
**File:** `dialogue_equilibrium.py`
**Purpose:** Detect mid-conversation preference shifts and recommend rebalancing
**Core Classes:**
- `DialgueDimension` (Enum): FORMALITY, PACE, DIRECTNESS, ENGAGEMENT, EXPLANATION_DEPTH, HUMOR
- `EquilibriumStatus` (Enum): BALANCED, DRIFT_AGENT_FORMAL, DRIFT_AGENT_CASUAL, DRIFT_USER, OSCILLATION, CONVERGING
- `DimensionMeasure`: Agent value vs. user preference with difference score
- `EquilibriumSnapshot`: Measurement at turn with status and overall distance
- `Rebalance`: Recommended adjustment to dimension with effectiveness tracking
- `EquilibriumDetector`: Analyzes recent responses for preference signals (formal_words, casual_words, fast_words, slow_words)
- **Rebalancing:** When agent-user difference >0.3 on any dimension, recommend 0.5× adjustment

**Integration:** Epics 69-73 enable agent communication, goal diagnosis, context management, style learning, and dynamic rebalancing
