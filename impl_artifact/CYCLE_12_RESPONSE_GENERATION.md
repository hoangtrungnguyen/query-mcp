# Cycle 12: Response Generation & Ranking (Epics 59-63)

## Epic 59: Response Generation Engine
**File:** `response_generation.py`
**Purpose:** Generate contextually appropriate responses
**Core Classes:**
- `GenerationStrategy` (Enum): TEMPLATE_BASED, RULE_BASED, LEARNED, HYBRID
- `ResponseType` (Enum): INFORMATIVE, CLARIFYING, CONFIRMING, SUGGESTING, INSTRUCTIONAL, EMPATHETIC
- `ResponseTemplate`: Template pattern with slots and applicability conditions
- `ResponseContext`: Complete context for generation (state, intent, knowledge level, goals, constraints)
- `CandidateResponse`: Generated response with confidence and quality scores
- `ResponseGenerator`: Generates candidates via template/rule-based approaches
- `ResponseAnalyzer`: Analyzes relevance, informativeness, coherence, constraint satisfaction, adaptation
- `GenerationEngine`: Orchestrates generation and analysis, returns scored candidates
- `GenerationManager`: Manages engines across conversations

## Epic 60: Reference Resolution
**File:** `reference_resolution.py`
**Purpose:** Resolve pronouns and entity references across turns
**Core Classes:**
- `ReferenceType` (Enum): PRONOUN, DEFINITE_DESCRIPTION, DEMONSTRATIVE, ELLIPSIS, PROPER_NOUN
- `PronounType` (Enum): PERSONAL, POSSESSIVE, REFLEXIVE, DEMONSTRATIVE_PRON
- `ReferenceCandidate`: Possible referent with likelihood based on gender/number/distance
- `ResolvedReference`: Reference with identified referent and confidence
- `EntityMention`: Entity occurrence with turn, position, gender, number, animacy
- `ReferenceChain`: Chain of mentions linked to same entity
- `ReferenceResolver`: Pronoun antecedent finding, definite description matching, demonstrative resolution
- `ReferenceTracker`: Maintains chains and resolutions across turns
- `ReferenceManager`: Manages trackers across conversations

## Epic 61: Turn-Taking Management
**File:** `turn_taking_management.py`
**Purpose:** Model and enforce conversational turn-taking protocols
**Core Classes:**
- `TurnState` (Enum): FLOOR_AVAILABLE, USER_SPEAKING, ASSISTANT_SPEAKING, SIMULTANEOUS, PAUSE
- `TransitionType` (Enum): SMOOTH, OVERLAP, INTERRUPTION, HOLD
- `TurnBoundary`: Point where turn exchange can occur with syntactic/prosodic cues
- `FloorControl`: Current floor holder with duration and turn metrics
- `TurnTakingRule`: Convention for turn exchange with conditions and actions
- `TurnTransition`: Record of turn change with type and latency
- `TurnBoundaryDetector`: Identifies turn boundaries from linguistic cues (questions, discourse markers)
- `OverlapHandler`: Detects and resolves simultaneous speech
- `TurnTakingManager`: Enforces protocol, tracks transitions, validates rules
- `TurnTakingCoordinator`: Manages managers across conversations

## Epic 62: Multi-turn Coherence Tracking
**File:** `coherence_tracking.py`
**Purpose:** Track and measure discourse coherence across turns
**Core Classes:**
- `CoherenceLink` (Enum): ENTITY_CHAIN, TEMPORAL, CAUSAL, RHETORICAL, TOPIC_CONTINUATION, ELLIPSIS
- `EntityChain`: Mentions of entity with pronouns and continuity score (penalized for gaps)
- `TemporalOrdering`: Event ordering relations (BEFORE, AFTER, DURING, SIMULTANEOUS)
- `TopicContinuity`: Topic span with consistency and coherence scores
- `DiscourseSegment`: Turn with text, speaker, entities, topics, events, outgoing links
- `CoherenceAnalyzer`: Analyzes entity chains, temporal ordering, topic continuity
- `CoherenceTracker`: Accumulates segments, computes overall coherence (0-1)
- `CoherenceManager`: Manages trackers across conversations
- **Coherence Computation:** Entity chain continuity (1.0 - gap_penalty), topic consistency (gaps/span), overall (avg of all link strengths)

## Epic 63: Response Ranking Engine
**File:** `response_ranking.py`
**Purpose:** Score and rank candidate responses for selection
**Core Classes:**
- `RankingCriterion` (Enum): RELEVANCE, SAFETY, STYLE_MATCH, GOAL_ALIGNMENT, ENGAGEMENT, INFORMATIVENESS, CLARITY, CONCISENESS
- `CriterionScore`: Per-criterion score (0-1) with confidence and evidence
- `RankedResponse`: Response with overall score, position, criterion breakdown, justification
- `RankingContext`: Context for ranking (intent, state, knowledge level, goals, constraints, previous)
- `RankingModel`: Computes criterion scores (intent match, harm detection, goal overlap, word count, sentence length, engagement markers) and weighted overall
- **Weighting:** RELEVANCE(0.25), SAFETY(0.20), GOAL_ALIGNMENT(0.15), INFORMATIVENESS(0.15), CLARITY(0.10), ENGAGEMENT(0.10), STYLE_MATCH(0.03), CONCISENESS(0.02)
- `RankingExplainer`: Generates human-readable explanations of rankings and comparisons
- `RankingEngine`: Ranks response sets, returns sorted list with positions
- `RankingManager`: Manages engines across conversations
