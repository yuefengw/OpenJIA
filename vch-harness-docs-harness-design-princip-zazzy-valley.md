# Plan: Clean Generator Context

## Context

The user is asking how to provide the cleanest, most relevant, and complete context to the generator, based on the design principles in `HARNESS_DESIGN_PRINCIPLES.md`.

### Key Design Principles Driving Context Curation

**Principle 3: Context Must Be Curated, Not Dumped**
- "Generator context should include: current contract, ledger/progress, relevant files, and latest failure only."
- "Old eval reports and unrelated logs should be forbidden context unless explicitly requested."

**Principle 7: Evidence Is the Interface Between Roles**
- "Repair should not receive a vague critique. It should receive minimal, concrete evidence..."

### Current Context Flow

1. `ContextCurator.build_manifest()` → `ContextManifest`
2. `Generator.invoke(contract, manifest, repair_packet)`
3. `_build_llm_prompt()` assembles a JSON packet:
   ```json
   {
     "contract": contract.model_dump(),
     "context_manifest": manifest or {},
     "existing_allowed_files": {file_path: content, ...},
     "repair_packet": repair_packet.model_dump() if repair else None,
     "rules": [...]
   }
   ```

### Issues with Current Implementation

1. **`forbidden_context` is defined in manifest but never enforced**: The manifest has `forbidden_context: ["obsolete eval reports", "old unrelated logs", "previous generator self-praise"]` but `_build_llm_prompt` doesn't read or respect this field.

2. **All `existing_allowed_files` are dumped raw**: If allowed files are large (e.g., minified JS, large CSS), the prompt becomes enormous. There's no size limit or summarization.

3. **`may_read` files not included in prompt**: The generator prompt file says "Read CONTRACT.yaml and CONTEXT_MANIFEST.yaml first" but actual file contents for `may_read` files are not provided in the JSON packet — only paths exist in the manifest.

4. **Prompt template (generator.md) is generic**: It doesn't dynamically incorporate the specific contract goal, forbidden paths, or repair context into the instruction text.

5. **manifest vs model**: `_build_llm_prompt` receives `manifest: Optional[dict]` but the actual `ContextManifest` object is converted to dict in `orchestrator._run_generator()` — type safety is lost.

---

## Recommended Approach

### 1. Enforce `forbidden_context` at Prompt Assembly Time

In `_build_llm_prompt`, explicitly check and exclude forbidden context categories:

```python
# Explicitly state what's forbidden in rules
forbidden = manifest.get("forbidden_context", []) if manifest else []
rules = [
    f"Do not read or reference: {', '.join(forbidden)}.",
    # ... existing rules
]
```

### 2. Limit File Content Size with Truncation

Add a max file size (e.g., 8KB per file, 64KB total) for `existing_allowed_files`:

```python
MAX_FILE_SIZE = 8 * 1024  # 8KB per file
MAX_TOTAL_SIZE = 64 * 1024  # 64KB total

def _truncate_file_content(self, path: Path) -> str:
    content = path.read_text(encoding="utf-8", errors="replace")
    if len(content) > MAX_FILE_SIZE:
        return content[:MAX_FILE_SIZE] + f"\n... [truncated {len(content) - MAX_FILE_SIZE} chars]"
    return content
```

### 3. Include File Summaries for Large `may_read` Files

Instead of dumping all `may_read` files raw, provide a summary structure:

```python
def _summarize_files(self, file_paths: list[str]) -> dict:
    summaries = {}
    total_size = 0
    for path in file_paths:
        full_path = self.repo_root / path
        if not full_path.exists():
            continue
        content = full_path.read_text(encoding="utf-8", errors="replace")
        size = len(content)
        if total_size + size > MAX_TOTAL_SIZE:
            summaries[path] = {"type": "summary", "lines": len(content.splitlines()), "size": size}
            continue
        summaries[path] = {"type": "content", "content": content[:MAX_FILE_SIZE]}
        total_size += size
    return summaries
```

### 4. Make Prompt Template Dynamic

The `generator.md` prompt template should be parameterized. Instead of a static file, pass context directly:

```python
def _build_llm_prompt(...):
    # Build a focused prompt with explicit context
    prompt_parts = [
        f"# Generator Context for Sprint {contract.sprint_id}",
        "",
        f"## Goal: {contract.goal}",
        "",
        f"## Allowed Write Paths ({len(contract.allowed_files)} files):",
        *[f"- {p}" for p in contract.allowed_files],
        "",
        f"## Forbidden Paths:",
        *[f"- {p}" for p in contract.forbidden_files] if contract.forbidden_files else "- None",
        "",
        "## Acceptance Criteria:",
        *[f"- {ac.id}: {ac.behavior}" for ac in contract.acceptance_criteria],
        "",
    ]
    
    # Add repair context if present
    if repair_packet:
        prompt_parts.extend([
            "",
            "## REPAIR CONTEXT",
            f"Failed AC: {repair_packet.failed_ac}",
            f"Must fix: {', '.join(repair_packet.must_fix)}",
            f"Must NOT change: {', '.join(repair_packet.must_not_change)}",
            f"Evidence: {', '.join(repair_packet.evidence[:5])}",  # Limit evidence
        ])
    
    # ... then add file contents
```

### 5. Respect `latest_failure` from Manifest

When building repair context, use `manifest.latest_failure` instead of reconstructing:

```python
if manifest and manifest.get("latest_failure"):
    lf = manifest["latest_failure"]
    prompt_parts.extend([
        "",
        "## Latest Failure",
        f"Failed criteria: {', '.join(lf.get('failed_criteria', []))}",
        f"Evidence files: {', '.join(lf.get('evidence', [])[:5])}",
    ])
```

---

## Critical Files to Modify

| File | Change |
|------|--------|
| `vch-harness/src/vch/agents/generator.py` | `_build_llm_prompt()` — add truncation, dynamic prompt, enforce forbidden_context |
| `vch-harness/src/vch/context/curator.py` | Add file size limits when collecting `relevant_code_context` |

---

## Verification

1. Run existing unit tests: `pytest vch-harness/tests/unit/test_llm_generator.py -v`
2. Verify prompt size stays under 64KB for typical contracts
3. Verify forbidden_context items are explicitly mentioned in rules
4. Verify repair context is minimal and concrete (not full eval reports)
