"""Dialogue repair: detect and fix communication breakdowns"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

REPAIR_DIR = Path.home() / ".memory-mcp" / "dialogue-repair"
REPAIR_DIR.mkdir(exist_ok=True, parents=True)


class BreakdownType(Enum):
    """Type of communication breakdown"""
    MISUNDERSTANDING = "misunderstanding"  # Parties don't understand each other
    ASSUMPTION_MISMATCH = "assumption_mismatch"  # Different unstated assumptions
    TERM_AMBIGUITY = "term_ambiguity"  # Same word, different meanings
    CONTEXT_DRIFT = "context_drift"  # Topic shifted unexpectedly
    EXPECTATION_GAP = "expectation_gap"  # Different goals/expectations
    INFERENCE_ERROR = "inference_error"  # Wrong deduction from limited info


class RepairStrategy(Enum):
    """How to repair breakdown"""
    CLARIFY = "clarify"  # Ask what was meant
    REPHRASE = "rephrase"  # Say it differently
    ALIGN_CONTEXT = "align_context"  # Sync on shared context
    VALIDATE = "validate"  # Confirm understanding
    RESET = "reset"  # Start fresh on this topic


@dataclass
class BreakdownSignal:
    """Signal indicating a breakdown may exist"""
    signal_type: str  # "contradiction", "silence", "deflection", "repetition"
    confidence: float  # 0-1, how confident breakdown exists
    evidence: str  # What indicates breakdown
    turn_num: int

    def to_dict(self) -> Dict:
        """Serialize signal"""
        return {
            "signal_type": self.signal_type,
            "confidence": round(self.confidence, 2),
            "turn": self.turn_num,
        }


@dataclass
class DiagnosedBreakdown:
    """Diagnosed communication breakdown"""
    breakdown_id: str
    breakdown_type: BreakdownType
    detected_turn: int
    involved_terms: List[str]  # What was misunderstood
    agent_assumption: str  # What agent assumed
    user_evidence: str  # What user said that contradicts
    severity: float  # 0-1, how serious
    confidence: float  # 0-1, diagnosis confidence

    def to_dict(self) -> Dict:
        """Serialize breakdown"""
        return {
            "breakdown_id": self.breakdown_id,
            "type": self.breakdown_type.value,
            "severity": round(self.severity, 2),
            "confidence": round(self.confidence, 2),
        }


@dataclass
class RepairAttempt:
    """Attempt to repair a breakdown"""
    repair_id: str
    breakdown_id: str
    strategy: RepairStrategy
    proposed_action: str  # What to say/do
    turn_proposed: int
    turn_executed: Optional[int] = None
    success: bool = False
    user_response: str = ""

    def to_dict(self) -> Dict:
        """Serialize repair"""
        return {
            "repair_id": self.repair_id,
            "strategy": self.strategy.value,
            "success": self.success,
        }


class BreakdownDetector:
    """Detect communication breakdowns"""

    @staticmethod
    def detect_contradiction(
        previous_statement: str,
        current_statement: str,
        turn_num: int,
    ) -> BreakdownSignal:
        """Detect contradiction between statements"""
        prev_lower = previous_statement.lower()
        curr_lower = current_statement.lower()

        # Simple heuristic: look for negation
        negation_words = ["not", "don't", "doesn't", "no", "never", "can't"]
        contradiction_found = any(
            word in curr_lower for word in negation_words
        ) and not any(word in prev_lower for word in negation_words)

        if contradiction_found:
            return BreakdownSignal(
                signal_type="contradiction",
                confidence=0.7,
                evidence=current_statement[:100],
                turn_num=turn_num,
            )

        return BreakdownSignal(
            signal_type="contradiction",
            confidence=0.0,
            evidence="",
            turn_num=turn_num,
        )

    @staticmethod
    def detect_silence_or_deflection(
        response: str,
        expected_length: int = 20,
        turn_num: int = 0,
    ) -> BreakdownSignal:
        """Detect very short response or topic deflection"""
        is_short = len(response) < expected_length
        evasive_words = ["maybe", "not sure", "let me think", "actually"]
        is_evasive = any(word in response.lower() for word in evasive_words)

        if is_short or is_evasive:
            return BreakdownSignal(
                signal_type="deflection",
                confidence=0.5,
                evidence=response[:50],
                turn_num=turn_num,
            )

        return BreakdownSignal(
            signal_type="deflection",
            confidence=0.0,
            evidence="",
            turn_num=turn_num,
        )

    @staticmethod
    def detect_repetition(
        recent_responses: List[str],
        turn_num: int,
    ) -> BreakdownSignal:
        """Detect repeated questions/topics"""
        if len(recent_responses) < 3:
            return BreakdownSignal(
                signal_type="repetition",
                confidence=0.0,
                evidence="",
                turn_num=turn_num,
            )

        # Simple check: similar topics
        recent_text = " ".join([r.lower() for r in recent_responses[-3:]])
        unique_words = len(set(recent_text.split()))
        total_words = len(recent_text.split())

        if total_words > 0:
            repetition_ratio = 1 - (unique_words / total_words)
            if repetition_ratio > 0.4:
                return BreakdownSignal(
                    signal_type="repetition",
                    confidence=0.6,
                    evidence="High topic repetition",
                    turn_num=turn_num,
                )

        return BreakdownSignal(
            signal_type="repetition",
            confidence=0.0,
            evidence="",
            turn_num=turn_num,
        )


class DialogueRepairEngine:
    """Diagnose and repair dialogue breakdowns"""

    def __init__(self):
        self.breakdowns: Dict[str, DiagnosedBreakdown] = {}
        self.repairs: Dict[str, RepairAttempt] = {}
        self.signal_history: List[BreakdownSignal] = []

    def detect_breakdown_signals(
        self,
        previous_response: Optional[str],
        current_response: str,
        recent_context: List[str],
        turn_num: int,
    ) -> List[BreakdownSignal]:
        """Detect potential breakdown signals"""
        signals = []

        # Check for contradiction
        if previous_response:
            signal = BreakdownDetector.detect_contradiction(
                previous_response,
                current_response,
                turn_num,
            )
            if signal.confidence > 0.3:
                signals.append(signal)

        # Check for deflection
        deflection_signal = BreakdownDetector.detect_silence_or_deflection(
            current_response, turn_num=turn_num
        )
        if deflection_signal.confidence > 0.3:
            signals.append(deflection_signal)

        # Check for repetition
        if recent_context:
            repetition_signal = BreakdownDetector.detect_repetition(
                recent_context, turn_num
            )
            if repetition_signal.confidence > 0.3:
                signals.append(repetition_signal)

        self.signal_history.extend(signals)
        return signals

    def diagnose_breakdown(
        self,
        breakdown_type: BreakdownType,
        involved_terms: List[str],
        agent_assumption: str,
        user_evidence: str,
        severity: float = 0.5,
        turn_num: int = 0,
    ) -> DiagnosedBreakdown:
        """Diagnose a specific breakdown"""
        breakdown = DiagnosedBreakdown(
            breakdown_id=f"bd_{len(self.breakdowns)}",
            breakdown_type=breakdown_type,
            detected_turn=turn_num,
            involved_terms=involved_terms,
            agent_assumption=agent_assumption,
            user_evidence=user_evidence,
            severity=severity,
            confidence=0.7,
        )
        self.breakdowns[breakdown.breakdown_id] = breakdown
        return breakdown

    def recommend_repair(
        self,
        breakdown_id: str,
        turn_num: int,
    ) -> Optional[RepairAttempt]:
        """Recommend repair strategy for breakdown"""
        if breakdown_id not in self.breakdowns:
            return None

        breakdown = self.breakdowns[breakdown_id]

        # Choose strategy based on breakdown type
        strategy_map = {
            BreakdownType.MISUNDERSTANDING: RepairStrategy.CLARIFY,
            BreakdownType.ASSUMPTION_MISMATCH: RepairStrategy.ALIGN_CONTEXT,
            BreakdownType.TERM_AMBIGUITY: RepairStrategy.CLARIFY,
            BreakdownType.CONTEXT_DRIFT: RepairStrategy.ALIGN_CONTEXT,
            BreakdownType.EXPECTATION_GAP: RepairStrategy.VALIDATE,
            BreakdownType.INFERENCE_ERROR: RepairStrategy.REPHRASE,
        }

        strategy = strategy_map.get(breakdown.breakdown_type, RepairStrategy.CLARIFY)

        # Generate proposed action
        if strategy == RepairStrategy.CLARIFY:
            proposed = f"Let me clarify: do you mean {breakdown.involved_terms[0] if breakdown.involved_terms else 'that'}?"
        elif strategy == RepairStrategy.REPHRASE:
            proposed = f"Let me say that differently..."
        elif strategy == RepairStrategy.ALIGN_CONTEXT:
            proposed = f"I want to make sure we're on the same page about {breakdown.involved_terms[0] if breakdown.involved_terms else 'this'}."
        elif strategy == RepairStrategy.VALIDATE:
            proposed = f"Just to confirm: are we both trying to achieve the same goal?"
        else:
            proposed = "Let me approach this fresh."

        repair = RepairAttempt(
            repair_id=f"rep_{len(self.repairs)}",
            breakdown_id=breakdown_id,
            strategy=strategy,
            proposed_action=proposed,
            turn_proposed=turn_num,
        )
        self.repairs[repair.repair_id] = repair
        return repair

    def record_repair_execution(
        self,
        repair_id: str,
        turn_executed: int,
        user_response: str,
        succeeded: bool,
    ):
        """Record execution and outcome of repair"""
        if repair_id not in self.repairs:
            return

        repair = self.repairs[repair_id]
        repair.turn_executed = turn_executed
        repair.user_response = user_response
        repair.success = succeeded

    def get_repair_summary(self) -> Dict[str, Any]:
        """Get summary of detected breakdowns and repairs"""
        if not self.breakdowns:
            return {"breakdowns": 0, "repairs": 0, "success_rate": 0}

        successful_repairs = [r for r in self.repairs.values() if r.success]
        success_rate = (
            len(successful_repairs) / len(self.repairs)
            if self.repairs
            else 0
        )

        return {
            "breakdowns_detected": len(self.breakdowns),
            "repairs_attempted": len(self.repairs),
            "repairs_successful": len(successful_repairs),
            "success_rate": round(success_rate, 2),
            "signals_detected": len(self.signal_history),
        }


class RepairManager:
    """Manage dialogue repair across conversations"""

    def __init__(self):
        self.engines: Dict[str, DialogueRepairEngine] = {}

    def create_engine(self, engine_id: str) -> DialogueRepairEngine:
        """Create repair engine"""
        engine = DialogueRepairEngine()
        self.engines[engine_id] = engine
        return engine

    def get_engine(self, engine_id: str) -> Optional[DialogueRepairEngine]:
        """Get engine"""
        return self.engines.get(engine_id)


# Global manager
repair_manager = RepairManager()


# MCP Tools

def create_repair_engine(engine_id: str) -> dict:
    """Create repair engine"""
    engine = repair_manager.create_engine(engine_id)
    return {"engine_id": engine_id, "created": True}


def detect_breakdown_signals(
    engine_id: str,
    previous_response: Optional[str],
    current_response: str,
    recent_context: list,
    turn_num: int,
) -> dict:
    """Detect breakdown signals"""
    engine = repair_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    signals = engine.detect_breakdown_signals(
        previous_response, current_response, recent_context, turn_num
    )
    return {
        "signals_detected": len(signals),
        "signals": [s.to_dict() for s in signals],
    }


def diagnose_breakdown(
    engine_id: str,
    breakdown_type: str,
    involved_terms: list,
    agent_assumption: str,
    user_evidence: str,
    severity: float = 0.5,
    turn_num: int = 0,
) -> dict:
    """Diagnose breakdown"""
    engine = repair_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    try:
        bd_type = BreakdownType(breakdown_type)
        breakdown = engine.diagnose_breakdown(
            bd_type, involved_terms, agent_assumption, user_evidence, severity, turn_num
        )
        return breakdown.to_dict()
    except ValueError:
        return {"error": f"Invalid breakdown type: {breakdown_type}"}


def recommend_repair(engine_id: str, breakdown_id: str, turn_num: int) -> dict:
    """Get repair recommendation"""
    engine = repair_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    repair = engine.recommend_repair(breakdown_id, turn_num)
    if not repair:
        return {"error": "Breakdown not found"}

    return repair.to_dict()


def record_repair_execution(
    engine_id: str,
    repair_id: str,
    turn_executed: int,
    user_response: str,
    succeeded: bool,
) -> dict:
    """Record repair execution"""
    engine = repair_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    engine.record_repair_execution(repair_id, turn_executed, user_response, succeeded)
    return {"recorded": True}


def get_repair_summary(engine_id: str) -> dict:
    """Get repair summary"""
    engine = repair_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    return engine.get_repair_summary()


if __name__ == "__main__":
    engine = DialogueRepairEngine()

    # Detect signals
    signals = engine.detect_breakdown_signals(
        "I think Python is easy",
        "Actually Python is really hard",
        ["I said Python is easy", "But user said hard"],
        5,
    )

    print(f"Signals: {len(signals)}")

    # Diagnose
    breakdown = engine.diagnose_breakdown(
        BreakdownType.MISUNDERSTANDING,
        ["Python difficulty"],
        "User finds Python easy",
        "User said 'Python is really hard'",
        0.8,
        5,
    )

    # Recommend repair
    repair = engine.recommend_repair(breakdown.breakdown_id, 6)
    print(f"Repair: {repair.proposed_action if repair else 'None'}")

    # Get summary
    summary = engine.get_repair_summary()
    print(f"Summary: {summary}")
