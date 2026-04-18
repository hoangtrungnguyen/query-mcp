# Cycle 1: Core Dialogue Architecture (Epics 1-5)

## Epic 1: Dialogue State Machine
**File:** `dialogue_state.py`
**Purpose:** Manage conversation flow and state transitions
**Core Classes:**
- `DialogueState` (Enum): INIT, UNDERSTANDING, PROBLEM_SOLVING, INFORMATION_SEEKING, NEGOTIATION, DECISION, EXECUTION, CLOSING, ENDED
- `DialogueAct` (Enum): INFORM, REQUEST, CONFIRM, CLARIFY, ACCEPT, REJECT, GREET, FAREWELL, ACKNOWLEDGE, SUGGEST
- `ConversationContext`: Current state, slots, dialogue history, turn count
- `DialoguePolicy`: Manages state transitions based on acts and conditions
- `StateManager`: Orchestrates context creation and turn processing

## Epic 2: Intent Recognition and Classification
**File:** `intent_recognition.py`
**Purpose:** Detect user intents and dialogue acts from text
**Core Classes:**
- `UserIntent` (Enum): SEEK_INFORMATION, REQUEST_ACTION, EXPRESS_OPINION, MAKE_COMPLAINT, GET_RECOMMENDATION, CONFIRM_UNDERSTANDING, CLARIFY, NEGOTIATE, AGREE, DISAGREE
- `DialogueActType` (Enum): STATEMENT, YES_NO_QUESTION, OPEN_QUESTION, COMMAND, REQUEST_INFORMATION, REQUEST_ACTION, ACKNOWLEDGEMENT, AGREEMENT, DISAGREEMENT, APOLOGY, THANK
- `IntentDetection`: Detected primary/secondary intents with confidence and supporting phrases
- `DialogueActDetection`: Detected dialogue act with confidence and intent alignment
- `IntentRecognizer`: Keyword-based intent scoring
- `DialogueActClassifier`: Marker-based dialogue act classification
- `IntentAnalyzer`: Tracks intent/act sequences and patterns

## Epic 3: Information Extraction and Knowledge Graphs
**File:** `information_extraction.py`
**Purpose:** Extract entities, relationships, and facts into structured knowledge
**Core Classes:**
- `EntityType` (Enum): PERSON, ORGANIZATION, LOCATION, PRODUCT, DATE, QUANTITY, CONCEPT
- `RelationType` (Enum): PART_OF, OWNED_BY, WORKS_FOR, LOCATED_IN, RELATED_TO, CAUSES, SIMILAR_TO
- `Entity`: Extracted entity with type, confidence, context, attributes
- `Relationship`: Links between entities with relation type and evidence
- `ExtractedFact`: Structured fact with subject-predicate-object format
- `EntityExtractor`: Pattern-based entity extraction
- `RelationshipExtractor`: Keyword-based relationship extraction
- `FactExtractor`: Sentence-level fact extraction
- `KnowledgeGraph`: Accumulates entities, relationships, facts; provides entity info and graph summary

## Epic 4: Conversation Analytics
**File:** `conversation_analytics.py`
**Purpose:** Measure conversation quality across multiple dimensions
**Core Classes:**
- `QualityDimension` (Enum): RELEVANCE, COMPLETENESS, CLARITY, COHERENCE, ENGAGEMENT, SAFETY, EFFICIENCY, ACCURACY
- `EngagementLevel` (Enum): VERY_LOW, LOW, MEDIUM, HIGH, VERY_HIGH
- `ConversationMetrics`: Turn count, tokens, duration, satisfaction
- `QualityScore`: Dimension-specific quality (0-1) with evidence
- `EngagementMetrics`: Turn times, response times, user lengths, momentum
- `MetricsCalculator`: Computes metrics and quality scores
- `ConversationAnalyzer`: Orchestrates analysis, generates recommendations
- `AnalyticsManager`: Multi-conversation analytics management

## Epic 5: Proactive Assistance and Anticipation
**File:** `proactive_assistance.py`
**Purpose:** Generate proactive offers and anticipate user needs
**Core Classes:**
- `AssistanceType` (Enum): CLARIFICATION, ALTERNATIVE, WARNING, SUGGESTION, CONTEXT, SHORTCUT
- `AssistanceTrigger` (Enum): AMBIGUITY_DETECTED, LOW_CONFIDENCE, SUBOPTIMAL_PATH, COMMON_MISTAKE, USER_HESITATION, CONTEXT_MISMATCH, TIME_INEFFICIENCY
- `UserPattern`: Detected pattern with frequency, confidence, context triggers
- `ProactiveOffer`: Assistance offer with title, description, suggested action, confidence
- `AnticipatedNeed`: Predicted user need with confidence and urgency
- `UserBehaviorAnalyzer`: Detects repeated topics, dissatisfaction, slowness patterns
- `ProactiveAssistanceGenerator`: Generates offers and anticipates needs
- `ProactiveAssistanceEngine`: Coordinates analysis and offer generation
- `ProactiveManager`: Manages engines across conversations
