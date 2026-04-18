"""Proactive assistance and anticipatory agent behavior"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

PROACTIVE_DIR = Path.home() / ".memory-mcp" / "proactive-assistance"
PROACTIVE_DIR.mkdir(exist_ok=True, parents=True)


class AssistanceType(Enum):
    """Types of proactive assistance"""
    CLARIFICATION = "clarification"  # Offer to clarify
    ALTERNATIVE = "alternative"  # Suggest alternative approach
    WARNING = "warning"  # Alert to potential issue
    SUGGESTION = "suggestion"  # Recommend improvement
    CONTEXT = "context"  # Provide relevant context
    SHORTCUT = "shortcut"  # Offer faster path


class AssistanceTrigger(Enum):
    """When to offer assistance"""
    AMBIGUITY_DETECTED = "ambiguity"
    LOW_CONFIDENCE = "low_confidence"
    SUBOPTIMAL_PATH = "suboptimal_path"
    COMMON_MISTAKE = "common_mistake"
    USER_HESITATION = "hesitation"
    CONTEXT_MISMATCH = "context_mismatch"
    TIME_INEFFICIENCY = "time_inefficiency"


@dataclass
class UserPattern:
    """Pattern in user behavior"""
    pattern_id: str
    pattern_type: str
    description: str
    frequency: int = 0
    confidence: float = 0.7
    last_observed: str = ""
    context_triggers: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.last_observed:
            self.last_observed = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize pattern"""
        return {
            "pattern_type": self.pattern_type,
            "frequency": self.frequency,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class ProactiveOffer:
    """Proactive assistance offer"""
    offer_id: str
    assistance_type: AssistanceType
    trigger: AssistanceTrigger
    title: str
    description: str
    suggested_action: str
    confidence: float  # 0-1, how confident this will help
    benefit: str = ""  # What user gains
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize offer"""
        return {
            "offer_id": self.offer_id,
            "type": self.assistance_type.value,
            "trigger": self.trigger.value,
            "title": self.title,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class AnticipatedNeed:
    """Anticipated user need"""
    need_id: str
    prediction: str
    confidence: float
    supporting_evidence: List[str] = field(default_factory=list)
    suggested_resources: List[str] = field(default_factory=list)
    urgency: float = 0.5  # 0-1, how urgent
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize need"""
        return {
            "need_id": self.need_id,
            "prediction": self.prediction[:100],
            "confidence": round(self.confidence, 2),
            "urgency": round(self.urgency, 2),
        }


class UserBehaviorAnalyzer:
    """Analyze user behavior for patterns"""

    def __init__(self):
        self.patterns: Dict[str, UserPattern] = {}
        self.interaction_history: List[Dict[str, Any]] = []

    def record_interaction(
        self,
        user_input: str,
        response: str,
        user_satisfaction: float = 0.5,
        response_time: float = 0.0,
    ):
        """Record user interaction"""
        self.interaction_history.append({
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "response": response,
            "satisfaction": user_satisfaction,
            "response_time": response_time,
        })

    def detect_patterns(self) -> List[UserPattern]:
        """Detect patterns in user behavior"""
        patterns = []

        if not self.interaction_history:
            return patterns

        # Pattern 1: Questions about same topic
        topic_queries = {}
        for interaction in self.interaction_history:
            words = interaction["user_input"].lower().split()
            for word in words:
                if len(word) > 4:
                    topic_queries[word] = topic_queries.get(word, 0) + 1

        for topic, freq in topic_queries.items():
            if freq >= 2:
                pattern = UserPattern(
                    pattern_id=f"pat_topic_{topic}",
                    pattern_type="repeated_topic",
                    description=f"Frequently asks about '{topic}'",
                    frequency=freq,
                    confidence=0.8,
                )
                self.patterns[pattern.pattern_id] = pattern
                patterns.append(pattern)

        # Pattern 2: Low satisfaction responses
        low_satisfaction = [
            i for i in self.interaction_history
            if i["satisfaction"] < 0.4
        ]
        if len(low_satisfaction) > 1:
            pattern = UserPattern(
                pattern_id="pat_dissatisfaction",
                pattern_type="low_satisfaction",
                description=f"Tends to be dissatisfied with responses",
                frequency=len(low_satisfaction),
                confidence=0.7,
            )
            self.patterns[pattern.pattern_id] = pattern
            patterns.append(pattern)

        # Pattern 3: Long response times
        slow_interactions = [
            i for i in self.interaction_history
            if i["response_time"] > 2.0
        ]
        if len(slow_interactions) > 0:
            pattern = UserPattern(
                pattern_id="pat_slowness",
                pattern_type="long_wait_times",
                description=f"Waits long for responses",
                frequency=len(slow_interactions),
                confidence=0.6,
            )
            self.patterns[pattern.pattern_id] = pattern
            patterns.append(pattern)

        return patterns


class ProactiveAssistanceGenerator:
    """Generate proactive assistance offers"""

    @staticmethod
    def generate_offers(
        current_input: str,
        patterns: List[UserPattern],
        conversation_state: Dict[str, Any],
    ) -> List[ProactiveOffer]:
        """Generate proactive offers"""
        offers = []

        # Check for ambiguity
        if len(current_input.split()) < 3:
            offer = ProactiveOffer(
                offer_id=f"offer_ambig_{int(datetime.now().timestamp())}",
                assistance_type=AssistanceType.CLARIFICATION,
                trigger=AssistanceTrigger.AMBIGUITY_DETECTED,
                title="Your question is brief",
                description="Would you like me to ask clarifying questions?",
                suggested_action="ask_clarifications",
                confidence=0.6,
                benefit="Get more relevant answers",
            )
            offers.append(offer)

        # Check for pattern-based suggestions
        for pattern in patterns:
            if pattern.pattern_type == "low_satisfaction":
                offer = ProactiveOffer(
                    offer_id=f"offer_improve_{int(datetime.now().timestamp())}",
                    assistance_type=AssistanceType.ALTERNATIVE,
                    trigger=AssistanceTrigger.SUBOPTIMAL_PATH,
                    title="Alternative approaches available",
                    description="I can try different explanation styles",
                    suggested_action="try_alternatives",
                    confidence=0.7,
                    benefit="Better match your preferences",
                )
                offers.append(offer)

            elif pattern.pattern_type == "long_wait_times":
                offer = ProactiveOffer(
                    offer_id=f"offer_shortcut_{int(datetime.now().timestamp())}",
                    assistance_type=AssistanceType.SHORTCUT,
                    trigger=AssistanceTrigger.TIME_INEFFICIENCY,
                    title="Faster response available",
                    description="I can give quick answers with details on demand",
                    suggested_action="use_short_form",
                    confidence=0.8,
                    benefit="Get answers faster",
                )
                offers.append(offer)

        # Context-based suggestion
        if "how" in current_input.lower() or "why" in current_input.lower():
            offer = ProactiveOffer(
                offer_id=f"offer_context_{int(datetime.now().timestamp())}",
                assistance_type=AssistanceType.CONTEXT,
                trigger=AssistanceTrigger.CONTEXT_MISMATCH,
                title="Background information available",
                description="I can provide context for better understanding",
                suggested_action="provide_context",
                confidence=0.7,
                benefit="Deeper understanding",
            )
            offers.append(offer)

        return offers

    @staticmethod
    def anticipate_needs(
        current_input: str,
        interaction_history: List[Dict[str, Any]],
    ) -> List[AnticipatedNeed]:
        """Anticipate user needs"""
        needs = []

        if not interaction_history:
            return needs

        # If user asks about X, they likely want to know about Y
        topic_sequences = {}

        for i, interaction in enumerate(interaction_history):
            if i < len(interaction_history) - 1:
                curr_words = set(interaction["user_input"].lower().split())
                next_words = set(interaction_history[i+1]["user_input"].lower().split())

                key = tuple(sorted(curr_words & next_words))
                if key:
                    follow_up = next_words - curr_words
                    if follow_up:
                        topic_sequences[key] = list(follow_up)

        # Predict next question
        current_words = set(current_input.lower().split())
        for topic_key, follow_ups in topic_sequences.items():
            if current_words & set(topic_key):
                for follow_up in follow_ups[:2]:
                    need = AnticipatedNeed(
                        need_id=f"need_{follow_up}_{int(datetime.now().timestamp())}",
                        prediction=f"You might want to know about {follow_up}",
                        confidence=0.6,
                        supporting_evidence=["Similar users asked this next"],
                        urgency=0.5,
                    )
                    needs.append(need)

        return needs


class ProactiveAssistanceEngine:
    """Engine for proactive assistance"""

    def __init__(self):
        self.behavior_analyzer = UserBehaviorAnalyzer()
        self.offers_made: Dict[str, ProactiveOffer] = {}
        self.offers_accepted: int = 0
        self.offers_rejected: int = 0

    def process_user_input(
        self,
        user_input: str,
        response: str,
        satisfaction: float = 0.5,
        response_time: float = 0.0,
    ) -> Dict[str, Any]:
        """Process input and generate proactive offers"""
        # Record interaction
        self.behavior_analyzer.record_interaction(
            user_input,
            response,
            satisfaction,
            response_time,
        )

        # Detect patterns
        patterns = self.behavior_analyzer.detect_patterns()

        # Generate offers
        offers = ProactiveAssistanceGenerator.generate_offers(
            user_input,
            patterns,
            {},
        )

        # Anticipate needs
        anticipated = ProactiveAssistanceGenerator.anticipate_needs(
            user_input,
            self.behavior_analyzer.interaction_history,
        )

        for offer in offers:
            self.offers_made[offer.offer_id] = offer

        return {
            "offers": [o.to_dict() for o in offers],
            "anticipated_needs": [n.to_dict() for n in anticipated],
            "patterns_detected": [p.to_dict() for p in patterns],
            "total_offers": len(offers),
            "total_anticipated": len(anticipated),
        }

    def handle_offer_response(
        self,
        offer_id: str,
        accepted: bool,
    ) -> Dict[str, Any]:
        """Handle user response to offer"""
        if offer_id not in self.offers_made:
            return {"error": "Offer not found"}

        offer = self.offers_made[offer_id]

        if accepted:
            self.offers_accepted += 1
            action = offer.suggested_action
        else:
            self.offers_rejected += 1
            action = None

        return {
            "offer_id": offer_id,
            "accepted": accepted,
            "action": action,
            "acceptance_rate": (
                self.offers_accepted / (self.offers_accepted + self.offers_rejected)
                if (self.offers_accepted + self.offers_rejected) > 0 else 0.0
            ),
        }

    def get_effectiveness_metrics(self) -> Dict[str, Any]:
        """Get effectiveness of proactive assistance"""
        total_offers = self.offers_accepted + self.offers_rejected

        return {
            "total_offers_made": len(self.offers_made),
            "accepted": self.offers_accepted,
            "rejected": self.offers_rejected,
            "acceptance_rate": (
                self.offers_accepted / total_offers
                if total_offers > 0 else 0.0
            ),
            "interaction_count": len(self.behavior_analyzer.interaction_history),
            "patterns_detected": len(self.behavior_analyzer.patterns),
        }


class ProactiveManager:
    """Manage proactive assistance across conversations"""

    def __init__(self):
        self.engines: Dict[str, ProactiveAssistanceEngine] = {}

    def create_engine(self, engine_id: str) -> ProactiveAssistanceEngine:
        """Create proactive engine"""
        engine = ProactiveAssistanceEngine()
        self.engines[engine_id] = engine
        return engine

    def get_engine(self, engine_id: str) -> Optional[ProactiveAssistanceEngine]:
        """Get engine"""
        return self.engines.get(engine_id)


# Global manager
proactive_manager = ProactiveManager()


# MCP Tools

def create_proactive_engine(engine_id: str) -> dict:
    """Create proactive assistance engine"""
    engine = proactive_manager.create_engine(engine_id)
    return {"engine_id": engine_id, "created": True}


def process_user_input(
    engine_id: str,
    user_input: str,
    response: str,
    satisfaction: float = 0.5,
) -> dict:
    """Process input and generate proactive offers"""
    engine = proactive_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    return engine.process_user_input(user_input, response, satisfaction)


def respond_to_offer(
    engine_id: str,
    offer_id: str,
    accepted: bool,
) -> dict:
    """Respond to proactive offer"""
    engine = proactive_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    return engine.handle_offer_response(offer_id, accepted)


def get_proactive_metrics(engine_id: str) -> dict:
    """Get proactive assistance metrics"""
    engine = proactive_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    return engine.get_effectiveness_metrics()


if __name__ == "__main__":
    # Test proactive assistance
    engine = ProactiveAssistanceEngine()

    # Process interactions
    engine.process_user_input(
        "How do I learn Python?",
        "You can start with tutorials and practice coding",
        satisfaction=0.7,
    )
    engine.process_user_input(
        "What about Python advanced topics?",
        "Advanced topics include decorators and metaclasses",
        satisfaction=0.6,
    )
    engine.process_user_input(
        "How does Python work internally?",
        "Python uses an interpreter and virtual machine",
        satisfaction=0.5,
    )

    # Process new input with offers
    result = engine.process_user_input(
        "Tell me about Python",
        "Python is a programming language",
        satisfaction=0.8,
    )

    print(f"Offers: {json.dumps(result, indent=2)}")

    # Metrics
    metrics = engine.get_effectiveness_metrics()
    print(f"Metrics: {json.dumps(metrics, indent=2)}")
