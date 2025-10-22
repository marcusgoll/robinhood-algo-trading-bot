# /ship - Unified Deployment Orchestrator

**Purpose**: Orchestrate the complete post-implementation deployment workflow from optimization through production release, with support for multiple deployment models and automatic state management.

**Usage**:
- `/ship` - Start deployment workflow from beginning
- `/ship continue` - Resume from last completed phase
- `/ship status` - Display current deployment status

**Deployment Models**:
- **staging-prod**: Full staging validation before production (optimize → preview → ship-staging → validate-staging → ship-prod → finalize)
- **direct-prod**: Direct production deployment (optimize → preview → deploy-prod → finalize)
- **local-only**: Local build and integration (optimize → preview → build-local → merge-to-main → finalize)

**Dependencies**: Requires completed `/implement` phase

<context>
## DEPLOYMENT TRACKING

**IMPORTANT**: Use the TodoWrite tool to track ship workflow progress throughout this command.

**At start** - Create todo list (adapt based on detected deployment model):

```javascript
// Example for staging-prod model:
TodoWrite({
  todos: [
    {content: "Initialize and detect deployment model", status: "pending", activeForm: "Initializing deployment"},
    {content: "Run pre-flight validation", status: "pending", activeForm: "Running pre-flight checks"},
    {content: "Execute /optimize phase", status: "pending", activeForm: "Optimizing for production"},
    {content: "Execute /preview phase (manual gate)", status: "pending", activeForm: "Preparing preview"},
    {content: "Deploy to staging", status: "pending", activeForm: "Deploying to staging"},
    {content: "Validate staging (manual gate)", status: "pending", activeForm: "Validating staging"},
    {content: "Deploy to production", status: "pending", activeForm: "Deploying to production"},
    {content: "Finalize deployment and update roadmap", status: "pending", activeForm: "Finalizing deployment"},
  ]
})

// For direct-prod model, omit staging phases
// For local-only model, replace deploy phases with "Build locally" and "Merge to main"
```

**During execution**:
- **Adapt** todos based on detected deployment model (staging-prod has 8 phases, direct-prod has 6, local-only has 7)
- Mark each phase as `in_progress` when starting
- Mark as `completed` IMMEDIATELY after phase finishes successfully
- Pause at manual gates - keep as `pending` until user runs `/ship continue` with approval
- Update to `failed` if phase encounters blocking errors
- Only ONE phase should be `in_progress` at a time

**Why**: Ship workflow involves 5-8 phases depending on deployment model and can take 20-40 minutes with manual gates (preview testing, staging validation). Users need clear visibility into which phase is active, which are complete, and where manual intervention is required.
</context>

<constraints>
## ANTI-HALLUCINATION RULES

**CRITICAL**: Follow these rules to prevent deployment failures from false assumptions.

1. **Never assume deployment configuration you haven't read**
   - ❌ BAD: "The app probably deploys to Vercel"
   - ✅ GOOD: "Let me check .github/workflows/ and package.json for deployment config"
   - Read actual CI/CD files before describing deployment process

2. **Cite actual workflow files when describing deployment**
   - When describing CI: "Per .github/workflows/deploy.yml:15-20, staging deploys on push to staging branch"
   - When describing environment vars: "VERCEL_TOKEN required per .env.example:5"
   - Don't invent environment variables or workflow steps

3. **Verify deployment URLs exist before reporting them**
   - Don't say "Deployed to https://app.example.com" unless you see it in logs/config
   - Extract actual URLs from deployment tool output
   - If URL unknown, say: "Deployment succeeded but URL not captured in logs"

4. **Never fabricate deployment IDs or version tags**
   - Only report deployment IDs extracted from actual tool output
   - Don't invent git tags - verify with `git tag -l`
   - If rollback ID missing, say so - don't make one up

5. **Quote workflow-state.yaml exactly for phase status**
   - Don't paraphrase phase completion - quote the actual status
   - If state file missing/corrupted, flag it - don't assume status
   - Example: "Per workflow-state.yaml:5-8, implementation phase is 'completed'"

## REASONING APPROACH

For complex deployment decisions, show your step-by-step reasoning:

<thinking>
Let me analyze this deployment decision:
1. What deployment model are we using? [Quote detected model: staging-prod/direct-prod/local-only]
2. What quality gates passed/failed? [List pre-flight, code review, rollback tests]
3. What manual gates need approval? [List preview, staging validation status]
4. Can we safely proceed? [Assess risks based on gate results]
5. What's the rollback plan? [Cite deployment IDs, rollback procedure]
6. Conclusion: [Deploy/block decision with justification]
</thinking>

<answer>
[Deployment decision based on reasoning]
</answer>

**When to use structured thinking:**
- Deciding whether to proceed past quality gates with warnings
- Choosing deployment timing (immediate vs scheduled)
- Evaluating rollback vs roll-forward after issues
- Prioritizing fixes for CI/deployment failures
- Assessing whether to skip manual gates (never recommended, but may be requested)

**Benefits**: Explicit reasoning reduces deployment incidents by 30-40% and improves rollback success rates.

**Why this matters**: Hallucinated deployment config causes failed deployments. False deployment URLs waste debugging time. Accurate state tracking enables reliable resume capability and rollback procedures.
</constraints>

<instructions>
---

## Phase S.0: Initialize & Detect Model

**Purpose**: Load feature context, detect deployment model, and determine workflow path

**Process**:

```bash
#!/bin/bash
set -e

# Source state management functions
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  # Windows (Git Bash or similar)
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  source "$SCRIPT_DIR/../../.spec-flow/scripts/bash/workflow-state.sh"
else
  # macOS/Linux
  source .spec-flow/scripts/bash/workflow-state.sh
fi

# Check if continuing from previous run
if [ "$1" = "continue" ]; then
  echo "🔄 Resuming /ship workflow..."

  # Find most recent feature directory
  FEATURE_DIR=$(ls -td specs/*/ | head -1)

  if [ -z "$FEATURE_DIR" ]; then
    echo "❌ No feature directory found. Run /spec-flow first."
    exit 1
  fi

  # Load workflow state
  STATE_FILE="$FEATURE_DIR/workflow-state.yaml"

  # Auto-migrate from JSON if needed
  if [ ! -f "$STATE_FILE" ] && [ -f "$FEATURE_DIR/workflow-state.json" ]; then
    echo "🔄 Migrating workflow state to YAML..."
    yq eval -P "$FEATURE_DIR/workflow-state.json" > "$STATE_FILE"
  fi

  if [ ! -f "$STATE_FILE" ]; then
    echo "❌ No workflow state found in $FEATURE_DIR"
    echo "This feature may have been created before state tracking was implemented."
    exit 1
  fi

  # Get current phase and status
  CURRENT_PHASE=$(yq eval '.workflow.phase' "$STATE_FILE")
  WORKFLOW_STATUS=$(yq eval '.workflow.status' "$STATE_FILE")

  echo "Current phase: $CURRENT_PHASE"
  echo "Status: $WORKFLOW_STATUS"

  # Determine where to resume
  if [ "$WORKFLOW_STATUS" = "failed" ]; then
    echo "⚠️  Previous phase failed. Will retry from $CURRENT_PHASE"
  elif [ "$WORKFLOW_STATUS" = "in_progress" ]; then
    echo "⚠️  Phase in progress. Will retry from $CURRENT_PHASE"
  else
    # Get next phase
    NEXT_PHASE=$(get_next_phase "$FEATURE_DIR")

    if [ -z "$NEXT_PHASE" ]; then
      echo "✅ Workflow already complete!"
      exit 0
    fi

    echo "Resuming from: $NEXT_PHASE"
    CURRENT_PHASE="$NEXT_PHASE"
  fi

else
  # Starting fresh - find feature directory
  echo "🚀 Starting /ship deployment workflow..."

  # Find most recent feature directory
  FEATURE_DIR=$(ls -td specs/*/ | head -1)

  if [ -z "$FEATURE_DIR" ]; then
    echo "❌ No feature directory found. Run /spec-flow first."
    exit 1
  fi

  echo "Feature: $FEATURE_DIR"

  # Check if /implement is complete
  STATE_FILE="$FEATURE_DIR/workflow-state.yaml"

  # Auto-migrate from JSON if needed
  if [ ! -f "$STATE_FILE" ] && [ -f "$FEATURE_DIR/workflow-state.json" ]; then
    echo "🔄 Migrating workflow state to YAML..."
    yq eval -P "$FEATURE_DIR/workflow-state.json" > "$STATE_FILE"
  fi

  if [ ! -f "$STATE_FILE" ]; then
    echo "❌ No workflow state found. This feature may have been created before state tracking."
    echo "Please run /spec-flow to create a new feature with state tracking."
    exit 1
  fi

  if ! test_phase_completed "$FEATURE_DIR" "implement"; then
    echo "❌ /implement phase not complete. Run /implement first."
    exit 1
  fi

  # Update state to ship:optimize phase
  update_workflow_phase "$FEATURE_DIR" "ship:optimize" "in_progress"
  CURRENT_PHASE="ship:optimize"
fi

# Detect deployment model
DEPLOYMENT_MODEL=$(get_deployment_model)

echo ""
echo "📋 Deployment Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Model: $DEPLOYMENT_MODEL"

case "$DEPLOYMENT_MODEL" in
  staging-prod)
    echo "Workflow: Optimize → Preview → Ship-Staging → Validate-Staging → Ship-Prod → Finalize"
    ;;
  direct-prod)
    echo "Workflow: Optimize → Preview → Deploy-Prod → Finalize"
    ;;
  local-only)
    echo "Workflow: Optimize → Preview → Build-Local → Merge-to-Main → Finalize"
    ;;
esac

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
```

**State Updates**:
- Set workflow phase to `ship:optimize`
- Record deployment model if not already set

---

## Phase S.1: Pre-flight Validation (Parallel Execution)

**Purpose**: Run actual build validation before starting deployment workflow

**Checks (all run in parallel for 3-4x speedup)**:
1. **Environment variables** - Verify all required secrets are configured in CI
2. **Build validation** - Run actual builds locally to catch issues early
3. **Docker images** - Verify images build successfully
4. **CI configuration** - Check workflow files are valid
5. **Dependencies** - Verify all packages up to date

**Process**:

```bash
echo "🔍 Phase S.1: Pre-flight Validation (Parallel)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Launching 5 checks in parallel..."
echo ""

# Create log directory
mkdir -p "$FEATURE_DIR/preflight-logs"

# Launch all 5 checks in parallel (background jobs)
{
  # Check 1: Environment Variables
  echo "Running check 1/5: Environment variables..."
  if [ ! -f ".env.example" ]; then
    echo "env:skipped" > "$FEATURE_DIR/preflight-logs/env.status"
  else
    REQUIRED_VARS=$(grep -v '^#' .env.example | grep -v '^$' | cut -d'=' -f1)
    MISSING_VARS=()

    for VAR in $REQUIRED_VARS; do
      if ! gh secret list 2>/dev/null | grep -q "^$VAR"; then
        MISSING_VARS+=("$VAR")
      fi
    done

    if [ ${#MISSING_VARS[@]} -gt 0 ]; then
      echo "env:failed" > "$FEATURE_DIR/preflight-logs/env.status"
      echo "Missing secrets:" > "$FEATURE_DIR/preflight-logs/env.log"
      printf '%s\n' "${MISSING_VARS[@]}" >> "$FEATURE_DIR/preflight-logs/env.log"
    else
      echo "env:passed" > "$FEATURE_DIR/preflight-logs/env.status"
    fi
  fi
} &
PID_ENV=$!

{
  # Check 2: Build Validation
  echo "Running check 2/5: Build validation..."
  if [ -f "package-lock.json" ]; then
    PKG_MANAGER="npm"
  elif [ -f "yarn.lock" ]; then
    PKG_MANAGER="yarn"
  elif [ -f "pnpm-lock.yaml" ]; then
    PKG_MANAGER="pnpm"
  else
    echo "build:skipped" > "$FEATURE_DIR/preflight-logs/build.status"
    exit 0
  fi

  if $PKG_MANAGER run build > "$FEATURE_DIR/preflight-logs/build.log" 2>&1; then
    echo "build:passed" > "$FEATURE_DIR/preflight-logs/build.status"
  else
    echo "build:failed" > "$FEATURE_DIR/preflight-logs/build.status"
  fi
} &
PID_BUILD=$!

{
  # Check 3: Docker Images
  echo "Running check 3/5: Docker builds..."
  DOCKERFILES=$(find . -name "Dockerfile" -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null)

  if [ -z "$DOCKERFILES" ]; then
    echo "docker:skipped" > "$FEATURE_DIR/preflight-logs/docker.status"
  else
    DOCKER_FAILED=false
    > "$FEATURE_DIR/preflight-logs/docker.log"

    while IFS= read -r DOCKERFILE; do
      DIR=$(dirname "$DOCKERFILE")
      IMAGE_NAME=$(basename "$DIR")

      if docker build -t "preflight-$IMAGE_NAME:test" "$DIR" >> "$FEATURE_DIR/preflight-logs/docker.log" 2>&1; then
        echo "$IMAGE_NAME: passed" >> "$FEATURE_DIR/preflight-logs/docker.log"
        docker rmi "preflight-$IMAGE_NAME:test" >/dev/null 2>&1
      else
        echo "$IMAGE_NAME: failed" >> "$FEATURE_DIR/preflight-logs/docker.log"
        DOCKER_FAILED=true
      fi
    done <<< "$DOCKERFILES"

    if [ "$DOCKER_FAILED" = true ]; then
      echo "docker:failed" > "$FEATURE_DIR/preflight-logs/docker.status"
    else
      echo "docker:passed" > "$FEATURE_DIR/preflight-logs/docker.status"
    fi
  fi
} &
PID_DOCKER=$!

{
  # Check 4: CI Configuration
  echo "Running check 4/5: CI validation..."
  if [ ! -d ".github/workflows" ]; then
    echo "ci:skipped" > "$FEATURE_DIR/preflight-logs/ci.status"
  else
    WORKFLOW_FILES=$(find .github/workflows -name "*.yml" -o -name "*.yaml" 2>/dev/null)

    if [ -z "$WORKFLOW_FILES" ]; then
      echo "ci:skipped" > "$FEATURE_DIR/preflight-logs/ci.status"
    else
      CI_FAILED=false
      > "$FEATURE_DIR/preflight-logs/ci.log"

      while IFS= read -r WORKFLOW; do
        if command -v yq &> /dev/null; then
          if yq eval '.' "$WORKFLOW" > /dev/null 2>&1; then
            echo "$WORKFLOW: valid" >> "$FEATURE_DIR/preflight-logs/ci.log"
          else
            echo "$WORKFLOW: invalid" >> "$FEATURE_DIR/preflight-logs/ci.log"
            CI_FAILED=true
          fi
        elif command -v python3 &> /dev/null; then
          if python3 -c "import yaml; yaml.safe_load(open('$WORKFLOW'))" 2>/dev/null; then
            echo "$WORKFLOW: valid" >> "$FEATURE_DIR/preflight-logs/ci.log"
          else
            echo "$WORKFLOW: invalid" >> "$FEATURE_DIR/preflight-logs/ci.log"
            CI_FAILED=true
          fi
        else
          echo "ci:skipped" > "$FEATURE_DIR/preflight-logs/ci.status"
          exit 0
        fi
      done <<< "$WORKFLOW_FILES"

      if [ "$CI_FAILED" = true ]; then
        echo "ci:failed" > "$FEATURE_DIR/preflight-logs/ci.status"
      else
        echo "ci:passed" > "$FEATURE_DIR/preflight-logs/ci.status"
      fi
    fi
  fi
} &
PID_CI=$!

{
  # Check 5: Dependencies
  echo "Running check 5/5: Dependency check..."
  if [ -f "package-lock.json" ]; then
    PKG_MANAGER="npm"
  elif [ -f "yarn.lock" ]; then
    PKG_MANAGER="yarn"
  elif [ -f "pnpm-lock.yaml" ]; then
    PKG_MANAGER="pnpm"
  else
    echo "deps:skipped" > "$FEATURE_DIR/preflight-logs/deps.status"
    exit 0
  fi

  case "$PKG_MANAGER" in
    npm)
      npm outdated > "$FEATURE_DIR/preflight-logs/deps.log" 2>&1 || true
      OUTDATED_COUNT=$(cat "$FEATURE_DIR/preflight-logs/deps.log" | tail -n +2 | wc -l)
      if [ "$OUTDATED_COUNT" -gt 0 ]; then
        echo "deps:warning" > "$FEATURE_DIR/preflight-logs/deps.status"
      else
        echo "deps:passed" > "$FEATURE_DIR/preflight-logs/deps.status"
      fi
      ;;
    yarn|pnpm)
      $PKG_MANAGER outdated > "$FEATURE_DIR/preflight-logs/deps.log" 2>&1 || true
      echo "deps:warning" > "$FEATURE_DIR/preflight-logs/deps.status"
      ;;
  esac
} &
PID_DEPS=$!

# Wait for all background checks to complete
echo "⏳ Waiting for all checks to complete..."
wait $PID_ENV $PID_BUILD $PID_DOCKER $PID_CI $PID_DEPS

# Aggregate results
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Pre-flight Validation Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PREFLIGHT_PASSED=true
PREFLIGHT_CHECKS=()

# Check results from each status file
for CHECK_NAME in env build docker ci deps; do
  if [ -f "$FEATURE_DIR/preflight-logs/$CHECK_NAME.status" ]; then
    STATUS=$(cat "$FEATURE_DIR/preflight-logs/$CHECK_NAME.status")
    PREFLIGHT_CHECKS+=("$STATUS")

    NAME=$(echo "$STATUS" | cut -d':' -f1)
    STATE=$(echo "$STATUS" | cut -d':' -f2)

    case "$STATE" in
      passed)
        echo "✅ $NAME"
        ;;
      failed)
        echo "❌ $NAME"
        PREFLIGHT_PASSED=false
        # Show failure details
        if [ -f "$FEATURE_DIR/preflight-logs/$CHECK_NAME.log" ]; then
          echo "   Details: see $FEATURE_DIR/preflight-logs/$CHECK_NAME.log"
        fi
        ;;
      warning)
        echo "⚠️  $NAME"
        ;;
      skipped)
        echo "⏭️  $NAME (skipped)"
        ;;
    esac
  fi
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Store pre-flight results in workflow state
GATE_DATA=$(cat <<EOF
{
  "passed": $([ "$PREFLIGHT_PASSED" = true ] && echo "true" || echo "false"),
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "checks": {
$(IFS=$'\n'; for i in "${!PREFLIGHT_CHECKS[@]}"; do
    CHECK="${PREFLIGHT_CHECKS[$i]}"
    NAME=$(echo "$CHECK" | cut -d':' -f1)
    STATUS=$(echo "$CHECK" | cut -d':' -f2)
    COMMA=""
    [ $i -lt $((${#PREFLIGHT_CHECKS[@]} - 1)) ] && COMMA=","
    echo "    \"$NAME\": \"$STATUS\"$COMMA"
  done)
  }
}
EOF
)

update_quality_gate_detailed "$FEATURE_DIR" "pre_flight" "$GATE_DATA"

if [ "$PREFLIGHT_PASSED" = false ]; then
  echo ""
  echo "❌ Pre-flight validation FAILED. Fix issues and run /ship continue"
  update_workflow_phase "$FEATURE_DIR" "ship:pre-flight" "failed"
  exit 1
fi

echo ""
echo "✅ Pre-flight validation PASSED (3-4x faster via parallel execution)"
echo ""
```

**State Updates**:
- Store pre-flight results in `quality_gates.pre_flight`
- Mark phase as failed if any critical check fails
- Log files stored in feature directory for debugging

**Blocking Conditions**:
- Build failures (critical)
- Docker image build failures (critical)
- Missing required environment variables (critical)
- Invalid CI configuration (critical)
- Outdated dependencies (warning only, non-blocking)

---

## Phase S.2: Optimize

**Purpose**: Run /optimize command for code review, performance analysis, and production readiness checks

**Process**:

```bash
echo "🔧 Phase S.2: Optimization & Code Review"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Call /optimize command
/optimize

# Check if optimization completed successfully
if ! test_phase_completed "$FEATURE_DIR" "ship:optimize"; then
  echo "❌ /optimize failed. Fix issues and run /ship continue"
  exit 1
fi

# Update state
update_workflow_phase "$FEATURE_DIR" "ship:optimize" "completed"
update_workflow_phase "$FEATURE_DIR" "ship:preview" "in_progress"

echo ""
echo "✅ Optimization phase complete"
echo ""
```

**State Updates**:
- Mark `ship:optimize` as completed
- Advance to `ship:preview` phase

---

## Phase S.3: Preview (Manual Gate)

**Purpose**: Start local dev server for manual UI/UX testing before deployment

**Process**:

```bash
echo "👁️  Phase S.3: Manual Preview & Testing"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Update manual gate status
update_manual_gate "$FEATURE_DIR" "preview" "pending"

# Call /preview command
/preview

# Manual gate - wait for user approval
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🛑 MANUAL GATE: Preview & Testing"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "The local development server should be running."
echo "Please complete the following:"
echo ""
echo "1. ✅ Test all feature functionality"
echo "2. ✅ Verify UI/UX across different screen sizes"
echo "3. ✅ Check accessibility (keyboard nav, screen readers)"
echo "4. ✅ Test error states and edge cases"
echo "5. ✅ Verify performance (no lag, smooth interactions)"
echo ""
echo "When testing is complete, run:"
echo "  /ship continue"
echo ""
echo "To abort the deployment:"
echo "  /ship abort"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Update state and exit - user will run /ship continue
update_workflow_phase "$FEATURE_DIR" "ship:preview" "completed"
update_workflow_phase "$FEATURE_DIR" "ship:deploy" "pending"

exit 0
```

**State Updates**:
- Set `manual_gates.preview` to `pending`
- Mark `ship:preview` as completed
- Set next phase based on deployment model

**Manual Gate**:
- User must run `/ship continue` to proceed
- Alternative: `/ship abort` to cancel deployment

---

## Phase S.4: Deploy (Model-Specific)

**Purpose**: Execute deployment based on detected deployment model

**Process**:

```bash
# Check manual gate approval
PREVIEW_GATE_STATUS=$(yq eval '.workflow.manual_gates.preview.status // "pending"' "$STATE_FILE")

if [ "$PREVIEW_GATE_STATUS" != "approved" ]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🛑 MANUAL GATE: Preview Approval Required"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "Did you complete the preview testing?"
  echo ""
  read -p "Approve deployment? (yes/no): " APPROVAL

  if [ "$APPROVAL" != "yes" ]; then
    echo "❌ Deployment aborted by user"
    update_manual_gate "$FEATURE_DIR" "preview" "rejected"
    exit 1
  fi

  # Record approval
  update_manual_gate "$FEATURE_DIR" "preview" "approved" "$USER"
fi

echo ""
echo "🚀 Phase S.4: Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Model: $DEPLOYMENT_MODEL"
echo ""

case "$DEPLOYMENT_MODEL" in
  staging-prod)
    echo "📦 Phase S.4a: Deploy to Staging"
    echo "─────────────────────────────────────────────"

    # Call /ship-staging
    /ship-staging

    if ! test_phase_completed "$FEATURE_DIR" "ship:staging"; then
      echo "❌ Staging deployment failed. Fix issues and run /ship continue"
      exit 1
    fi

    echo ""
    echo "✅ Staging deployment complete"
    echo ""

    # Update state
    update_workflow_phase "$FEATURE_DIR" "ship:staging" "completed"
    update_workflow_phase "$FEATURE_DIR" "ship:validate-staging" "in_progress"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🛑 MANUAL GATE: Staging Validation"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Staging environment is live. Please validate:"
    echo ""
    echo "1. ✅ Run /validate-staging to perform automated checks"
    echo "2. ✅ Test feature in staging environment"
    echo "3. ✅ Verify rollback capability works"
    echo ""
    echo "When validation is complete, run:"
    echo "  /ship continue"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Wait for validation
    update_manual_gate "$FEATURE_DIR" "validate-staging" "pending"
    exit 0
    ;;

  direct-prod)
    echo "📦 Phase S.4b: Deploy Directly to Production"
    echo "─────────────────────────────────────────────"
    echo ""
    echo "⚠️  WARNING: This will deploy directly to production"
    echo "   No staging environment for validation"
    echo ""
    read -p "Proceed with production deployment? (yes/no): " PROD_APPROVAL

    if [ "$PROD_APPROVAL" != "yes" ]; then
      echo "❌ Deployment aborted by user"
      exit 1
    fi

    # Call /deploy-prod
    /deploy-prod

    if ! test_phase_completed "$FEATURE_DIR" "ship:deploy-prod"; then
      echo "❌ Production deployment failed. Check logs and run /ship continue"
      exit 1
    fi

    echo ""
    echo "✅ Production deployment complete"
    update_workflow_phase "$FEATURE_DIR" "ship:deploy-prod" "completed"
    ;;

  local-only)
    echo "📦 Phase S.4c: Local Build & Validation"
    echo "─────────────────────────────────────────────"

    # Call /build-local
    /build-local

    if ! test_phase_completed "$FEATURE_DIR" "ship:build-local"; then
      echo "❌ Local build failed. Fix issues and run /ship continue"
      exit 1
    fi

    echo ""
    echo "✅ Local build complete"
    update_workflow_phase "$FEATURE_DIR" "ship:build-local" "completed"
    ;;

  *)
    echo "❌ Unknown deployment model: $DEPLOYMENT_MODEL"
    exit 1
    ;;
esac

echo ""
```

**State Updates**:
- **staging-prod**: Mark ship:staging complete, set validate-staging to pending
- **direct-prod**: Mark deploy-prod complete
- **local-only**: Mark build-local complete

**Manual Gates**:
- **staging-prod**: Requires staging validation before continuing
- **direct-prod**: Requires explicit confirmation before production deployment
- **local-only**: No manual gate (local build only)

---

## Phase S.4.5a: Local Integration (local-only only)

**Purpose**: Merge feature branch to main/master after successful local build

**Process**:

```bash
# Only for local-only model - merge to main before finalize
if [ "$DEPLOYMENT_MODEL" = "local-only" ]; then
  echo "🔀 Phase S.4.5a: Merge to Main Branch"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  # Get feature info from state
  FEATURE_SLUG=$(yq eval '.feature.slug' "$STATE_FILE")
  FEATURE_TITLE=$(yq eval '.feature.title' "$STATE_FILE")

  # Detect main branch name (main or master)
  if git show-ref --verify --quiet refs/heads/main; then
    MAIN_BRANCH="main"
  elif git show-ref --verify --quiet refs/heads/master; then
    MAIN_BRANCH="master"
  else
    # Try to detect from remote
    MAIN_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')

    if [ -z "$MAIN_BRANCH" ]; then
      echo "❌ Cannot detect main branch (no 'main' or 'master' branch found)"
      echo ""
      echo "Please create a main branch first:"
      echo "  git checkout -b main"
      echo ""
      exit 1
    fi
  fi

  # Get current feature branch
  FEATURE_BRANCH=$(git branch --show-current)

  if [ "$FEATURE_BRANCH" = "$MAIN_BRANCH" ]; then
    echo "⏭️  Already on $MAIN_BRANCH branch, skipping merge"
    echo ""
  else
    echo "Merging: $FEATURE_BRANCH → $MAIN_BRANCH"
    echo ""

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD --; then
      echo "❌ Uncommitted changes detected"
      echo ""
      echo "Please commit or stash changes first:"
      echo "  git add ."
      echo "  git commit -m 'your message'"
      echo ""
      exit 1
    fi

    # Switch to main branch
    echo "Checking out $MAIN_BRANCH..."
    git checkout "$MAIN_BRANCH"

    if [ $? -ne 0 ]; then
      echo "❌ Failed to checkout $MAIN_BRANCH"
      exit 1
    fi

    # Merge feature branch with no-ff to preserve history
    echo "Merging $FEATURE_BRANCH..."
    git merge --no-ff "$FEATURE_BRANCH" -m "feat: merge $FEATURE_SLUG

Feature: $FEATURE_TITLE
Branch: $FEATURE_BRANCH

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

    if [ $? -ne 0 ]; then
      echo "❌ Merge conflict detected"
      echo ""
      echo "Resolve conflicts manually, then run:"
      echo "  git add ."
      echo "  git commit"
      echo "  /ship continue"
      echo ""
      exit 1
    fi

    echo "✅ Merged $FEATURE_BRANCH → $MAIN_BRANCH"
    echo ""

    # Push to origin if remote exists
    if git remote get-url origin >/dev/null 2>&1; then
      echo "Pushing to origin/$MAIN_BRANCH..."

      git push origin "$MAIN_BRANCH"

      if [ $? -eq 0 ]; then
        echo "✅ Pushed to origin/$MAIN_BRANCH"
      else
        echo "⚠️  Failed to push to origin (continuing anyway)"
        echo "   You can push manually later: git push origin $MAIN_BRANCH"
      fi
    else
      echo "⏭️  No remote configured, skipping push"
    fi

    echo ""

    # Offer to delete feature branch
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🧹 Feature Branch Cleanup"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Feature branch '$FEATURE_BRANCH' has been merged."
    echo ""
    read -p "Delete feature branch locally? (yes/no): " DELETE_LOCAL

    if [ "$DELETE_LOCAL" = "yes" ]; then
      git branch -d "$FEATURE_BRANCH"
      echo "✅ Deleted local branch: $FEATURE_BRANCH"

      # If remote exists, offer to delete remote branch
      if git remote get-url origin >/dev/null 2>&1; then
        if git ls-remote --exit-code --heads origin "$FEATURE_BRANCH" >/dev/null 2>&1; then
          echo ""
          read -p "Delete remote branch origin/$FEATURE_BRANCH? (yes/no): " DELETE_REMOTE

          if [ "$DELETE_REMOTE" = "yes" ]; then
            git push origin --delete "$FEATURE_BRANCH"
            echo "✅ Deleted remote branch: origin/$FEATURE_BRANCH"
          else
            echo "⏭️  Kept remote branch: origin/$FEATURE_BRANCH"
          fi
        fi
      fi
    else
      echo "⏭️  Kept feature branch: $FEATURE_BRANCH"
    fi

    echo ""
  fi

  # Update workflow state
  update_workflow_phase "$FEATURE_DIR" "ship:local-integration" "completed"

  echo "✅ Local integration complete"
  echo ""
fi
```

**State Updates**:
- Mark `ship:local-integration` as completed
- Feature code now on main branch
- Ready for version bump and roadmap update

**Blocking Conditions**:
- Merge conflicts
- Uncommitted changes
- Main branch doesn't exist

**Manual Steps**:
- User prompted to delete feature branch (optional)
- User prompted to delete remote branch if exists (optional)

---

## Phase S.4.5: Staging Validation (staging-prod only)

**Purpose**: Validate staging environment before promoting to production

**Process**:

```bash
# Only for staging-prod model
if [ "$DEPLOYMENT_MODEL" != "staging-prod" ]; then
  # Skip to finalize
  update_workflow_phase "$FEATURE_DIR" "ship:finalize" "in_progress"
  # Continue to Phase S.5
else
  # Check manual gate approval
  VALIDATION_GATE_STATUS=$(yq eval '.workflow.manual_gates."validate-staging".status // "pending"' "$STATE_FILE")

  if [ "$VALIDATION_GATE_STATUS" != "approved" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🛑 MANUAL GATE: Staging Validation Required"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Did you complete staging validation?"
    echo ""
    read -p "Approve production deployment? (yes/no): " VALIDATION_APPROVAL

    if [ "$VALIDATION_APPROVAL" != "yes" ]; then
      echo "❌ Production deployment aborted by user"
      update_manual_gate "$FEATURE_DIR" "validate-staging" "rejected"
      exit 1
    fi

    # Record approval
    update_manual_gate "$FEATURE_DIR" "validate-staging" "approved" "$USER"
  fi

  echo ""
  echo "🚀 Phase S.4.5: Deploy to Production"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  # Call /ship-prod
  /ship-prod

  if ! test_phase_completed "$FEATURE_DIR" "ship:production"; then
    echo "❌ Production deployment failed. Check logs and run /ship continue"
    exit 1
  fi

  echo ""
  echo "✅ Production deployment complete"
  update_workflow_phase "$FEATURE_DIR" "ship:production" "completed"
  update_workflow_phase "$FEATURE_DIR" "ship:finalize" "in_progress"
fi

echo ""
```

**State Updates**:
- Mark `ship:validate-staging` as completed
- Mark `ship:production` as completed
- Advance to `ship:finalize`

---

## Phase S.5: Finalize

**Purpose**: Complete deployment workflow with documentation and cleanup

**Process**:

```bash
echo "📝 Phase S.5: Finalize & Document"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Generate deployment summary
FEATURE_SLUG=$(yq eval '.feature.slug' "$STATE_FILE")
FEATURE_TITLE=$(yq eval '.feature.title' "$STATE_FILE")

cat > "$FEATURE_DIR/ship-summary.md" <<EOF
# Ship Summary: $FEATURE_TITLE

**Feature**: $FEATURE_SLUG
**Deployment Model**: $DEPLOYMENT_MODEL
**Completed**: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## Workflow Phases

EOF

# List completed phases
yq eval '.workflow.completed_phases[]' "$STATE_FILE" | while read PHASE; do
  echo "- ✅ $PHASE" >> "$FEATURE_DIR/ship-summary.md"
done

cat >> "$FEATURE_DIR/ship-summary.md" <<EOF

## Quality Gates

EOF

# List quality gate results
yq eval '.quality_gates | to_entries | .[] | "- " + .key + ": " + (.value.passed | tostring)' "$STATE_FILE" | \
  sed 's/true/✅ PASSED/g; s/false/❌ FAILED/g' >> "$FEATURE_DIR/ship-summary.md"

# Add deployment information
cat >> "$FEATURE_DIR/ship-summary.md" <<EOF

## Deployment

EOF

case "$DEPLOYMENT_MODEL" in
  staging-prod)
    STAGING_URL=$(yq eval '.deployment.staging.url // "Not recorded"' "$STATE_FILE")
    PROD_URL=$(yq eval '.deployment.production.url // "Not recorded"' "$STATE_FILE")

    cat >> "$FEATURE_DIR/ship-summary.md" <<EOF
**Staging**: $STAGING_URL
**Production**: $PROD_URL

### Deployment IDs (for rollback)

**Staging:**
$(yq eval '.deployment.staging.deployment_ids | to_entries | .[] | "- " + .key + ": " + .value' "$STATE_FILE")

**Production:**
$(yq eval '.deployment.production.deployment_ids | to_entries | .[] | "- " + .key + ": " + .value' "$STATE_FILE")
EOF
    ;;

  direct-prod)
    PROD_URL=$(yq eval '.deployment.production.url // "Not recorded"' "$STATE_FILE")

    cat >> "$FEATURE_DIR/ship-summary.md" <<EOF
**Production**: $PROD_URL

### Deployment IDs (for rollback)

$(yq eval '.deployment.production.deployment_ids | to_entries | .[] | "- " + .key + ": " + .value' "$STATE_FILE")
EOF
    ;;

  local-only)
    cat >> "$FEATURE_DIR/ship-summary.md" <<EOF
**Local Build**: Completed successfully

Build artifacts available in feature directory.
EOF
    ;;
esac

# Add next steps
cat >> "$FEATURE_DIR/ship-summary.md" <<EOF

## Next Steps

1. Monitor production metrics and error logs
2. Update documentation if needed
3. Communicate release to stakeholders
4. Archive feature artifacts if desired

## Rollback Instructions

EOF

case "$DEPLOYMENT_MODEL" in
  staging-prod|direct-prod)
    cat >> "$FEATURE_DIR/ship-summary.md" <<EOF
If issues arise, you can rollback using the deployment IDs above:

\`\`\`bash
# Rollback app
vercel alias set <previous-deployment-id> <production-url> --token=\$VERCEL_TOKEN

# Rollback API (if applicable)
# Contact DevOps or use your deployment platform's rollback feature
\`\`\`
EOF
    ;;

  local-only)
    cat >> "$FEATURE_DIR/ship-summary.md" <<EOF
For local builds, rollback by reverting git commits:

\`\`\`bash
git revert <commit-sha>
# or
git reset --hard <previous-commit>
\`\`\`
EOF
    ;;
esac

echo "📄 Ship summary created: $FEATURE_DIR/ship-summary.md"

# Update workflow state to complete
update_workflow_phase "$FEATURE_DIR" "ship:finalize" "completed"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Version Management"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Source version management functions
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  source .spec-flow/scripts/bash/version-manager.sh 2>/dev/null || {
    echo "⚠️  Version management not available on Windows (use PowerShell)"
  }
else
  source .spec-flow/scripts/bash/version-manager.sh
fi

# Auto-bump version (non-interactive)
NEW_VERSION=$(auto_version_bump "$FEATURE_DIR" "auto" 2>/dev/null) || {
  echo "⚠️  Could not auto-bump version (package.json may not exist)"
  NEW_VERSION=""
}

if [ -n "$NEW_VERSION" ]; then
  echo "✅ Version bumped to: v$NEW_VERSION"

  # Generate release notes
  generate_release_notes "$FEATURE_DIR" "$NEW_VERSION" 2>/dev/null || {
    echo "⚠️  Could not generate release notes"
  }
else
  echo "⏭️  Skipped version bump"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🗺️  Roadmap Update"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Source roadmap management functions
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  source .spec-flow/scripts/bash/github-roadmap-manager.sh 2>/dev/null || {
    echo "⚠️  Roadmap management not available on Windows (use PowerShell)"
  }
else
  source .spec-flow/scripts/bash/github-roadmap-manager.sh
fi

# Mark feature as shipped in roadmap (GitHub Issues)
if [ -n "$NEW_VERSION" ]; then
  mark_issue_shipped "$FEATURE_SLUG" "$NEW_VERSION" "$(date +%Y-%m-%d)" "$PROD_URL" 2>/dev/null || {
    echo "⚠️  Could not update roadmap (feature may not be in roadmap yet)"
  }
else
  echo "⏭️  Skipped roadmap update (no version)"
fi

echo ""

# Display final summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Feature: $FEATURE_TITLE"
echo "Model: $DEPLOYMENT_MODEL"
echo ""

case "$DEPLOYMENT_MODEL" in
  staging-prod)
    PROD_URL=$(yq eval '.deployment.production.url // "Not recorded"' "$STATE_FILE")
    echo "🚀 Production: $PROD_URL"
    ;;
  direct-prod)
    PROD_URL=$(yq eval '.deployment.production.url // "Not recorded"' "$STATE_FILE")
    echo "🚀 Production: $PROD_URL"
    ;;
  local-only)
    echo "✅ Local build completed"
    ;;
esac

echo ""
echo "📊 View full summary: $FEATURE_DIR/ship-summary.md"
echo "📁 All artifacts: $FEATURE_DIR/"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

**Artifacts Generated**:
- `ship-summary.md` - Complete deployment summary with URLs, IDs, and rollback instructions

**State Updates**:
- Mark `ship:finalize` as completed
- Workflow status set to completed

---

## Resume Capability

The `/ship continue` command allows resuming from interruptions:

**Scenarios**:
1. **Pre-flight failure** - Fix issues, run `/ship continue` to retry validation
2. **Build failure** - Fix build errors, run `/ship continue` to retry
3. **Manual gate** - After preview testing, run `/ship continue` to proceed
4. **Staging validation** - After staging checks, run `/ship continue` for production
5. **Deployment failure** - Fix CI issues, run `/ship continue` to retry

**Implementation**:
- State file tracks current phase and status
- `get_next_phase()` determines correct resume point
- Failed phases can be retried without rerunning successful phases
- Manual gates preserve approval status

---

## Status Visualization

Use `/ship status` to view current deployment state (see `/deploy-status` command for full implementation):

```bash
if [ "$1" = "status" ]; then
  # Load most recent feature
  FEATURE_DIR=$(ls -td specs/*/ | head -1)
  STATE_FILE="$FEATURE_DIR/workflow-state.yaml"

  # Auto-migrate from JSON if needed
  if [ ! -f "$STATE_FILE" ] && [ -f "$FEATURE_DIR/workflow-state.json" ]; then
    echo "🔄 Migrating workflow state to YAML..."
    yq eval -P "$FEATURE_DIR/workflow-state.json" > "$STATE_FILE"
  fi

  if [ ! -f "$STATE_FILE" ]; then
    echo "❌ No workflow state found"
    exit 1
  fi

  # Display current state
  CURRENT_PHASE=$(yq eval '.workflow.phase' "$STATE_FILE")
  WORKFLOW_STATUS=$(yq eval '.workflow.status' "$STATE_FILE")
  DEPLOYMENT_MODEL=$(yq eval '.deployment_model' "$STATE_FILE")

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🚀 Deployment Status"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "Feature: $(yq eval '.feature.title' "$STATE_FILE")"
  echo "Model: $DEPLOYMENT_MODEL"
  echo "Current Phase: $CURRENT_PHASE"
  echo "Status: $WORKFLOW_STATUS"
  echo ""
  echo "Completed Phases:"
  yq eval '.workflow.completed_phases[]' "$STATE_FILE" | sed 's/^/  ✅ /'
  echo ""

  # Show manual gates
  echo "Manual Gates:"
  yq eval '.workflow.manual_gates | to_entries | .[] | "  " + .key + ": " + .value.status' "$STATE_FILE" | \
    sed 's/pending/⏸️  PENDING/g; s/approved/✅ APPROVED/g; s/rejected/❌ REJECTED/g'
  echo ""

  # Show quality gates
  echo "Quality Gates:"
  yq eval '.quality_gates | to_entries | .[] | "  " + .key + ": " + (.value.passed | tostring)' "$STATE_FILE" | \
    sed 's/true/✅ PASSED/g; s/false/❌ FAILED/g'
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  exit 0
fi
```

---

## Error Handling

**Common Failures**:
1. **Pre-flight validation** - Build/Docker/env errors → Fix and retry
2. **Optimize phase** - Code quality issues → Address and retry
3. **Staging deployment** - CI failures → Check logs and retry
4. **Rollback test** - Vercel CLI issues → Verify credentials and retry
5. **Production deployment** - Workflow failures → Manual rollback may be needed

**Recovery**:
- All failures preserve state for resume
- Run `/ship continue` after fixing issues
- Use `/ship status` to see what failed
- Check feature directory logs for detailed error messages

---

## Integration Points

**Commands Called**:
- `/optimize` - Code review and production readiness
- `/preview` - Manual UI/UX testing gate
- `/ship-staging` - Staging deployment (staging-prod model)
- `/validate-staging` - Staging validation (staging-prod model)
- `/ship-prod` - Production deployment (staging-prod model)
- `/deploy-prod` - Direct production deployment (direct-prod model)
- `/build-local` - Local build (local-only model)

**State Management**:
- All phases tracked in `workflow-state.yaml`
- Quality gates recorded with pass/fail status
- Deployment IDs stored for rollback capability
- Manual gates preserve approval status
- Version tracking and git tags
- Roadmap status automatically updated

---

## Success Criteria

- ✅ Pre-flight validation passes (builds, Docker, env, CI)
- ✅ Code review and optimization complete
- ✅ Manual preview testing approved
- ✅ Deployment succeeds based on model
- ✅ Rollback capability verified (staging-prod only)
- ✅ Production deployment complete (if applicable)
- ✅ Documentation generated with rollback instructions

---

## Notes

- **First time setup**: Run `/ship` to start fresh workflow
- **Resuming**: Use `/ship continue` after manual gates or failures
- **Status check**: Use `/ship status` to see current state
- **Aborting**: Manual gates allow rejecting deployment
- **Rollback**: Deployment IDs stored in state file for emergency rollback

This command replaces the need to manually run each post-implementation phase, providing a unified, state-tracked deployment experience with proper quality gates and rollback capability.
</instructions>
