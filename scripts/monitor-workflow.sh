#!/bin/bash
# Real-time workflow progress monitor for spec-flow

FEATURE_DIR="specs/004-order-execution-enhanced"
FEATURE_NUM="004"
FEATURE_SLUG="order-execution-enhanced"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Phase progress tracking
declare -A PHASE_ARTIFACTS=(
    [0]="spec.md NOTES.md checklists/requirements.md"
    [1]="plan.md research.md"
    [2]="tasks.md"
    [3]="analysis-report.md"
    [4]="NOTES.md"
    [5]="optimization-report.md code-review-report.md"
)

declare -A PHASE_NAMES=(
    [0]="Specification"
    [1]="Planning"
    [2]="Task Breakdown"
    [3]="Analysis"
    [4]="Implementation"
    [5]="Optimization"
)

print_header() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 SPEC-FLOW WORKFLOW MONITOR"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Feature: $FEATURE_SLUG (Feature #$FEATURE_NUM)"
    echo "Status updated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
}

check_branch_status() {
    echo -e "${BLUE}🔀 GIT BRANCH STATUS${NC}"

    if git rev-parse --verify --quiet feat/$FEATURE_NUM-$FEATURE_SLUG 2>/dev/null; then
        echo -e "  ${GREEN}✅${NC} Feature branch exists: feat/$FEATURE_NUM-$FEATURE_SLUG"
        CURRENT=$(git branch --show-current)
        if [ "$CURRENT" = "feat/$FEATURE_NUM-$FEATURE_SLUG" ]; then
            echo -e "  ${GREEN}✅${NC} Currently checked out"
        else
            echo -e "  ${YELLOW}ℹ️ ${NC}On branch: $CURRENT"
        fi
    else
        echo -e "  ${YELLOW}⏳${NC} Feature branch not yet created"
    fi
    echo ""
}

check_phase_progress() {
    echo -e "${BLUE}📋 PHASE PROGRESS${NC}"

    for phase in 0 1 2 3 4 5; do
        phase_name="${PHASE_NAMES[$phase]}"
        artifacts="${PHASE_ARTIFACTS[$phase]}"
        completed=0
        total=0

        for artifact in $artifacts; do
            total=$((total + 1))
            if [ -f "$FEATURE_DIR/$artifact" ]; then
                completed=$((completed + 1))
            fi
        done

        if [ $completed -eq $total ] && [ $total -gt 0 ]; then
            echo -e "  ${GREEN}✅${NC} Phase $phase: $phase_name ($completed/$total artifacts)"
        elif [ $completed -gt 0 ]; then
            echo -e "  ${YELLOW}⏳${NC} Phase $phase: $phase_name ($completed/$total artifacts)"
        else
            echo -e "  ${YELLOW}⏳${NC} Phase $phase: $phase_name (pending)"
        fi
    done
    echo ""
}

check_artifacts() {
    echo -e "${BLUE}📁 CREATED ARTIFACTS${NC}"

    if [ ! -d "$FEATURE_DIR" ]; then
        echo -e "  ${YELLOW}⏳${NC} Feature directory not yet created"
        echo ""
        return
    fi

    file_count=$(find "$FEATURE_DIR" -type f 2>/dev/null | wc -l)

    if [ $file_count -eq 0 ]; then
        echo -e "  ${YELLOW}⏳${NC} No artifacts yet (waiting for /specify to complete)"
    else
        echo -e "  ${GREEN}✅${NC} Total files: $file_count"
        echo ""
        find "$FEATURE_DIR" -type f -name "*.md" -o -name "*.yaml" 2>/dev/null | while read f; do
            relative_path="${f#$FEATURE_DIR/}"
            lines=$(wc -l < "$f" 2>/dev/null || echo "0")
            echo "     📄 $relative_path ($lines lines)"
        done
    fi
    echo ""
}

check_git_commits() {
    echo -e "${BLUE}💾 GIT COMMITS${NC}"

    commits=$(git log --oneline --all -- "specs/$FEATURE_NUM-$FEATURE_SLUG" 2>/dev/null | wc -l)

    if [ $commits -eq 0 ]; then
        echo -e "  ${YELLOW}⏳${NC} No commits yet for this feature"
    else
        echo -e "  ${GREEN}✅${NC} Total commits: $commits"
        git log --oneline --all -- "specs/$FEATURE_NUM-$FEATURE_SLUG" 2>/dev/null | head -5 | while read line; do
            echo "     📌 $line"
        done
        if [ $commits -gt 5 ]; then
            remaining=$((commits - 5))
            echo "     ... and $remaining more commits"
        fi
    fi
    echo ""
}

check_spec_details() {
    echo -e "${BLUE}📝 SPECIFICATION DETAILS${NC}"

    if [ ! -f "$FEATURE_DIR/spec.md" ]; then
        echo -e "  ${YELLOW}⏳${NC} spec.md not yet created"
    else
        echo -e "  ${GREEN}✅${NC} spec.md created"

        # Extract section count
        sections=$(grep "^## " "$FEATURE_DIR/spec.md" 2>/dev/null | wc -l)
        echo "     📋 Sections: $sections"
        grep "^## " "$FEATURE_DIR/spec.md" | head -8 | sed 's/## /        • /'

        # Check for clarifications
        clarifications=$(grep -c "\\[NEEDS CLARIFICATION" "$FEATURE_DIR/spec.md" 2>/dev/null || echo 0)
        if [ $clarifications -gt 0 ]; then
            echo -e "     ${YELLOW}⚠️  Clarifications needed: $clarifications${NC}"
        else
            echo "     ✅ No clarifications needed"
        fi
    fi
    echo ""
}

check_requirements() {
    echo -e "${BLUE}✅ REQUIREMENTS${NC}"

    if [ ! -f "$FEATURE_DIR/spec.md" ]; then
        echo -e "  ${YELLOW}⏳${NC} Requirements not yet documented"
    else
        fr_count=$(grep -c "^- \[FR-" "$FEATURE_DIR/spec.md" 2>/dev/null || echo 0)
        nfr_count=$(grep -c "^- \[NFR-" "$FEATURE_DIR/spec.md" 2>/dev/null || echo 0)
        total=$((fr_count + nfr_count))

        if [ $total -eq 0 ]; then
            echo -e "  ${YELLOW}⏳${NC} No requirements documented yet"
        else
            echo -e "  ${GREEN}✅${NC} Requirements: $fr_count FR, $nfr_count NFR"
        fi
    fi
    echo ""
}

check_tasks_breakdown() {
    echo -e "${BLUE}📋 TASKS BREAKDOWN${NC}"

    if [ ! -f "$FEATURE_DIR/tasks.md" ]; then
        echo -e "  ${YELLOW}⏳${NC} Tasks not yet created (Phase 2)"
    else
        total_tasks=$(grep -c "^- \[" "$FEATURE_DIR/tasks.md" 2>/dev/null || echo 0)
        completed_tasks=$(grep -c "^- \[x\]" "$FEATURE_DIR/tasks.md" 2>/dev/null || echo 0)
        pending_tasks=$((total_tasks - completed_tasks))

        echo -e "  ${GREEN}✅${NC} Total: $total_tasks | Completed: $completed_tasks | Pending: $pending_tasks"
    fi
    echo ""
}

print_next_steps() {
    echo -e "${BLUE}🚀 NEXT STEPS${NC}"

    # Check current phase completion
    if [ ! -f "$FEATURE_DIR/spec.md" ]; then
        echo "  ⏳ Waiting for Phase 0 (/specify) to complete"
        echo "     The specification phase is running..."
        echo "     → Once complete, Phase 1 (/plan) will start automatically"
    elif [ ! -f "$FEATURE_DIR/plan.md" ]; then
        echo "  ✅ Phase 0 (Specification) complete"
        echo "  ⏳ Phase 1 (/plan) in progress..."
        echo "     → Once complete, Phase 2 (/tasks) will start"
    elif [ ! -f "$FEATURE_DIR/tasks.md" ]; then
        echo "  ✅ Phase 1 (Planning) complete"
        echo "  ⏳ Phase 2 (/tasks) in progress..."
        echo "     → Once complete, Phase 3 (/analyze) will start"
    elif [ ! -f "$FEATURE_DIR/analysis-report.md" ]; then
        echo "  ✅ Phase 2 (Task Breakdown) complete"
        echo "  ⏳ Phase 3 (/analyze) in progress..."
        echo "     → Once complete, Phase 4 (/implement) will start"
    elif [ ! -f "$FEATURE_DIR/optimization-report.md" ]; then
        echo "  ✅ Phase 3 (Analysis) complete"
        echo "  ⏳ Phase 4 (/implement) in progress..."
        echo "     → Once complete, Phase 5 (/optimize) will start"
    else
        echo "  ✅ All phases complete!"
        echo "  🎉 Ready for manual preview testing (/preview)"
    fi
    echo ""
}

print_footer() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💡 TIPS:"
    echo "   • Run this script periodically: bash monitor-workflow.sh"
    echo "   • Check detailed spec: cat $FEATURE_DIR/spec.md"
    echo "   • View recent commits: git log --oneline -10"
    echo "   • Check feature branch: git status"
    echo ""
}

# Main execution
print_header
check_branch_status
check_phase_progress
check_artifacts
check_git_commits
check_spec_details
check_requirements
check_tasks_breakdown
print_next_steps
print_footer
