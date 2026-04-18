"""Cross-domain knowledge transfer and skill generalization"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

TRANSFER_DIR = Path.home() / ".memory-mcp" / "knowledge-transfer"
TRANSFER_DIR.mkdir(exist_ok=True, parents=True)


class TransferType(Enum):
    """Types of knowledge transfer"""
    ANALOGICAL = "analogical"  # Map structures between domains
    FEATURE_REUSE = "feature_reuse"  # Use same features
    PRINCIPLE_TRANSFER = "principle_transfer"  # Transfer general principles
    SKILL_ADAPTATION = "skill_adaptation"  # Adapt skills to new domain
    PATTERN_RECOGNITION = "pattern_recognition"  # Recognize similar patterns


class DomainSimilarity(Enum):
    """Similarity between domains"""
    IDENTICAL = 1.0
    VERY_SIMILAR = 0.75
    SIMILAR = 0.5
    SOMEWHAT_RELATED = 0.25
    UNRELATED = 0.0


@dataclass
class DomainKnowledge:
    """Knowledge in a specific domain"""
    domain: str
    concepts: List[str]
    skills: List[str]
    patterns: List[str]
    principles: List[str]
    relationships: Dict[str, List[str]] = field(default_factory=dict)  # concept -> related concepts
    learned_at: str = ""

    def __post_init__(self):
        if not self.learned_at:
            self.learned_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize knowledge"""
        return {
            "domain": self.domain,
            "concepts": len(self.concepts),
            "skills": len(self.skills),
            "patterns": len(self.patterns),
            "principles": len(self.principles),
        }


@dataclass
class TransferOpportunity:
    """Opportunity to transfer knowledge between domains"""
    opportunity_id: str
    source_domain: str
    target_domain: str
    transfer_type: TransferType
    similarity_score: float  # 0-1
    applicable_concepts: List[str]  # What can be transferred
    adaptation_required: List[str]  # What needs adjustment
    estimated_benefit: float  # 0-1, how much it helps
    confidence: float  # 0-1, how confident in transfer
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize opportunity"""
        return {
            "opportunity_id": self.opportunity_id,
            "source": self.source_domain,
            "target": self.target_domain,
            "type": self.transfer_type.value,
            "similarity": round(self.similarity_score, 2),
            "concepts_transferable": len(self.applicable_concepts),
            "benefit": round(self.estimated_benefit, 2),
            "confidence": round(self.confidence, 2),
        }


@dataclass
class TransferLog:
    """Record of knowledge transfer"""
    transfer_id: str
    source_domain: str
    target_domain: str
    transferred_knowledge: List[str]
    results: Dict[str, Any]  # What happened
    success: bool
    improvement: float = 0.0  # % improvement in target domain
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize log"""
        return {
            "transfer_id": self.transfer_id,
            "source": self.source_domain,
            "target": self.target_domain,
            "success": self.success,
            "improvement": round(self.improvement, 2),
            "transferred_items": len(self.transferred_knowledge),
        }


class DomainAnalyzer:
    """Analyze domain knowledge and find similarities"""

    @staticmethod
    def calculate_domain_similarity(
        domain1_knowledge: DomainKnowledge,
        domain2_knowledge: DomainKnowledge,
    ) -> Tuple[float, List[str]]:
        """Calculate similarity between domains"""
        # Concept overlap
        concepts_1 = set(domain1_knowledge.concepts)
        concepts_2 = set(domain2_knowledge.concepts)
        concept_overlap = len(concepts_1 & concepts_2) / max(1, len(concepts_1 | concepts_2))

        # Skill overlap
        skills_1 = set(domain1_knowledge.skills)
        skills_2 = set(domain2_knowledge.skills)
        skill_overlap = len(skills_1 & skills_2) / max(1, len(skills_1 | skills_2))

        # Pattern overlap
        patterns_1 = set(domain1_knowledge.patterns)
        patterns_2 = set(domain2_knowledge.patterns)
        pattern_overlap = len(patterns_1 & patterns_2) / max(1, len(patterns_1 | patterns_2))

        # Weighted average (concepts most important)
        similarity = (
            concept_overlap * 0.5 +
            skill_overlap * 0.3 +
            pattern_overlap * 0.2
        )

        # Find transferable knowledge
        transferable = list(concepts_1 & concepts_2)
        transferable.extend(list(skills_1 & skills_2))
        transferable.extend(list(patterns_1 & patterns_2))

        return similarity, transferable

    @staticmethod
    def find_structural_analogies(
        domain1_knowledge: DomainKnowledge,
        domain2_knowledge: DomainKnowledge,
    ) -> List[Tuple[str, str]]:
        """Find structural analogies between domains"""
        analogies = []

        # Map relationships
        for concept1, related1 in domain1_knowledge.relationships.items():
            for concept2, related2 in domain2_knowledge.relationships.items():
                # Check if structure is similar
                if len(related1) == len(related2):
                    analogies.append((concept1, concept2))

        return analogies

    @staticmethod
    def extract_transferable_principles(
        domain_knowledge: DomainKnowledge,
    ) -> List[Dict[str, Any]]:
        """Extract general principles that might transfer"""
        principles_detail = []

        for principle in domain_knowledge.principles:
            principles_detail.append({
                "principle": principle,
                "domain": domain_knowledge.domain,
                "generality": 0.7,  # How general is it
                "applicability_domains": [],  # Will fill when checking other domains
            })

        return principles_detail


class KnowledgeTransferer:
    """Execute knowledge transfer between domains"""

    def __init__(self):
        self.domain_knowledge: Dict[str, DomainKnowledge] = {}
        self.transfer_opportunities: Dict[str, TransferOpportunity] = {}
        self.transfer_logs: List[TransferLog] = []

    def add_domain_knowledge(
        self,
        domain: str,
        concepts: List[str],
        skills: List[str],
        patterns: List[str],
        principles: List[str],
    ) -> DomainKnowledge:
        """Add domain knowledge"""
        knowledge = DomainKnowledge(
            domain=domain,
            concepts=concepts,
            skills=skills,
            patterns=patterns,
            principles=principles,
        )
        self.domain_knowledge[domain] = knowledge
        return knowledge

    def find_transfer_opportunities(
        self,
        source_domain: str,
        target_domain: str,
    ) -> List[TransferOpportunity]:
        """Find opportunities to transfer knowledge"""
        if source_domain not in self.domain_knowledge or target_domain not in self.domain_knowledge:
            return []

        source = self.domain_knowledge[source_domain]
        target = self.domain_knowledge[target_domain]

        opportunities = []

        # Calculate domain similarity
        similarity, transferable = DomainAnalyzer.calculate_domain_similarity(source, target)

        if similarity > 0:
            # Direct transfer of overlapping knowledge
            opp = TransferOpportunity(
                opportunity_id=f"opp_{source_domain}_{target_domain}_1",
                source_domain=source_domain,
                target_domain=target_domain,
                transfer_type=TransferType.FEATURE_REUSE,
                similarity_score=similarity,
                applicable_concepts=transferable,
                adaptation_required=[],
                estimated_benefit=similarity,
                confidence=similarity,
            )
            opportunities.append(opp)

        # Analogical transfer
        analogies = DomainAnalyzer.find_structural_analogies(source, target)
        if analogies:
            analogy_concepts = [a[0] for a in analogies]
            opp = TransferOpportunity(
                opportunity_id=f"opp_{source_domain}_{target_domain}_2",
                source_domain=source_domain,
                target_domain=target_domain,
                transfer_type=TransferType.ANALOGICAL,
                similarity_score=min(1.0, len(analogies) / max(1, len(source.concepts))),
                applicable_concepts=analogy_concepts,
                adaptation_required=[f"Map {c} to target domain" for c in analogy_concepts],
                estimated_benefit=0.5 * similarity,
                confidence=0.6,
            )
            opportunities.append(opp)

        # Principle transfer
        principles = DomainAnalyzer.extract_transferable_principles(source)
        if principles:
            principle_names = [p["principle"] for p in principles]
            opp = TransferOpportunity(
                opportunity_id=f"opp_{source_domain}_{target_domain}_3",
                source_domain=source_domain,
                target_domain=target_domain,
                transfer_type=TransferType.PRINCIPLE_TRANSFER,
                similarity_score=0.4,
                applicable_concepts=principle_names,
                adaptation_required=["Contextualize to target domain"],
                estimated_benefit=0.3,
                confidence=0.5,
            )
            opportunities.append(opp)

        # Store opportunities
        for opp in opportunities:
            self.transfer_opportunities[opp.opportunity_id] = opp

        return opportunities

    def execute_transfer(
        self,
        opportunity_id: str,
    ) -> Optional[TransferLog]:
        """Execute knowledge transfer"""
        if opportunity_id not in self.transfer_opportunities:
            return None

        opp = self.transfer_opportunities[opportunity_id]

        # Create transfer
        transfer = TransferLog(
            transfer_id=f"trans_{opportunity_id}",
            source_domain=opp.source_domain,
            target_domain=opp.target_domain,
            transferred_knowledge=opp.applicable_concepts,
            results={
                "type": opp.transfer_type.value,
                "concepts_transferred": len(opp.applicable_concepts),
                "adaptations_needed": len(opp.adaptation_required),
            },
            success=opp.confidence > 0.5,
            improvement=opp.estimated_benefit,
        )

        self.transfer_logs.append(transfer)

        # Update target domain with transferred knowledge
        if transfer.success and opp.target_domain in self.domain_knowledge:
            target = self.domain_knowledge[opp.target_domain]
            target.concepts.extend(opp.applicable_concepts[:3])  # Add top transferable

        return transfer

    def get_transfer_statistics(self) -> Dict[str, Any]:
        """Get transfer statistics"""
        successful_transfers = [t for t in self.transfer_logs if t.success]
        total_improvement = sum(t.improvement for t in self.transfer_logs)

        return {
            "total_domains": len(self.domain_knowledge),
            "total_transfers": len(self.transfer_logs),
            "successful_transfers": len(successful_transfers),
            "success_rate": (
                len(successful_transfers) / len(self.transfer_logs)
                if self.transfer_logs else 0.0
            ),
            "total_improvement": round(total_improvement, 2),
            "avg_improvement": (
                total_improvement / len(self.transfer_logs)
                if self.transfer_logs else 0.0
            ),
        }

    def get_domain_growth_potential(self, target_domain: str) -> Dict[str, Any]:
        """Get growth potential from other domains"""
        if target_domain not in self.domain_knowledge:
            return {}

        potentials = []
        for source_domain in self.domain_knowledge:
            if source_domain == target_domain:
                continue

            opps = self.find_transfer_opportunities(source_domain, target_domain)
            if opps:
                potentials.extend([{
                    "source": source_domain,
                    "benefit": opp.estimated_benefit,
                    "confidence": opp.confidence,
                    "type": opp.transfer_type.value,
                } for opp in opps])

        # Sort by potential benefit
        potentials.sort(key=lambda x: x["benefit"], reverse=True)

        return {
            "target_domain": target_domain,
            "transfer_opportunities": len(potentials),
            "highest_potential": potentials[0] if potentials else None,
            "top_sources": [p["source"] for p in potentials[:3]],
        }


class TransferManager:
    """Manage knowledge transfer across multiple agents"""

    def __init__(self):
        self.transferers: Dict[str, KnowledgeTransferer] = {}

    def create_transferer(self, transferer_id: str) -> KnowledgeTransferer:
        """Create knowledge transferer"""
        transferer = KnowledgeTransferer()
        self.transferers[transferer_id] = transferer
        return transferer

    def get_transferer(self, transferer_id: str) -> Optional[KnowledgeTransferer]:
        """Get transferer"""
        return self.transferers.get(transferer_id)


# Global manager
transfer_manager = TransferManager()


# MCP Tools

def create_knowledge_transferer(transferer_id: str) -> dict:
    """Create knowledge transferer"""
    transferer = transfer_manager.create_transferer(transferer_id)
    return {"transferer_id": transferer_id, "created": True}


def add_domain_knowledge(
    transferer_id: str,
    domain: str,
    concepts: list,
    skills: list,
    patterns: list,
    principles: list,
) -> dict:
    """Add domain knowledge"""
    transferer = transfer_manager.get_transferer(transferer_id)
    if not transferer:
        return {"error": "Transferer not found"}

    knowledge = transferer.add_domain_knowledge(
        domain,
        concepts,
        skills,
        patterns,
        principles,
    )
    return knowledge.to_dict()


def find_transfer_opportunities(
    transferer_id: str,
    source_domain: str,
    target_domain: str,
) -> dict:
    """Find knowledge transfer opportunities"""
    transferer = transfer_manager.get_transferer(transferer_id)
    if not transferer:
        return {"error": "Transferer not found"}

    opportunities = transferer.find_transfer_opportunities(source_domain, target_domain)
    return {
        "source": source_domain,
        "target": target_domain,
        "opportunities": [o.to_dict() for o in opportunities],
        "count": len(opportunities),
    }


def execute_knowledge_transfer(transferer_id: str, opportunity_id: str) -> dict:
    """Execute knowledge transfer"""
    transferer = transfer_manager.get_transferer(transferer_id)
    if not transferer:
        return {"error": "Transferer not found"}

    transfer = transferer.execute_transfer(opportunity_id)
    return transfer.to_dict() if transfer else {"error": "Opportunity not found"}


def get_transfer_statistics(transferer_id: str) -> dict:
    """Get transfer statistics"""
    transferer = transfer_manager.get_transferer(transferer_id)
    if not transferer:
        return {"error": "Transferer not found"}

    return transferer.get_transfer_statistics()


def get_domain_growth_potential(transferer_id: str, domain: str) -> dict:
    """Get growth potential for domain"""
    transferer = transfer_manager.get_transferer(transferer_id)
    if not transferer:
        return {"error": "Transferer not found"}

    return transferer.get_domain_growth_potential(domain)


if __name__ == "__main__":
    # Test knowledge transfer
    transferer = KnowledgeTransferer()

    # Add domains
    transferer.add_domain_knowledge(
        "web_development",
        ["HTTP", "REST", "Client-Server"],
        ["HTML", "CSS", "JavaScript"],
        ["Request-Response", "Routing"],
        ["Separation of concerns"],
    )

    transferer.add_domain_knowledge(
        "mobile_development",
        ["HTTP", "REST", "Client-Server"],
        ["Swift", "Kotlin", "UI Design"],
        ["Request-Response", "State management"],
        ["User-centered design"],
    )

    # Find opportunities
    opps = transferer.find_transfer_opportunities("web_development", "mobile_development")
    print(f"Transfer opportunities: {len(opps)}")
    for opp in opps:
        print(f"  - {opp.transfer_type.value}: {len(opp.applicable_concepts)} concepts")

    # Execute transfer
    if opps:
        transfer = transferer.execute_transfer(opps[0].opportunity_id)
        print(f"\nTransfer result: {transfer.success}")
        print(f"Improvement: {transfer.improvement}")

    # Statistics
    stats = transferer.get_transfer_statistics()
    print(f"\nStatistics: {json.dumps(stats, indent=2)}")

    # Growth potential
    potential = transferer.get_domain_growth_potential("mobile_development")
    print(f"Growth potential: {json.dumps(potential, indent=2, default=str)}")
