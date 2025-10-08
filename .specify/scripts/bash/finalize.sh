#!/bin/bash
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Finalize: Documentation Housekeeping"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

#═══════════════════════════════════════════════════════════
# Phase F.1: LOAD CONTEXT
#═══════════════════════════════════════════════════════════

echo "Loading deployment context..."
echo ""

# Find latest ship-report.md
SHIP_REPORTS=$(find specs -name "ship-report.md" 2>/dev/null | grep -v archive)

if [ -z "$SHIP_REPORTS" ]; then
  echo "❌ No ship-report.md found"
  echo ""
  echo "Run /phase-2-ship first to deploy to production"
  echo "Expected: specs/[feature-slug]/ship-report.md"
  exit 1
fi

# Use most recent report
LATEST_REPORT=$(echo "$SHIP_REPORTS" | xargs ls -t | head -1)

# Extract feature slug from path
SLUG=$(echo "$LATEST_REPORT" | sed 's|specs/||' | sed 's|/.*||')
FEATURE_DIR="specs/$SLUG"
SHIP_REPORT="$LATEST_REPORT"

echo "✅ Feature: $SLUG"
echo "✅ Ship report: $SHIP_REPORT"
echo ""

# Validate feature directory
if [ ! -d "$FEATURE_DIR" ]; then
  echo "❌ Feature directory not found: $FEATURE_DIR"
  exit 1
fi

# Initialize file paths
SPEC_FILE="$FEATURE_DIR/spec.md"
CHANGELOG="CHANGELOG.md"
README="README.md"
API_DOCS="docs/API_ENDPOINTS.md"
HELP_DIR="docs/help/features"
HELP_INDEX="docs/help/README.md"

# Extract version from ship-report.md
VERSION=$(grep "Version:" "$SHIP_REPORT" | head -1 | grep -oE "v[0-9]+\.[0-9]+\.[0-9]+" | head -1)

if [ -z "$VERSION" ]; then
  echo "❌ Could not extract version from ship-report.md"
  exit 1
fi

echo "Version: $VERSION"
echo ""

# Get previous version for commit range
PREV_VERSION=$(git tag --list "v*" --sort=-version:refname | grep -v "^$VERSION$" | head -1)

if [ -z "$PREV_VERSION" ]; then
  echo "⚠️  No previous version found"
  echo "   This is the first release"
  PREV_VERSION=$(git rev-list --max-parents=0 HEAD)
fi

echo "Commit range: $PREV_VERSION → $VERSION"
echo ""

#═══════════════════════════════════════════════════════════
# Phase F.2: UPDATE CHANGELOG.md
#═══════════════════════════════════════════════════════════

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Updating CHANGELOG.md"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Extract changes from commits
COMMITS=$(git log "$PREV_VERSION..$VERSION" --pretty=format:"%s" 2>/dev/null || echo "")

if [ -z "$COMMITS" ]; then
  echo "⚠️  No commits found in range"
  echo "   Using ship report for changes"
fi

# Categorize commits
ADDED=$(echo "$COMMITS" | grep -E "^feat:" | sed 's/^feat: /- /' || echo "")
CHANGED=$(echo "$COMMITS" | grep -E "^refactor:|^perf:" | sed 's/^[^:]*: /- /' || echo "")
FIXED=$(echo "$COMMITS" | grep -E "^fix:" | sed 's/^fix: /- /' || echo "")
SECURITY=$(echo "$COMMITS" | grep -E "^security:" | sed 's/^security: /- /' || echo "")

# Fallback to spec.md if no categorized commits
if [ -z "$ADDED" ] && [ -f "$SPEC_FILE" ]; then
  echo "Extracting features from spec.md..."
  ADDED=$(sed -n '/## Functional Requirements/,/^## /p' "$SPEC_FILE" | \
          grep "^- " | \
          head -5 | \
          sed 's/^- /- /')
fi

# Generate changelog entry
CHANGELOG_ENTRY="## [$VERSION] - $(date +%Y-%m-%d)

### Added

$ADDED

### Changed

$CHANGED

### Fixed

$FIXED

### Security

$SECURITY
"

# Create CHANGELOG.md if it doesn't exist
if [ ! -f "$CHANGELOG" ]; then
  echo "Creating CHANGELOG.md..."
  cat > "$CHANGELOG" <<EOF
# Changelog

All notable changes to CFIPros will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

EOF
fi

# Insert new entry at top (after header)
awk -v entry="$CHANGELOG_ENTRY" '
  NR==1 { print; next }
  NR==2 { print; next }
  NR==3 { print; next }
  NR==4 { print; next }
  NR==5 { print; next }
  NR==6 { print entry; print }
  NR>6 { print }
' "$CHANGELOG" > /tmp/changelog-updated.md

mv /tmp/changelog-updated.md "$CHANGELOG"

echo "✅ CHANGELOG.md updated with $VERSION"
echo ""

#═══════════════════════════════════════════════════════════
# Phase F.3: UPDATE README.md
#═══════════════════════════════════════════════════════════

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Updating README.md"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Extract feature title from spec.md
FEATURE_TITLE=$(grep "^# " "$SPEC_FILE" | head -1 | sed 's/^# //' || echo "$SLUG")

# Extract one-line summary
FEATURE_SUMMARY=$(sed -n '/## Summary/,/^## /p' "$SPEC_FILE" | \
                  grep -v "^## " | \
                  grep -v "^$" | \
                  head -1 || echo "New feature")

echo "Feature: $FEATURE_TITLE"
echo "Summary: $FEATURE_SUMMARY"
echo ""

# Update version badge
if grep -q "badge/version-" "$README"; then
  echo "Updating version badge..."
  sed -i "s/badge\/version-[^-]*-blue/badge\/version-$VERSION-blue/" "$README"
  echo "✅ Version badge updated"
else
  echo "⚠️  No version badge found in README.md"
fi

echo ""

# Add feature to features list (if ## Features section exists)
if grep -q "## Features" "$README"; then
  echo "Adding feature to README features list..."

  # Create feature entry with NEW marker
  FEATURE_ENTRY="- 🎯 **$FEATURE_TITLE** - $FEATURE_SUMMARY (NEW $VERSION)"

  # Check if feature already exists
  if grep -q "$FEATURE_TITLE" "$README"; then
    echo "⚠️  Feature already in README.md"
  else
    # Insert after ## Features line
    awk -v entry="$FEATURE_ENTRY" '
      /^## Features/ { print; print entry; next }
      { print }
    ' "$README" > /tmp/readme-updated.md

    mv /tmp/readme-updated.md "$README"
    echo "✅ Feature added to README.md"
  fi
else
  echo "⚠️  No ## Features section in README.md"
fi

echo ""

#═══════════════════════════════════════════════════════════
# Phase F.4: GENERATE USER DOCUMENTATION
#═══════════════════════════════════════════════════════════

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Generating User Documentation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create help directory if needed
mkdir -p "$HELP_DIR"

HELP_FILE="$HELP_DIR/$SLUG.md"

echo "Creating help article: $HELP_FILE"
echo ""

# Extract user stories from spec.md
USER_STORIES=$(sed -n '/## User Stories/,/^## /p' "$SPEC_FILE" | \
               grep -v "^## " | \
               grep -v "^$" || echo "")

# Extract functional requirements
REQUIREMENTS=$(sed -n '/## Functional Requirements/,/^## /p' "$SPEC_FILE" | \
               grep "^- " | \
               head -5 || echo "")

# Generate help article
cat > "$HELP_FILE" <<EOF
# $FEATURE_TITLE

$FEATURE_SUMMARY

**Added in**: $VERSION

## How to Use

$USER_STORIES

## Features

$REQUIREMENTS

## Benefits

- Faster workflow
- Improved user experience
- Better accuracy

## Troubleshooting

### Feature not working?

1. Refresh the page
2. Clear browser cache
3. Check browser console for errors
4. Contact support: support@cfipros.com

### Performance issues?

1. Check internet connection
2. Try smaller file sizes
3. Disable browser extensions
4. Contact support if issue persists

## Related Documentation

- [API Documentation](../../API_ENDPOINTS.md)
- [FAQ](../FAQ.md)
- [Support](../SUPPORT.md)

---
**Last updated**: $(date +%Y-%m-%d)
**Version**: $VERSION
EOF

echo "✅ Help article created: $HELP_FILE"
echo ""

# Update help index
if [ -f "$HELP_INDEX" ]; then
  echo "Updating help index..."

  # Check if feature already in index
  if grep -q "$SLUG" "$HELP_INDEX"; then
    echo "⚠️  Feature already in help index"
  else
    # Add to index
    echo "- [$FEATURE_TITLE](features/$SLUG.md) - $FEATURE_SUMMARY" >> "$HELP_INDEX"
    echo "✅ Help index updated"
  fi
else
  echo "Creating help index..."

  cat > "$HELP_INDEX" <<EOF
# Help Documentation

## Features

- [$FEATURE_TITLE](features/$SLUG.md) - $FEATURE_SUMMARY

## Getting Started

- [Quick Start](QUICK_START.md)
- [FAQ](FAQ.md)
- [Support](SUPPORT.md)

---
**Last updated**: $(date +%Y-%m-%d)
EOF

  echo "✅ Help index created"
fi

echo ""

#═══════════════════════════════════════════════════════════
# Phase F.5: UPDATE API DOCS
#═══════════════════════════════════════════════════════════

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Updating API Documentation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if API files changed
API_CHANGES=$(git diff "$PREV_VERSION..$VERSION" --name-only | grep "api/app/api/" || echo "")

if [ -z "$API_CHANGES" ]; then
  echo "✅ No API changes detected"
  echo ""
else
  echo "API files changed:"
  echo "$API_CHANGES" | sed 's/^/  - /'
  echo ""

  if [ -f "$API_DOCS" ]; then
    echo "⚠️  Manual update needed for API_ENDPOINTS.md"
    echo ""
    echo "Changed endpoints:"
    echo "$API_CHANGES" | sed 's/api\/app\/api\///' | sed 's/\.py$//' | sed 's/^/  - /'
    echo ""
    echo "Review and update: $API_DOCS"
    echo ""
  else
    echo "⚠️  API_ENDPOINTS.md not found"
    echo "   Create it manually: $API_DOCS"
    echo ""
  fi
fi

#═══════════════════════════════════════════════════════════
# Phase F.6: MANAGE GITHUB MILESTONES
#═══════════════════════════════════════════════════════════

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Managing GitHub Milestones"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Find milestone matching version pattern (v1.2.x matches v1.2.0, v1.2.1, etc.)
VERSION_PATTERN=$(echo "$VERSION" | sed 's/\.[0-9]*$//')

MILESTONE=$(gh api repos/:owner/:repo/milestones \
  --jq ".[] | select(.title | test(\"$VERSION_PATTERN\")) | .number" 2>/dev/null | head -1)

if [ -n "$MILESTONE" ]; then
  echo "Found milestone: #$MILESTONE"
  echo ""

  # Close milestone
  echo "Closing milestone..."
  gh api repos/:owner/:repo/milestones/"$MILESTONE" \
    -X PATCH \
    -f state='closed' \
    -f due_on="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    >/dev/null 2>&1

  if [ $? -eq 0 ]; then
    echo "✅ Milestone closed"
  else
    echo "⚠️  Could not close milestone (may need permissions)"
  fi

  echo ""

  # Link release to milestone
  echo "Linking release to milestone..."
  gh release edit "$VERSION" \
    --notes-file <(cat <(gh release view "$VERSION" --json body -q .body) \
                        <(echo ""; echo "**Milestone**: #$MILESTONE")) \
    2>/dev/null || echo "⚠️  Could not update release notes"

  echo ""
else
  echo "⚠️  No matching milestone found for $VERSION_PATTERN"
  echo ""
fi

# Create next milestone
NEXT_VERSION=$(echo "$VERSION" | awk -F. '{print $1"."($2+1)".0"}')

echo "Creating next milestone: $NEXT_VERSION"
echo ""

EXISTING_NEXT=$(gh api repos/:owner/:repo/milestones \
  --jq ".[] | select(.title==\"$NEXT_VERSION\") | .number" 2>/dev/null)

if [ -n "$EXISTING_NEXT" ]; then
  echo "⚠️  Milestone $NEXT_VERSION already exists"
else
  # Calculate due date (2 weeks from now)
  DUE_DATE=$(date -u -d "+2 weeks" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v+2w +%Y-%m-%dT%H:%M:%SZ)

  gh api repos/:owner/:repo/milestones \
    -X POST \
    -f title="$NEXT_VERSION" \
    -f description="Next release milestone" \
    -f due_on="$DUE_DATE" \
    >/dev/null 2>&1

  if [ $? -eq 0 ]; then
    echo "✅ Next milestone created: $NEXT_VERSION"
    echo "   Due: $(date -d "$DUE_DATE" +%Y-%m-%d 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$DUE_DATE" +%Y-%m-%d)"
  else
    echo "⚠️  Could not create next milestone (may need permissions)"
  fi
fi

echo ""

#═══════════════════════════════════════════════════════════
# Phase F.7: COMMIT DOCUMENTATION
#═══════════════════════════════════════════════════════════

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Committing Documentation Changes"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if there are changes to commit
CHANGES=$(git status --porcelain)

if [ -z "$CHANGES" ]; then
  echo "✅ No changes to commit (documentation up to date)"
  echo ""
else
  echo "Changes to commit:"
  git status --short | sed 's/^/  /'
  echo ""

  # Stage documentation files
  git add "$CHANGELOG" "$README" "$HELP_DIR" "$HELP_INDEX" 2>/dev/null

  # Commit
  git commit -m "docs: update documentation for $VERSION

Updated:
- CHANGELOG.md (added $VERSION section)
- README.md (updated features)
- Help documentation (added $SLUG)

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

  if [ $? -eq 0 ]; then
    echo "✅ Changes committed"
    echo ""

    # Push to main
    echo "Pushing to main..."
    git push origin main

    if [ $? -eq 0 ]; then
      echo "✅ Changes pushed to main"
    else
      echo "⚠️  Failed to push changes"
      echo "   Push manually: git push origin main"
    fi
  else
    echo "❌ Failed to commit changes"
    exit 1
  fi

  echo ""
fi

#═══════════════════════════════════════════════════════════
# Phase F.8: OUTPUT SUMMARY
#═══════════════════════════════════════════════════════════

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 Documentation Updated"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "**Version**: $VERSION"
echo "**Feature**: $SLUG"
echo ""

echo "### Files Updated"
echo ""
echo "- ✅ CHANGELOG.md (Added $VERSION section)"
echo "- ✅ README.md (Updated features, badges)"
echo "- ✅ $HELP_FILE (New help article)"

if [ -n "$API_CHANGES" ]; then
  echo "- ⚠️  $API_DOCS (Manual review needed)"
else
  echo "- ✅ $API_DOCS (No changes needed)"
fi

echo ""

echo "### GitHub"
echo ""

if [ -n "$MILESTONE" ]; then
  echo "- ✅ Closed milestone: #$MILESTONE"
else
  echo "- ⚠️  No milestone found"
fi

echo "- ✅ Created next milestone: $NEXT_VERSION"
echo ""

echo "### Commits"
echo ""
git log -1 --oneline | sed 's/^/- /'
echo ""

echo "### Next Steps"
echo ""
echo "1. Review documentation accuracy"
echo "2. Update marketing site copy (if needed)"
echo "3. Announce release on social media"
echo "4. Monitor user feedback"
echo ""

echo "---"
echo "**Workflow complete**: ... → phase-2-ship → finalize ✅"
echo ""
