# Claude Code Agent Integration Analysis

## Agent Specializations Overview

Our CFIPros monorepo has **12 specialized agents** that follow Claude Code best practices. Here's how each agent specializes and where they fit in our workflow:

### 📋 **Planning & Analysis Agents**

#### 1. **senior-code-reviewer**
- **Specialization**: KISS/DRY/API contract compliance review
- **Tools**: Read, Grep, Glob, Bash, TodoWrite
- **Integration**: Already integrated in `/implement` command for mandatory code review

#### 2. **cfipros-docs-context**
- **Specialization**: Project decisions, ADRs, PROJECT_CONTEXT.md maintenance
- **Integration**: Should be called after major features to capture decisions

### 🧪 **Testing & Quality Agents**

#### 3. **tdd-coverage-enhancer**
- **Specialization**: Risk-based test coverage (95% for critical, 80% for standard)
- **Integration**: Perfect for `/implement` when coverage is below targets

#### 4. **cfipros-qa-test**
- **Specialization**: Comprehensive test creation (unit, integration, E2E, accessibility)
- **Integration**: Should be used during test phase of `/implement`

#### 5. **test-runner**
- **Specialization**: Test execution and reporting (no fixing, just running)
- **Integration**: Ideal for validation phases in `/implement`

### 🔧 **Development Agents**

#### 6. **cfipros-backend-dev**
- **Specialization**: FastAPI backend features, TDD, contract-first
- **Integration**: Primary agent for backend tasks in `/implement`

#### 7. **cfipros-frontend-shipper**
- **Specialization**: Next.js 15 features, one feature per session, TDD
- **Integration**: Primary agent for frontend tasks in `/implement`

#### 8. **cfipros-database-architect**
- **Specialization**: PostgreSQL schemas, migrations, RLS policies
- **Integration**: Should be used for database-related tasks

#### 9. **cfipros-debugger**
- **Specialization**: Root cause analysis, minimal surgical fixes
- **Integration**: Perfect for debugging phases

### 🏗️ **Infrastructure & Integration Agents**

#### 10. **cfipros-contracts-sdk**
- **Specialization**: OpenAPI contracts, SDK generation, drift prevention
- **Integration**: Critical for API changes in `/implement`

#### 11. **cfipros-ci-cd-release**
- **Specialization**: GitHub Actions, release automation, quality gates
- **Integration**: Should be used for CI/CD setup and releases

#### 12. **github-repo-manager**
- **Specialization**: Repository hygiene, PR management, project organization
- **Integration**: Perfect for repository maintenance tasks

## Strategic Integration Points

### 1. **Enhanced `/implement` Command Workflow**

The `/implement` command should intelligently route tasks to specialized agents based on task type:

```markdown
Phase 1: Task Analysis & Routing
- Parse task description and file paths
- Determine primary specialization needed
- Route to appropriate agent(s)

Phase 2: Specialized Implementation
- Backend tasks → cfipros-backend-dev
- Frontend tasks → cfipros-frontend-shipper
- Database tasks → cfipros-database-architect
- API contract tasks → cfipros-contracts-sdk
- Test tasks → cfipros-qa-test or tdd-coverage-enhancer
- Debug tasks → cfipros-debugger

Phase 3: Quality Gates
- Always use senior-code-reviewer for KISS/DRY/contract review
- Use test-runner for validation
- Use tdd-coverage-enhancer if coverage below targets

Phase 4: Documentation & Context
- Use cfipros-docs-context for major decisions
- Use github-repo-manager for PR management
```

### 2. **Agent Selection Logic**

Based on task characteristics:

**File Path Analysis:**
- `apps/api/**` → cfipros-backend-dev
- `apps/web/**` → cfipros-frontend-shipper
- `contracts/**` → cfipros-contracts-sdk
- Database migrations → cfipros-database-architect
- Tests → cfipros-qa-test or tdd-coverage-enhancer
- `.github/workflows/**` → cfipros-ci-cd-release

**Task Type Analysis:**
- Bug reports → cfipros-debugger
- New features → appropriate dev agent + qa agent
- Performance issues → cfipros-debugger + tdd-coverage-enhancer
- API changes → cfipros-contracts-sdk + cfipros-backend-dev
- Coverage improvements → tdd-coverage-enhancer

### 3. **Parallel Agent Execution**

Following Claude Code best practice #4 (separate agents for frontend/backend/database):

```markdown
**Parallel Safe Combinations:**
- cfipros-frontend-shipper + cfipros-backend-dev (different files)
- cfipros-contracts-sdk + cfipros-qa-test (contracts then tests)
- tdd-coverage-enhancer + cfipros-docs-context (testing + documentation)

**Sequential Requirements:**
- cfipros-contracts-sdk → cfipros-backend-dev (contracts first)
- cfipros-backend-dev → cfipros-qa-test (implementation then tests)
- Any dev agent → senior-code-reviewer (development then review)
```

## Recommended Integration Updates

### 1. **Update `/implement` Command**

Add agent routing logic to the existing implementation:

```xml
<agent_routing>
Smart agent selection based on Claude Code best practices

**Task Analysis:**
- Parse task.description for keywords (backend, frontend, database, test, debug)
- Analyze task.FilePaths for directory patterns
- Determine if parallel execution is safe (different files)

**Agent Selection:**
- Backend: Task tool with subagent_type: "cfipros-backend-dev"
- Frontend: Task tool with subagent_type: "cfipros-frontend-shipper"
- Database: Task tool with subagent_type: "cfipros-database-architect"
- Contracts: Task tool with subagent_type: "cfipros-contracts-sdk"
- Testing: Task tool with subagent_type: "cfipros-qa-test"
- Coverage: Task tool with subagent_type: "tdd-coverage-enhancer"
- Debug: Task tool with subagent_type: "cfipros-debugger"

**Quality Gates:**
- Always: Task tool with subagent_type: "senior-code-reviewer"
- Validation: Task tool with subagent_type: "test-runner"
- Documentation: Task tool with subagent_type: "cfipros-docs-context"
</agent_routing>
```

### 2. **Enhanced Task Tracking Integration**

Update the task tracking script to understand agent assignments:

```powershell
# Add agent assignment to task metadata
function Assign-TaskAgent {
    param($TaskId, $AgentType)
    # Record which agent should handle this task
    # Enable agent-specific progress tracking
}

function Get-RecommendedAgent {
    param($TaskDescription, $FilePaths)
    # Analyze task and return recommended agent
    # Follow the routing logic from above
}
```

### 3. **Agent Coordination Workflow**

Create a meta-workflow that coordinates multiple agents:

```markdown
**Coordination Patterns:**

1. **API Feature Flow:**
   - cfipros-contracts-sdk (define API)
   - cfipros-backend-dev (implement backend)
   - cfipros-frontend-shipper (implement frontend)
   - cfipros-qa-test (comprehensive testing)
   - senior-code-reviewer (quality review)

2. **Bug Fix Flow:**
   - cfipros-debugger (diagnose and fix)
   - tdd-coverage-enhancer (add regression tests)
   - senior-code-reviewer (review fix)
   - test-runner (validate all tests pass)

3. **Database Feature Flow:**
   - cfipros-database-architect (schema design)
   - cfipros-backend-dev (service layer)
   - cfipros-qa-test (integration tests)
   - senior-code-reviewer (review)

4. **Release Flow:**
   - cfipros-ci-cd-release (prepare release)
   - test-runner (full test suite)
   - github-repo-manager (create PR/release)
   - cfipros-docs-context (document changes)
```

## Benefits of Agent Integration

### 1. **Follows Claude Code Best Practices**
- **Specialized agents (#4)**: Each agent does ONE thing perfectly
- **Separate agents for frontend/backend/database (#17)**
- **Planning is 80% of success (#1)**: Right agent for right task
- **TDD focus (#14)**: Testing agents ensure tests before code

### 2. **Improved Quality & Efficiency**
- **Risk-based coverage**: tdd-coverage-enhancer targets critical paths
- **Contract-first development**: cfipros-contracts-sdk prevents drift
- **Minimal fixes**: cfipros-debugger focuses on surgical changes
- **Comprehensive testing**: cfipros-qa-test covers all test types

### 3. **Better Task Management**
- **Clear agent assignment**: Each task knows its expert
- **Parallel execution**: Different specializations can work simultaneously
- **Quality gates**: senior-code-reviewer ensures standards
- **Documentation**: cfipros-docs-context captures decisions

### 4. **Reduced Context Switching**
- **Agent expertise**: Each agent knows its domain deeply
- **Consistent patterns**: Each agent follows established practices
- **Quality enforcement**: Built-in review and testing workflows

## Implementation Priority

### Phase 1: Core Integration (High Priority)
1. **Update `/implement` command** with agent routing logic
2. **Integrate senior-code-reviewer** (already partially done)
3. **Add cfipros-backend-dev and cfipros-frontend-shipper** routing
4. **Test the enhanced workflow** with a sample feature

### Phase 2: Quality Enhancement (Medium Priority)
1. **Integrate cfipros-qa-test** for comprehensive testing
2. **Add tdd-coverage-enhancer** for coverage targets
3. **Include cfipros-debugger** for bug fix workflows
4. **Add test-runner** for validation phases

### Phase 3: Full Integration (Lower Priority)
1. **Integrate cfipros-contracts-sdk** for API workflows
2. **Add cfipros-database-architect** for schema changes
3. **Include cfipros-ci-cd-release** for deployment
4. **Add cfipros-docs-context** for documentation
5. **Include github-repo-manager** for repository management

## Example Integration Code

Here's how the enhanced `/implement` command would work:

```xml
<execution_phases>
**Phase 1: Task Analysis & Agent Assignment**
```bash
scripts/task-tick.ps1 next
```
- Parse task description and file paths
- Determine recommended agent based on specialization
- Check parallel execution safety

**Phase 2: Specialized Implementation**
```bash
# Backend task example
Task tool with subagent_type: "cfipros-backend-dev"
Prompt: "Implement task T001: Create user authentication endpoint in apps/api/app/api/auth.py"

# Frontend task example
Task tool with subagent_type: "cfipros-frontend-shipper"
Prompt: "Implement task T002: Create login form component in apps/web/src/components/auth/"
```

**Phase 3: Quality Gates**
```bash
# Always run senior code review
Task tool with subagent_type: "senior-code-reviewer"
Prompt: "Review implementation of T001. Check KISS, DRY, API contract compliance"

# Run tests if needed
Task tool with subagent_type: "test-runner"
Prompt: "Execute all tests related to authentication changes"
```

**Phase 4: Completion & Documentation**
```bash
scripts/task-tick.ps1 done T001 "Implemented authentication endpoint;Added JWT validation;Integrated with Clerk"

# For major decisions
Task tool with subagent_type: "cfipros-docs-context"
Prompt: "Document the authentication system change and update PROJECT_CONTEXT.md"
```
</execution_phases>
```

This integration transforms our `/implement` command into an intelligent orchestrator that leverages specialized agents for maximum efficiency while maintaining quality standards.
