# Cycle 13: Advanced Dialogue Management (Epics 64-68)

## Epic 64: Multi-modal Input Processing
**File:** `multimodal_input.py`
**Purpose:** Process non-text inputs and fuse into unified representation
**Core Classes:**
- `InputModality` (Enum): TEXT, IMAGE, AUDIO, STRUCTURED, MIXED
- `ContentType` (Enum): TEXT_CONTENT, VISUAL_DESCRIPTION, AUDIO_TRANSCRIPT, STRUCTURED_DATA, METADATA
- `ExtractedContent`: Content from single modality with confidence
- `ImageInput`: Image with visual description, detected objects, OCR text
- `AudioInput`: Audio with transcript, duration, language, speaker segments
- `StructuredInput`: Structured data (JSON/CSV/table) with schema
- `UnifiedInputRepresentation`: Unified query combining all modalities
- `InputExtractor`: Extracts from text/image/audio/structured separately
- `InputFuser`: Fuses multi-modal inputs into single representation
- `MultimodalProcessor`: Orchestrates extraction and fusion
- `MultimodalManager`: Manages processors across conversations

## Epic 65: Dialogue Repair and Error Correction
**File:** `dialogue_repair.py`
**Purpose:** Detect and repair misunderstandings
**Core Classes:**
- `MisunderstandingType` (Enum): REFERENCE_FAILURE, CONCEPT_MISMATCH, INTENTION_MISMATCH, KNOWLEDGE_GAP, FACTUAL_ERROR, SPEECH_ACT_FAILURE
- `RepairStrategy` (Enum): CLARIFICATION_REQUEST, EXPLICIT_CONFIRMATION, RESTATEMENT, EXEMPLIFICATION, CORRECTION, EXPLANATION
- `Misunderstanding`: Detected misunderstanding with type, turn, nature, evidence, confidence
- `RepairQuestion`: Generated question to resolve misunderstanding with expected responses
- `Correction`: User-provided correction with what was wrong
- `RepairSession`: Full repair dialogue record with questions and corrections
- `MisunderstandingDetector`: Detects confusion, off-topic responses, reference failures
- `RepairGenerator`: Generates clarification questions via templates
- `RepairManager`: Initiates repairs, tracks sessions, applies corrections
- `RepairCoordinator`: Manages repair across conversations

## Epic 66: Pragmatic Reasoning
**File:** `pragmatic_reasoning.py`
**Purpose:** Infer speech acts and detect implicatures
**Core Classes:**
- `SpeechAct` (Enum): ASSERTION, PROMISE, REQUEST, QUESTION, COMMAND, THANKS, APOLOGY
- `ImplicatureType` (Enum): CONVENTIONAL, CONVERSATIONAL, SCALAR, GENERALIZED, PARTICULARIZED
- `SpeechActInterpretation`: Detected speech act with confidence, pragmatic force, intended effect
- `ImplicatureDetection`: Detected implicature with literal/implied meanings
- `ScalarImplicature`: Scalar implicature (some→not all) with scale representation
- `SpeechActClassifier`: Keyword-based classification of speech acts with pragmatic force
- `ImplicatureDetector`: Detects scalar implicatures and conversational implicatures
- `PragmaticInterpreter`: Full interpretation including speech acts, implicatures, scalar implicatures
- `PragmaticManager`: Manages interpretation across conversations

## Epic 67: Dialogue Context Stacking
**File:** `context_stacking.py`
**Purpose:** Manage topic suspension/resumption with context stack
**Core Classes:**
- `ContextStatus` (Enum): ACTIVE, SUSPENDED, CLOSED, INTERRUPTED
- `DialogueContext`: Topic with status, turn range, entities, goals, assumptions, resolution
- `ContextStackFrame`: Context on stack with depth and timestamps
- `ContextTransition`: Topic switch with type (PUSH/POP/SWITCH) and reason
- `ContextStack`: LIFO stack of contexts with full transition history
  - **Operations:** push (suspend previous), pop (reactivate previous), peek, get_path, get_depth
- `ContextStackManager`: Manages stacks across conversations
- **Use Cases:** Interruptions, nested topics (e.g., discuss flight details within vacation planning discussion)

## Epic 68: User Personality Detection
**File:** `personality_detection.py`
**Purpose:** Detect Big Five personality traits and communication style
**Core Classes:**
- `Trait` (Enum): OPENNESS, CONSCIENTIOUSNESS, EXTRAVERSION, AGREEABLENESS, NEUROTICISM
- `PersonalityScore`: Per-trait score (-1 to 1) with confidence and evidence
- `CommunicationStyle`: Formality, verbosity, directness, humor, expertise level
- `UserPersonality`: Full personality profile with trait scores, style, learning style, pace, risk tolerance
- `PersonalityDetector`: 
  - Detects traits from linguistic markers (keywords indicating each trait)
  - Analyzes communication style (formality, verbosity, directness, humor)
  - Detects pace preference from response intervals
- `PersonalityAnalyzer`: Accumulates profiles, provides adaptation suggestions
- `PersonalityManager`: Manages analyzers across users
- **Adaptation Suggestions:** Formality level, verbosity (detailed vs. concise), directness, pace (slow/normal/fast)
