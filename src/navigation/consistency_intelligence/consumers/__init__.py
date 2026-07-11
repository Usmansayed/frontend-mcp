"""Phase 3 thin consumers — validators and fix proposers query the graph only."""
from navigation.consistency_intelligence.consumers.auditor import ConsistencyAuditor
from navigation.consistency_intelligence.consumers.fix_proposer import FixProposer
from navigation.consistency_intelligence.consumers.validator import ConsistencyValidator
from navigation.consistency_intelligence.knowledge.queries._helpers import group_deviations

__all__ = ['ConsistencyAuditor', 'ConsistencyValidator', 'FixProposer', 'group_deviations']
