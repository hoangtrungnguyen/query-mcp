"""Advanced reasoning patterns: chain-of-thought, tree-of-thought, and meta-reasoning"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

REASONING_DIR = Path.home() / ".memory-mcp" / "reasoning"
REASONING_DIR.mkdir(exist_ok=True, parents=True)


class ReasoningStrategy(Enum):
    """Problem-solving approaches"""
    CHAIN_OF_THOUGHT = "chain_of_thought"  # Linear reasoning steps
    TREE_OF_THOUGHT = "tree_of_thought"  # Explore multiple paths
    GRAPH_OF_THOUGHT = "graph_of_thought"  # Non-linear reasoning
    DECOMPOSITION = "decomposition"  # Break into subproblems
    ANALOGY = "analogy"  # Reason by analogy


class ConfidenceLevel(Enum):
    """Confidence in reasoning steps"""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.95


@dataclass
class ReasoningStep:
    """Single step in reasoning chain"""
    step_id: str
    step_number: int
    description: str
    reasoning_type: str  # "logical", "inductive", "deductive", "abductive"
    conclusion: str
    supporting_facts: List[str] = field(default_factory=list)
    confidence: float = 0.8
    uncertainty: Optional[str] = None  # Expressed doubts
    alternatives: List[str] = field(default_factory=list)  # Alternative conclusions
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize step"""
        return {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "description": self.description,
            "reasoning_type": self.reasoning_type,
            "conclusion": self.conclusion,
            "supporting_facts": self.supporting_facts,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "alternatives": self.alternatives,
            "timestamp": self.timestamp,
        }


@dataclass
class ReasoningChain:
    """Complete chain of reasoning steps"""
    chain_id: str
    problem: str
    strategy: ReasoningStrategy
    steps: List[ReasoningStep] = field(default_factory=list)
    final_conclusion: str = ""
    overall_confidence: float = 0.8
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    @property
    def avg_step_confidence(self) -> float:
        """Average confidence across steps"""
        if not self.steps:
            return 0.0
        return sum(s.confidence for s in self.steps) / len(self.steps)

    def to_dict(self) -> Dict:
        """Serialize chain"""
        return {
            "chain_id": self.chain_id,
            "problem": self.problem,
            "strategy": self.strategy.value,
            "steps": [s.to_dict() for s in self.steps],
            "final_conclusion": self.final_conclusion,
            "overall_confidence": self.overall_confidence,
            "avg_step_confidence": self.avg_step_confidence,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class ReasoningBranch:
    """Single branch in tree of thought"""
    branch_id: str
    parent_branch_id: Optional[str]
    step_number: int
    hypothesis: str
    reasoning: str
    confidence: float
    viable: bool  # Should branch continue?
    children: List[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize branch"""
        return {
            "branch_id": self.branch_id,
            "parent_branch_id": self.parent_branch_id,
            "step_number": self.step_number,
            "hypothesis": self.hypothesis,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "viable": self.viable,
            "children": self.children,
            "timestamp": self.timestamp,
        }


class ChainOfThoughtReasoner:
    """Linear chain-of-thought reasoning"""

    @staticmethod
    def create_chain(
        chain_id: str,
        problem: str,
    ) -> ReasoningChain:
        """Initialize reasoning chain"""
        return ReasoningChain(
            chain_id=chain_id,
            problem=problem,
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
        )

    @staticmethod
    def add_step(
        chain: ReasoningChain,
        description: str,
        reasoning_type: str,
        conclusion: str,
        supporting_facts: List[str] = None,
        confidence: float = 0.8,
    ) -> ReasoningStep:
        """Add reasoning step to chain"""
        step = ReasoningStep(
            step_id=f"step_{len(chain.steps)}",
            step_number=len(chain.steps) + 1,
            description=description,
            reasoning_type=reasoning_type,
            conclusion=conclusion,
            supporting_facts=supporting_facts or [],
            confidence=confidence,
        )

        chain.steps.append(step)
        return step

    @staticmethod
    def finalize_chain(chain: ReasoningChain) -> ReasoningChain:
        """Finalize chain and set overall conclusion"""
        if chain.steps:
            chain.final_conclusion = chain.steps[-1].conclusion
            chain.overall_confidence = chain.avg_step_confidence

        return chain


class TreeOfThoughtReasoner:
    """Explore multiple reasoning branches"""

    def __init__(self):
        self.branches: Dict[str, ReasoningBranch] = {}
        self.root_branch_ids: List[str] = []

    def create_root_branch(
        self,
        branch_id: str,
        hypothesis: str,
        reasoning: str,
    ) -> ReasoningBranch:
        """Create root branch"""
        branch = ReasoningBranch(
            branch_id=branch_id,
            parent_branch_id=None,
            step_number=0,
            hypothesis=hypothesis,
            reasoning=reasoning,
            confidence=0.8,
            viable=True,
        )

        self.branches[branch_id] = branch
        self.root_branch_ids.append(branch_id)
        return branch

    def expand_branch(
        self,
        parent_branch_id: str,
        new_branch_id: str,
        hypothesis: str,
        reasoning: str,
        confidence: float = 0.8,
    ) -> Optional[ReasoningBranch]:
        """Create child branch from parent"""
        if parent_branch_id not in self.branches:
            return None

        parent = self.branches[parent_branch_id]
        branch = ReasoningBranch(
            branch_id=new_branch_id,
            parent_branch_id=parent_branch_id,
            step_number=parent.step_number + 1,
            hypothesis=hypothesis,
            reasoning=reasoning,
            confidence=confidence,
            viable=True,
        )

        self.branches[new_branch_id] = branch
        parent.children.append(new_branch_id)
        return branch

    def prune_branch(self, branch_id: str) -> bool:
        """Mark branch as not viable (prune)"""
        if branch_id not in self.branches:
            return False

        self.branches[branch_id].viable = False
        return True

    def get_best_path(self) -> List[ReasoningBranch]:
        """Get highest-confidence viable path through tree"""
        best_path = []
        best_confidence = 0.0

        def traverse(branch_id: str, path: List[ReasoningBranch]) -> Tuple[List[ReasoningBranch], float]:
            branch = self.branches[branch_id]

            if not branch.viable:
                return [], 0.0

            current_path = path + [branch]

            if not branch.children:
                # Leaf node
                avg_conf = sum(b.confidence for b in current_path) / len(current_path)
                return current_path, avg_conf

            # Explore children
            best_child_path = []
            best_child_conf = 0.0

            for child_id in branch.children:
                child_path, child_conf = traverse(child_id, current_path)
                if child_conf > best_child_conf:
                    best_child_path = child_path
                    best_child_conf = child_conf

            return best_child_path, best_child_conf

        for root_id in self.root_branch_ids:
            path, conf = traverse(root_id, [])
            if conf > best_confidence:
                best_path = path
                best_confidence = conf

        return best_path

    def get_tree_statistics(self) -> Dict[str, Any]:
        """Get statistics about reasoning tree"""
        total_branches = len(self.branches)
        viable_branches = sum(1 for b in self.branches.values() if b.viable)
        pruned_branches = total_branches - viable_branches
        avg_confidence = (
            sum(b.confidence for b in self.branches.values() if b.viable) / viable_branches
            if viable_branches > 0
            else 0
        )

        max_depth = 0
        for root_id in self.root_branch_ids:
            def get_depth(branch_id: str) -> int:
                branch = self.branches[branch_id]
                if not branch.children:
                    return branch.step_number
                return max(get_depth(child) for child in branch.children)
            max_depth = max(max_depth, get_depth(root_id))

        return {
            "total_branches": total_branches,
            "viable_branches": viable_branches,
            "pruned_branches": pruned_branches,
            "avg_confidence": avg_confidence,
            "max_depth": max_depth,
        }


class MetaReasoner:
    """Reason about reasoning quality"""

    @staticmethod
    def validate_chain(chain: ReasoningChain) -> Dict[str, Any]:
        """Validate reasoning chain quality"""
        issues = []

        # Check step coherence
        for i in range(1, len(chain.steps)):
            prev_conclusion = chain.steps[i - 1].conclusion
            curr_description = chain.steps[i].description
            if prev_conclusion not in curr_description:
                issues.append(f"Step {i}: May not follow logically from step {i-1}")

        # Check confidence consistency
        if chain.overall_confidence < 0.6:
            issues.append("Overall confidence is low - consider alternative approaches")

        # Check for circular reasoning
        conclusions = [s.conclusion for s in chain.steps]
        if len(conclusions) != len(set(conclusions)):
            issues.append("Possible circular reasoning detected")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "confidence_level": "high" if chain.overall_confidence > 0.8 else "medium" if chain.overall_confidence > 0.6 else "low",
        }

    @staticmethod
    def estimate_uncertainty(chain: ReasoningChain) -> Dict[str, Any]:
        """Estimate uncertainty in reasoning"""
        low_confidence_steps = [s for s in chain.steps if s.confidence < 0.7]

        uncertainty_factors = []
        if low_confidence_steps:
            uncertainty_factors.append(
                f"{len(low_confidence_steps)} steps with low confidence"
            )

        if len(chain.steps) < 3:
            uncertainty_factors.append("Limited reasoning depth")

        any_alternatives = any(s.alternatives for s in chain.steps)
        if not any_alternatives:
            uncertainty_factors.append("No alternative paths considered")

        return {
            "overall_uncertainty": 1.0 - chain.overall_confidence,
            "uncertainty_sources": uncertainty_factors,
            "recommendation": (
                "High confidence - proceed with conclusion"
                if chain.overall_confidence > 0.8
                else "Consider gathering more information" if chain.overall_confidence > 0.6
                else "Uncertainty is high - explore alternatives"
            ),
        }


class ReasoningSystem:
    """Complete reasoning orchestration"""

    def __init__(self):
        self.chains: Dict[str, ReasoningChain] = {}
        self.tree_reasoner = TreeOfThoughtReasoner()
        self.meta_reasoner = MetaReasoner()

    def create_cot_reasoning(self, problem: str) -> ReasoningChain:
        """Start chain-of-thought reasoning"""
        chain_id = f"cot_{hash(problem)%1000000}"
        chain = ChainOfThoughtReasoner.create_chain(chain_id, problem)
        self.chains[chain_id] = chain
        return chain

    def create_tot_reasoning(self, problem: str) -> Tuple[ReasoningChain, str]:
        """Start tree-of-thought reasoning"""
        chain_id = f"tot_{hash(problem)%1000000}"
        chain = ReasoningChain(
            chain_id=chain_id,
            problem=problem,
            strategy=ReasoningStrategy.TREE_OF_THOUGHT,
        )

        # Create initial root branch
        root_branch = self.tree_reasoner.create_root_branch(
            f"branch_{chain_id}_0",
            hypothesis=f"Exploring: {problem[:50]}",
            reasoning="Initial branch for exploration",
        )

        self.chains[chain_id] = chain
        return chain, root_branch.branch_id

    def validate_reasoning(self, chain_id: str) -> Dict[str, Any]:
        """Validate reasoning quality"""
        if chain_id not in self.chains:
            return {"error": "Chain not found"}

        chain = self.chains[chain_id]
        validation = self.meta_reasoner.validate_chain(chain)
        uncertainty = self.meta_reasoner.estimate_uncertainty(chain)

        return {
            "validation": validation,
            "uncertainty": uncertainty,
            "confidence_score": chain.overall_confidence,
        }

    def get_reasoning_summary(self, chain_id: str) -> Optional[Dict]:
        """Get summary of reasoning"""
        if chain_id not in self.chains:
            return None

        chain = self.chains[chain_id]
        return {
            "problem": chain.problem,
            "strategy": chain.strategy.value,
            "steps_count": len(chain.steps),
            "conclusion": chain.final_conclusion,
            "confidence": chain.overall_confidence,
            "step_summaries": [
                f"Step {s.step_number}: {s.conclusion} (confidence: {s.confidence:.0%})"
                for s in chain.steps
            ],
        }

    def save_reasoning(self, chain_id: str) -> str:
        """Save reasoning to disk"""
        if chain_id not in self.chains:
            return ""

        chain = self.chains[chain_id]
        filepath = REASONING_DIR / f"{chain_id}_reasoning.json"

        with open(filepath, "w") as f:
            json.dump(chain.to_dict(), f, indent=2)

        return str(filepath)


# Global system
reasoning_system = ReasoningSystem()


# MCP Tools (add to memory_server.py)

def create_chain_of_thought(problem: str) -> dict:
    """Create chain-of-thought reasoning"""
    chain = reasoning_system.create_cot_reasoning(problem)
    return {"chain_id": chain.chain_id, "problem": problem}


def add_reasoning_step(
    chain_id: str,
    description: str,
    reasoning_type: str,
    conclusion: str,
) -> dict:
    """Add step to reasoning chain"""
    if chain_id not in reasoning_system.chains:
        return {"error": "Chain not found"}

    chain = reasoning_system.chains[chain_id]
    step = ChainOfThoughtReasoner.add_step(
        chain,
        description,
        reasoning_type,
        conclusion,
    )
    return step.to_dict()


def create_tree_of_thought(problem: str) -> dict:
    """Create tree-of-thought reasoning"""
    chain, root_branch_id = reasoning_system.create_tot_reasoning(problem)
    return {
        "chain_id": chain.chain_id,
        "root_branch_id": root_branch_id,
        "problem": problem,
    }


def validate_reasoning(chain_id: str) -> dict:
    """Validate reasoning quality"""
    return reasoning_system.validate_reasoning(chain_id)


def get_reasoning_summary(chain_id: str) -> dict:
    """Get reasoning summary"""
    summary = reasoning_system.get_reasoning_summary(chain_id)
    return summary or {"error": "Chain not found"}


if __name__ == "__main__":
    # Test reasoning
    system = ReasoningSystem()

    # Create chain-of-thought
    chain = system.create_cot_reasoning("How to optimize database queries?")
    print(f"Chain created: {chain.chain_id}")

    # Add steps
    ChainOfThoughtReasoner.add_step(
        chain,
        "Analyze current query patterns",
        "inductive",
        "Most queries are full table scans",
        ["Observed slow queries"],
        0.9,
    )

    ChainOfThoughtReasoner.add_step(
        chain,
        "Consider indexing strategy",
        "deductive",
        "Add indexes on frequently filtered columns",
        ["Database best practices"],
        0.85,
    )

    ChainOfThoughtReasoner.finalize_chain(chain)

    # Validate
    validation = system.validate_reasoning(chain.chain_id)
    print(f"Validation: {json.dumps(validation, indent=2)}")

    # Get summary
    summary = system.get_reasoning_summary(chain.chain_id)
    print(f"Summary: {json.dumps(summary, indent=2)}")
