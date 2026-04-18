"""Negotiation framework: model offers, counteroffers, trade-offs, and principled negotiation"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

NEGOTIATION_DIR = Path.home() / ".memory-mcp" / "negotiation-engine"
NEGOTIATION_DIR.mkdir(exist_ok=True, parents=True)


class NegotiationStage(Enum):
    """Stage of negotiation"""
    OPENING = "opening"  # Initial positions stated
    EXPLORATION = "exploration"  # Understanding interests, exploring options
    BARGAINING = "bargaining"  # Making/receiving offers
    AGREEMENT = "agreement"  # Agreement reached
    BREAKDOWN = "breakdown"  # Negotiation failed


class OfferType(Enum):
    """Type of offer"""
    INITIAL = "initial"  # First offer
    COUNTEROFFER = "counteroffer"  # Response to offer
    COMPROMISE = "compromise"  # Move toward middle ground
    PACKAGE = "package"  # Multi-dimensional offer
    ULTIMATUM = "ultimatum"  # Take-it-or-leave-it


@dataclass
class Dimension:
    """Negotiation dimension (what's being negotiated)"""
    dimension_id: str
    name: str  # e.g., "price", "timeline", "scope"
    agent_value: float  # Agent's current position (0-1 scale)
    user_value: float  # User's current position
    importance: float  # How important to reach agreement on this (0-1)
    tradeoff_willing: bool  # Can trade off this dimension
    
    def to_dict(self) -> Dict:
        """Serialize dimension"""
        return {
            "dimension_id": self.dimension_id,
            "name": self.name,
            "agent_value": round(self.agent_value, 2),
            "user_value": round(self.user_value, 2),
            "gap": round(abs(self.agent_value - self.user_value), 2),
        }


@dataclass
class Offer:
    """Single offer in negotiation"""
    offer_id: str
    offer_type: OfferType
    maker: str  # "agent" or "user"
    dimensions: List[Dimension]  # Current values for each dimension
    rationale: str  # Why this offer
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Serialize offer"""
        return {
            "offer_id": self.offer_id,
            "type": self.offer_type.value,
            "maker": self.maker,
            "dimensions": len(self.dimensions),
        }


@dataclass
class TradeoffAnalysis:
    """Analysis of trade-off between dimensions"""
    tradeoff_id: str
    dimension_a: str
    dimension_b: str
    value_a_move: float  # How much A moves
    value_b_move: float  # How much B moves
    joint_gain: float  # Benefit of this trade-off (0-1)
    confidence: float  # How confident in this being good trade-off

    def to_dict(self) -> Dict:
        """Serialize analysis"""
        return {
            "tradeoff_id": self.tradeoff_id,
            "between": f"{self.dimension_a},{self.dimension_b}",
            "joint_gain": round(self.joint_gain, 2),
            "confidence": round(self.confidence, 2),
        }


class NegotiationEngine:
    """Model and conduct negotiations"""

    def __init__(self):
        self.dimensions: Dict[str, Dimension] = {}
        self.offers: List[Offer] = []
        self.stage: NegotiationStage = NegotiationStage.OPENING
        self.agreements: Dict[str, float] = {}

    def add_dimension(
        self,
        name: str,
        agent_value: float,
        user_value: float,
        importance: float = 0.5,
        tradeoff_willing: bool = True,
    ) -> Dimension:
        """Add negotiation dimension"""
        dimension = Dimension(
            dimension_id=f"dim_{len(self.dimensions)}",
            name=name,
            agent_value=agent_value,
            user_value=user_value,
            importance=importance,
            tradeoff_willing=tradeoff_willing,
        )
        self.dimensions[dimension.dimension_id] = dimension
        return dimension

    def make_offer(
        self,
        maker: str,
        offer_type: OfferType,
        dimension_values: Dict[str, float],
        rationale: str,
    ) -> Offer:
        """Make offer with current dimension values"""
        # Update dimensions with offered values
        updated_dims = []
        for dim_id, dim in self.dimensions.items():
            dim_copy = Dimension(
                dimension_id=dim.dimension_id,
                name=dim.name,
                agent_value=dimension_values.get(dim.name, dim.agent_value) if maker == "agent" else dim.agent_value,
                user_value=dimension_values.get(dim.name, dim.user_value) if maker == "user" else dim.user_value,
                importance=dim.importance,
                tradeoff_willing=dim.tradeoff_willing,
            )
            updated_dims.append(dim_copy)

        offer = Offer(
            offer_id=f"offer_{len(self.offers)}",
            offer_type=offer_type,
            maker=maker,
            dimensions=updated_dims,
            rationale=rationale,
        )
        self.offers.append(offer)
        self.stage = NegotiationStage.BARGAINING
        return offer

    def analyze_tradeoff_opportunity(self) -> Optional[TradeoffAnalysis]:
        """Analyze opportunity to trade off between dimensions"""
        if len(self.dimensions) < 2:
            return None

        dims = list(self.dimensions.values())
        
        # Find dimensions where moving on one helps both parties
        best_tradeoff = None
        best_gain = 0

        for i, dim_a in enumerate(dims):
            for dim_b in dims[i+1:]:
                if not (dim_a.tradeoff_willing and dim_b.tradeoff_willing):
                    continue

                # If agent wants higher on A, user wants higher on B
                gap_a = abs(dim_a.agent_value - dim_a.user_value)
                gap_b = abs(dim_b.agent_value - dim_b.user_value)

                # Trade-off value: combined gap reduction
                joint_gain = (gap_a + gap_b) / 2 * 0.5  # Move toward each other

                if joint_gain > best_gain:
                    best_gain = joint_gain
                    best_tradeoff = TradeoffAnalysis(
                        tradeoff_id=f"trade_{i}_{i+1}",
                        dimension_a=dim_a.name,
                        dimension_b=dim_b.name,
                        value_a_move=0.1 * (1 if dim_a.agent_value > dim_a.user_value else -1),
                        value_b_move=0.1 * (1 if dim_b.user_value > dim_b.agent_value else -1),
                        joint_gain=joint_gain,
                        confidence=0.6,
                    )

        return best_tradeoff

    def check_agreement_possible(self) -> bool:
        """Check if agreement is possible (convergence on all dimensions)"""
        for dim in self.dimensions.values():
            gap = abs(dim.agent_value - dim.user_value)
            if gap > 0.2:  # >0.2 gap = no agreement on this dimension
                return False
        return True

    def suggest_principled_move(self) -> Dict[str, Any]:
        """Suggest next move based on principled negotiation"""
        suggestions = {
            "interests": "Ask user about underlying interests rather than positions",
            "creative_options": "Generate options that satisfy both interests",
            "objective_criteria": "Propose objective standards for evaluation",
            "walkaway": "Know your BATNA (best alternative to negotiated agreement)",
        }

        # Analyze current gap
        total_gap = sum(abs(d.agent_value - d.user_value) for d in self.dimensions.values())
        avg_gap = total_gap / len(self.dimensions) if self.dimensions else 0

        if avg_gap > 0.5:
            return {
                "suggestion": "Large gap detected. Focus on understanding interests, not positions.",
                "action": "Ask: 'What's important about X?' rather than 'Agree to my value of X'",
                "principles": suggestions,
            }
        else:
            return {
                "suggestion": "Gaps narrowing. Focus on creative options for final agreement.",
                "action": "Suggest trade-offs and package deals",
                "principles": suggestions,
            }

    def get_negotiation_state(self) -> Dict[str, Any]:
        """Get full negotiation state"""
        return {
            "stage": self.stage.value,
            "offers_made": len(self.offers),
            "dimensions": {d.name: d.to_dict() for d in self.dimensions.values()},
            "agreement_possible": self.check_agreement_possible(),
            "agreements": self.agreements,
        }


class NegotiationManager:
    """Manage negotiations across conversations"""

    def __init__(self):
        self.engines: Dict[str, NegotiationEngine] = {}

    def create_engine(self, engine_id: str) -> NegotiationEngine:
        """Create negotiation engine"""
        engine = NegotiationEngine()
        self.engines[engine_id] = engine
        return engine

    def get_engine(self, engine_id: str) -> Optional[NegotiationEngine]:
        """Get engine"""
        return self.engines.get(engine_id)


negotiation_manager = NegotiationManager()


def create_negotiation_engine(engine_id: str) -> dict:
    """Create negotiation engine"""
    engine = negotiation_manager.create_engine(engine_id)
    return {"engine_id": engine_id, "created": True}


def add_dimension(
    engine_id: str,
    name: str,
    agent_value: float,
    user_value: float,
    importance: float = 0.5,
) -> dict:
    """Add negotiation dimension"""
    engine = negotiation_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    dim = engine.add_dimension(name, agent_value, user_value, importance)
    return dim.to_dict()


def make_offer(
    engine_id: str,
    maker: str,
    offer_type: str,
    dimension_values: dict,
    rationale: str,
) -> dict:
    """Make offer"""
    engine = negotiation_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    try:
        otype = OfferType(offer_type)
        offer = engine.make_offer(maker, otype, dimension_values, rationale)
        return offer.to_dict()
    except ValueError:
        return {"error": f"Invalid offer type: {offer_type}"}


def analyze_tradeoff(engine_id: str) -> dict:
    """Analyze tradeoff opportunity"""
    engine = negotiation_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    tradeoff = engine.analyze_tradeoff_opportunity()
    if not tradeoff:
        return {"tradeoff_found": False}

    return {
        "tradeoff_found": True,
        "tradeoff": tradeoff.to_dict(),
    }


def get_negotiation_state(engine_id: str) -> dict:
    """Get negotiation state"""
    engine = negotiation_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    return engine.get_negotiation_state()


if __name__ == "__main__":
    engine = NegotiationEngine()

    engine.add_dimension("price", 100, 80, 0.8)
    engine.add_dimension("timeline", 0.3, 0.7, 0.6)

    offer = engine.make_offer("agent", OfferType.INITIAL, {"price": 95, "timeline": 0.4}, "Meeting in middle")

    tradeoff = engine.analyze_tradeoff_opportunity()
    if tradeoff:
        print(f"Tradeoff: {tradeoff.to_dict()}")

    state = engine.get_negotiation_state()
    print(f"State: {json.dumps(state, indent=2)}")
