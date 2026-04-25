"""Relevance scoring for context curation."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FileRelevance:
    """Relevance score for a file."""

    path: str
    score: float
    reasons: list[str]


def relevance_score(
    file_path: str,
    contract_files: Optional[list[str]] = None,
    failing_stack_trace_files: Optional[list[str]] = None,
    touched_files: Optional[list[str]] = None,
    acceptance_keywords: Optional[list[str]] = None,
    recently_modified: Optional[list[str]] = None,
    test_references: Optional[list[str]] = None,
    obsolete_files: Optional[list[str]] = None,
) -> float:
    """
    Calculate relevance score for a file.

    Scoring rules from spec:
    - explicitly_mentioned_in_contract: +5
    - appears_in_failing_stack_trace: +4
    - imports_or_is_imported_by_touched_file: +3
    - grep_hits_acceptance_keywords: +3
    - recently_modified_in_current_sprint: +2
    - test_references_file: +1
    - belongs_to_completed_sprint_without_current_failure_ref: -5
    - is_obsolete_or_archived: -10

    Args:
        file_path: Path to score
        contract_files: Files mentioned in contract
        failing_stack_trace_files: Files in failing stack traces
        touched_files: Files that were touched in this sprint
        acceptance_keywords: Keywords from acceptance criteria
        recently_modified: Recently modified files
        test_references: Files that are test targets
        obsolete_files: Files that are obsolete

    Returns:
        Relevance score
    """
    score = 0.0
    reasons: list[str] = []

    contract_files = contract_files or []
    failing_stack_trace_files = failing_stack_trace_files or []
    touched_files = touched_files or []
    acceptance_keywords = acceptance_keywords or []
    recently_modified = recently_modified or []
    test_references = test_references or []
    obsolete_files = obsolete_files or []

    # Normalize path for comparison
    normalized = file_path.replace("\\", "/")

    # +5: explicitly mentioned in contract
    if any(normalized == f.replace("\\", "/") for f in contract_files):
        score += 5
        reasons.append("mentioned in contract")

    # +4: appears in failing stack trace
    if any(normalized == f.replace("\\", "/") for f in failing_stack_trace_files):
        score += 4
        reasons.append("in failing stack trace")

    # +3: imports or is imported by touched file
    if any(normalized == f.replace("\\", "/") for f in touched_files):
        score += 3
        reasons.append("touched in this sprint")

    # +3: grep hits acceptance keywords
    if acceptance_keywords:
        path_lower = normalized.lower()
        if any(kw.lower() in path_lower for kw in acceptance_keywords):
            score += 3
            reasons.append("matches acceptance keyword")

    # +2: recently modified in current sprint
    if any(normalized == f.replace("\\", "/") for f in recently_modified):
        score += 2
        reasons.append("recently modified")

    # +1: test references file
    if any(normalized == f.replace("\\", "/") for f in test_references):
        score += 1
        reasons.append("test target")

    # -5: belongs to completed sprint without current failure reference
    # (This would need sprint history to determine)

    # -10: is obsolete or archived
    if any(normalized == f.replace("\\", "/") for f in obsolete_files):
        score -= 10
        reasons.append("obsolete/archived")

    return score


def rank_files_by_relevance(
    files: list[str],
    **scoring_kwargs
) -> list[FileRelevance]:
    """
    Rank a list of files by relevance.

    Args:
        files: List of file paths to rank
        **scoring_kwargs: Arguments for relevance_score

    Returns:
        Sorted list of FileRelevance objects (highest first)
    """
    scored = []
    for f in files:
        score = relevance_score(f, **scoring_kwargs)
        scored.append(FileRelevance(path=f, score=score, reasons=[]))

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored
