"""Pragmatic reasoning and implicature detection"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

PRAGMATIC_DIR = Path.home() / ".memory-mcp" / "pragmatic-reasoning"
PRAGMATIC_DIR.mkdir(exist_ok=True, parents=True)


class SpeechAct(Enum):
    """Speech acts (Searle's taxonomy)"""
    ASSERTION = "assertion"  # Declare something true
    PROMISE = "promise"  # Commit to future action
    REQUEST = "request"  # Ask for action
    QUESTION = "question"  # Ask for information
    COMMAND = "command"  # Order action
    THANKS = "thanks"  # Express gratitude
    APOLOGY = "apology"  # Express regret


class ImplicatureType(Enum):
    """Types of implicatures"""
    CONVENTIONAL = "conventional"  # Embedded in meaning
    CONVERSATIONAL = "conversational"  # From context
    SCALAR = "scalar"  # From quantity scales (some→not all)
    GENERALIZED = "generalized"  # Default from utterance
    PARTICULARIZED = "particularized"  # From specific context


@dataclass
class SpeechActInterpretation:
    """Interpretation of speech act"""
    act_id: str
    text: str
    primary_act: SpeechAct
    secondary_acts: List[SpeechAct] = field(default_factory=list)
    confidence: float = 0.8
    pragmatic_force: str = ""  # E.g., "polite request", "insistent demand"
    intended_effect: str = ""  # What speaker hopes to achieve
    conditions: List[str] = field(default_factory=list)  # Success conditions

    def to_dict(self) -> Dict:
        """Serialize interpretation"""
        return {
            "act_id": self.act_id,
            "primary": self.primary_act.value,
            "secondary": [a.value for a in self.secondary_acts],
            "confidence": round(self.confidence, 2),
        }


@dataclass
class ImplicatureDetection:
    """Detected implicature"""
    implicature_id: str
    text: str
    implicature_type: ImplicatureType
    literal_meaning: str
    implied_meaning: str
    confidence: float
    cues: List[str] = field(default_factory=list)  # Evidence for implicature

    def to_dict(self) -> Dict:
        """Serialize detection"""
        return {
            "implicature_id": self.implicature_id,
            "type": self.implicature_type.value,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class ScalarImplicature:
    """Scalar implicature (some implies not all)"""
    implicature_id: str
    scalar_term: str  # E.g., "some", "warm", "good"
    scale: List[str]  # Ordered set (e.g., ["some", "most", "all"])
    asserted: str  # What's explicitly said (e.g., "some")
    implicated: str  # What's implied (e.g., "not all")
    confidence: float = 0.85

    def to_dict(self) -> Dict:
        """Serialize implicature"""
        return {
            "implicature_id": self.implicature_id,
            "scalar_term": self.scalar_term,
            "confidence": round(self.confidence, 2),
        }


class SpeechActClassifier:
    """Classify speech acts"""

    SPEECH_ACT_CUES = {
        SpeechAct.ASSERTION: ["believe", "claim", "it is", "we know", "likely"],
        SpeechAct.PROMISE: ["will", "promise", "guarantee", "commit", "pledge"],
        SpeechAct.REQUEST: ["please", "can you", "could you", "would you", "can I"],
        SpeechAct.QUESTION: ["?", "what", "where", "when", "how", "why"],
        SpeechAct.COMMAND: ["must", "should", "need to", "have to", "do"],
        SpeechAct.THANKS: ["thank", "thanks", "appreciate", "grateful"],
        SpeechAct.APOLOGY: ["sorry", "apologize", "excuse", "regret"],
    }

    @staticmethod
    def classify(text: str) -> SpeechActInterpretation:
        """Classify speech act"""
        text_lower = text.lower()

        # Score each act
        act_scores = {}
        for act, cues in SpeechActClassifier.SPEECH_ACT_CUES.items():
            matches = sum(1 for cue in cues if cue in text_lower)
            act_scores[act] = matches

        # Get primary act
        primary_act = max(act_scores.items(), key=lambda x: x[1])[0]

        # Get secondary acts
        sorted_acts = sorted(act_scores.items(), key=lambda x: x[1], reverse=True)
        secondary = [act for act, score in sorted_acts[1:3] if score > 0]

        # Determine pragmatic force
        force = "polite" if "please" in text_lower else "direct"

        interpretation = SpeechActInterpretation(
            act_id=f"act_{int(datetime.now().timestamp())}",
            text=text,
            primary_act=primary_act,
            secondary_acts=secondary,
            confidence=0.75,
            pragmatic_force=force,
            intended_effect="achieve primary communicative goal",
        )

        return interpretation


class ImplicatureDetector:
    """Detect implicatures in utterances"""

    # Scalar implicature scales
    SCALAR_SCALES = {
        "all": ["some", "most", "all"],
        "some": ["some", "most", "all"],
        "good": ["bad", "mediocre", "good", "excellent"],
        "warm": ["cold", "cool", "warm", "hot"],
        "believe": ["possible", "likely", "believe", "know"],
    }

    @staticmethod
    def detect_scalar_implicature(text: str) -> List[ScalarImplicature]:
        """Detect scalar implicatures"""
        implicatures = []
        text_lower = text.lower()

        for scalar_term, scale in ImplicatureDetector.SCALAR_SCALES.items():
            if scalar_term in text_lower:
                # Find position in scale
                pos = scale.index(scalar_term) if scalar_term in scale else len(scale) - 1

                # Implicature: not the higher terms
                if pos < len(scale) - 1:
                    higher_terms = scale[pos + 1:]
                    implied = f"not {higher_terms[-1]}"

                    implicature = ScalarImplicature(
                        implicature_id=f"scalar_{len(implicatures)}",
                        scalar_term=scalar_term,
                        scale=scale,
                        asserted=scalar_term,
                        implicated=implied,
                        confidence=0.8,
                    )
                    implicatures.append(implicature)

        return implicatures

    @staticmethod
    def detect_conversational_implicature(text: str) -> List[ImplicatureDetection]:
        """Detect conversational implicatures"""
        implicatures = []

        # Detect evasion (indirect answer suggests something wrong)
        if "?" not in text and len(text.split()) < 5:
            implicature = ImplicatureDetection(
                implicature_id=f"conv_{len(implicatures)}",
                text=text,
                implicature_type=ImplicatureType.CONVERSATIONAL,
                literal_meaning=text,
                implied_meaning="might be avoiding direct answer",
                confidence=0.6,
                cues=["brief response", "no direct answer to question"],
            )
            implicatures.append(implicature)

        return implicatures


class PragmaticInterpreter:
    """Interpret pragmatic meaning"""

    def __init__(self):
        self.interpretations: Dict[str, SpeechActInterpretation] = {}
        self.implicatures: Dict[str, List[ImplicatureDetection]] = {}
        self.scalar_implicatures: Dict[str, List[ScalarImplicature]] = {}

    def interpret_utterance(self, utterance_id: str, text: str) -> Dict[str, Any]:
        """Full pragmatic interpretation of utterance"""
        # Classify speech act
        interpretation = SpeechActClassifier.classify(text)
        self.interpretations[utterance_id] = interpretation

        # Detect implicatures
        conv_implicatures = ImplicatureDetector.detect_conversational_implicature(text)
        self.implicatures[utterance_id] = conv_implicatures

        # Detect scalar implicatures
        scalar = ImplicatureDetector.detect_scalar_implicature(text)
        self.scalar_implicatures[utterance_id] = scalar

        return {
            "utterance_id": utterance_id,
            "speech_act": interpretation.to_dict(),
            "implicatures": len(conv_implicatures),
            "scalar_implicatures": len(scalar),
            "pragmatic_force": interpretation.pragmatic_force,
        }

    def get_full_interpretation(self, utterance_id: str) -> Optional[Dict[str, Any]]:
        """Get complete pragmatic interpretation"""
        if utterance_id not in self.interpretations:
            return None

        interpretation = self.interpretations[utterance_id]
        implicatures = self.implicatures.get(utterance_id, [])
        scalars = self.scalar_implicatures.get(utterance_id, [])

        return {
            "utterance_id": utterance_id,
            "text": interpretation.text,
            "literal_meaning": interpretation.text,
            "speech_act": interpretation.primary_act.value,
            "pragmatic_force": interpretation.pragmatic_force,
            "implicatures": [i.to_dict() for i in implicatures],
            "scalar_implicatures": [s.to_dict() for s in scalars],
            "intended_effect": interpretation.intended_effect,
        }


class PragmaticManager:
    """Manage pragmatic reasoning"""

    def __init__(self):
        self.interpreters: Dict[str, PragmaticInterpreter] = {}

    def create_interpreter(self, interpreter_id: str) -> PragmaticInterpreter:
        """Create interpreter"""
        interpreter = PragmaticInterpreter()
        self.interpreters[interpreter_id] = interpreter
        return interpreter

    def get_interpreter(self, interpreter_id: str) -> Optional[PragmaticInterpreter]:
        """Get interpreter"""
        return self.interpreters.get(interpreter_id)


# Global manager
pragmatic_manager = PragmaticManager()


# MCP Tools

def create_pragmatic_interpreter(interpreter_id: str) -> dict:
    """Create pragmatic interpreter"""
    interpreter = pragmatic_manager.create_interpreter(interpreter_id)
    return {"interpreter_id": interpreter_id, "created": True}


def interpret_utterance(
    interpreter_id: str,
    utterance_id: str,
    text: str,
) -> dict:
    """Interpret utterance pragmatically"""
    interpreter = pragmatic_manager.get_interpreter(interpreter_id)
    if not interpreter:
        return {"error": "Interpreter not found"}

    return interpreter.interpret_utterance(utterance_id, text)


def get_pragmatic_interpretation(
    interpreter_id: str,
    utterance_id: str,
) -> dict:
    """Get full interpretation"""
    interpreter = pragmatic_manager.get_interpreter(interpreter_id)
    if not interpreter:
        return {"error": "Interpreter not found"}

    interp = interpreter.get_full_interpretation(utterance_id)
    return interp or {"error": "Utterance not found"}


if __name__ == "__main__":
    interpreter = PragmaticInterpreter()

    result = interpreter.interpret_utterance("u1", "Could you possibly help me with this?")
    print(f"Result: {json.dumps(result, indent=2)}")

    full = interpreter.get_full_interpretation("u1")
    print(f"Full: {json.dumps(full, indent=2)}")
