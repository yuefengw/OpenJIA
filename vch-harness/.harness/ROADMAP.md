# Roadmap

## Project Goal: Add a minimal observable smoke harness that demonstrates planner output, contract-ready acceptance criteria, and command evidence tracking

## S001: Create minimal smoke harness that demonstrates planner output structure with contract-ready acceptance criteria and command evidence tracking

### Features
- F001

### Acceptance Criteria
- AC001: Smoke harness executes and produces JSON output conforming to FEATURE_SPEC schema
  - Verification: integration
  - Oracle: Output JSON contains required fields: project_goal, features array with id/title/user_value, sprints array with id/goal
- AC002: All acceptance criteria within produced output have verification_type, oracle, and required_evidence fields
  - Verification: static_check
  - Oracle: Every AcceptanceCriterion object contains all three required fields with non-empty values
- AC003: Smoke harness command execution is captured with timestamp and exit code
  - Verification: log
  - Oracle: Evidence log contains command, timestamp, exit_code, and stdout/stderr for each verification command
- AC004: Verification commands are documented and runnable
  - Verification: integration
  - Oracle: All sprint verification_commands execute successfully with exit code 0

### Verification Commands
```bash
python -m pytest tests/smoke/test_harness.py -v --tb=short
```
```bash
python -c "import json; spec=json.load(open('tests/smoke/output/feature_spec.json')); assert 'project_goal' in spec and 'features' in spec and 'sprints' in spec"
```
```bash
python -c "import json; spec=json.load(open('tests/smoke/output/feature_spec.json')); acs=[ac for f in spec['features'] for ac in f.get('acceptance_criteria',[])]; assert all(all(k in ac for k in ['verification_type','oracle','required_evidence']) for ac in acs)"
```
