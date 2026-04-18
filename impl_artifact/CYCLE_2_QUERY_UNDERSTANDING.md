# Cycle 2: Query Understanding (Epics 6-10)

## Epic 6: Query Clarification and Ambiguity Detection
**File:** `query_clarification.py`
**Purpose:** Detect and resolve query ambiguities
**Core Classes:**
- `AmbiguityType` (Enum): LEXICAL, REFERENTIAL, STRUCTURAL, SEMANTIC
- `AmbiguousElement`: Identified ambiguous part with type and alternatives
- `ClarificationQuestion`: Generated question to resolve ambiguity with expected answers
- `ExpandedQuery`: Original query with detected ambiguities and resolved versions
- `AmbiguityDetector`: Detects word sense, scope, pronoun, and structural ambiguities
- `ClarificationGenerator`: Generates targeted clarification questions
- `AmbiguityResolver`: Resolves ambiguities given user responses

## Epic 7: Temporal Reasoning and Constraint Satisfaction
**File:** `temporal_reasoning.py`
**Purpose:** Handle temporal expressions and scheduling constraints
**Core Classes:**
- `TimeInterval`: Start/end time with duration and confidence
- `TemporalEvent`: Event with timestamp and relations to other events
- `TemporalConstraint`: Constraint types (BEFORE, AFTER, DURING, etc.) with confidence
- `Schedule`: Collection of events with ordering constraints
- `SchedulingEngine`: Validates constraints, finds valid schedules, detects conflicts
- `TemporalAnalyzer`: Analyzes temporal references in text
- `TemporalManager`: Manages temporal reasoning across conversations

## Epic 8: User Knowledge Level Detection
**File:** `user_knowledge_detection.py`
**Purpose:** Detect user expertise and adapt explanations
**Core Classes:**
- `KnowledgeLevel` (Enum): NOVICE, BEGINNER, INTERMEDIATE, ADVANCED, EXPERT
- `KnowledgeProfile`: User knowledge across domains with evidence
- `KnowledgeDetector`: Analyzes vocabulary, question sophistication, background knowledge
- `AdaptationStrategy`: Defines explanation depth, terminology, examples per level
- `AdaptationEngine`: Generates explanations tailored to detected level
- `KnowledgeManager`: Tracks knowledge per user/conversation

## Epic 9: Goal-Oriented Conversation Planning
**File:** `goal_oriented_planning.py`
**Purpose:** Plan conversations toward defined goals
**Core Classes:**
- `ConversationGoal`: Goal with target state, success criteria, priority
- `ConversationPlan`: Sequence of dialogue acts to achieve goal
- `PlanStep`: Individual action with preconditions, effects, alternatives
- `ProgressTracker`: Monitors goal progress across turns
- `PlanningEngine`: Generates plans, tracks progress, adapts if blocked
- `PlanningManager`: Manages goals and plans per conversation

## Epic 10: Memory Indexing and Search
**File:** `memory_search.py`
**Purpose:** Retrieve relevant past conversations and information
**Core Classes:**
- `SearchResult`: Retrieved conversation segment with relevance score
- `ConversationIndex`: Indexed conversations with multiple search strategies
- `MemoryIndexer`: Builds indices (keyword, semantic, metadata-based)
- `MemorySearchEngine`: Performs keyword/semantic/hybrid searches
- `SearchStrategy` (Enum): KEYWORD, SEMANTIC, HYBRID, METADATA
- `MemoryManager`: Manages memory across system
