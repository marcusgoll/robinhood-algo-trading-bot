#!/bin/bash
# .specify/commands/setup-doppler-github.sh
# Integrate Doppler with GitHub Actions

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "DOPPLER → GITHUB ACTIONS INTEGRATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

### Phase 1: Prerequisites

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 1: Check Prerequisites"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if GitHub CLI is installed
if ! command -v gh &>/dev/null; then
  echo "❌ GitHub CLI not installed"
  echo ""
  echo "Install via:"
  if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "  brew install gh"
  elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "  See: https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
  else
    echo "  scoop install gh  (Windows)"
  fi
  exit 1
fi

echo "✅ GitHub CLI installed"

# Check authentication
if ! gh auth status &>/dev/null; then
  echo "Authenticating with GitHub..."
  gh auth login
fi

if gh auth status &>/dev/null; then
  echo "✅ GitHub authenticated"
else
  echo "❌ GitHub authentication failed"
  exit 1
fi

echo ""

### Phase 2: Verify Doppler Tokens

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 2: Verify Doppler Tokens"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

TOKEN_DIR=".doppler/tokens"

if [ ! -d "$TOKEN_DIR" ]; then
  echo "❌ No tokens found at: $TOKEN_DIR"
  echo ""
  echo "Run setup first:"
  echo "  bash .specify/commands/setup-doppler.sh"
  exit 1
fi

# Count token files
TOKEN_COUNT=$(find "$TOKEN_DIR" -name "*.txt" | wc -l)

if [ "$TOKEN_COUNT" -eq 0 ]; then
  echo "❌ No token files found in: $TOKEN_DIR"
  echo ""
  echo "Run setup first:"
  echo "  bash .specify/commands/setup-doppler.sh"
  exit 1
fi

echo "✅ Found $TOKEN_COUNT token files"
echo ""

### Phase 3: Add Tokens to GitHub Secrets

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 3: Add Tokens to GitHub Secrets"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Adding Doppler service tokens to GitHub Secrets..."
echo ""

SUCCESS_COUNT=0
FAILED_COUNT=0

for token_file in "$TOKEN_DIR"/*.txt; do
  if [ -f "$token_file" ]; then
    # Convert filename to GitHub secret name
    # github-actions-staging-marketing.txt → GITHUB_ACTIONS_STAGING_MARKETING
    TOKEN_NAME=$(basename "$token_file" .txt | tr '[:lower:]' '[:upper:]' | tr '-' '_')
    TOKEN_VALUE=$(cat "$token_file")

    echo "Adding secret: $TOKEN_NAME"

    # Add to GitHub (redirect stdin from token value)
    if echo "$TOKEN_VALUE" | gh secret set "$TOKEN_NAME" 2>/dev/null; then
      echo "  ✅ Secret added to GitHub"
      ((SUCCESS_COUNT++))
    else
      echo "  ❌ Failed to add secret"
      ((FAILED_COUNT++))
    fi

    echo ""
  fi
done

echo "Summary:"
echo "  ✅ $SUCCESS_COUNT secrets added"
if [ "$FAILED_COUNT" -gt 0 ]; then
  echo "  ❌ $FAILED_COUNT secrets failed"
fi

echo ""

### Phase 4: Verify Secrets

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 4: Verify GitHub Secrets"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Current GitHub Secrets:"
gh secret list

echo ""

### Phase 5: Update Workflows

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 5: Workflow Integration Instructions"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Doppler tokens are now in GitHub Secrets."
echo ""
echo "To use in workflows, add these steps:"
echo ""
cat <<'EOF'
# Install Doppler CLI
- name: Install Doppler CLI
  uses: dopplerhq/cli-action@v3

# Load secrets for marketing
- name: Setup Marketing Environment
  working-directory: apps/marketing
  run: |
    echo "${{ secrets.GITHUB_ACTIONS_STAGING_MARKETING }}" | \
      doppler configure set token --scope .
    doppler secrets download --no-file --format env > .env

# Load secrets for app
- name: Setup App Environment
  working-directory: apps/app
  run: |
    echo "${{ secrets.GITHUB_ACTIONS_STAGING_APP }}" | \
      doppler configure set token --scope .
    doppler secrets download --no-file --format env > .env

# Load secrets for api
- name: Setup API Environment
  working-directory: api
  run: |
    echo "${{ secrets.GITHUB_ACTIONS_STAGING_API }}" | \
      doppler configure set token --scope .
    doppler secrets download --no-file --format env > .env

# Then run builds with secrets available
- name: Build Marketing
  working-directory: apps/marketing
  run: doppler run -- pnpm build

- name: Build App
  working-directory: apps/app
  run: doppler run -- pnpm build
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ GITHUB ACTIONS INTEGRATION COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📋 Summary:"
echo ""
echo "  ✅ Doppler tokens added to GitHub Secrets"
echo "  ✅ $SUCCESS_COUNT secrets configured"
echo ""

echo "📝 Next Steps:"
echo ""
echo "1. Update .github/workflows/verify.yml with Doppler steps (see above)"
echo "2. Update .github/workflows/deploy-staging.yml"
echo "3. Update .github/workflows/deploy-production.yml"
echo ""
echo "4. Test workflow:"
echo "   git push"
echo "   # Check Actions tab for successful secret loading"
echo ""
echo "5. Continue with platform integrations:"
echo "   bash .specify/commands/setup-doppler-vercel.sh"
echo "   bash .specify/commands/setup-doppler-railway.sh"
echo ""
echo "🔍 View secrets:"
echo "   gh secret list"
echo ""
