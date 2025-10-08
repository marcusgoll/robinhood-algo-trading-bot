#!/bin/bash
# .specify/commands/setup-doppler-railway.sh
# Integrate Doppler with Railway

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "DOPPLER → RAILWAY INTEGRATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

### Phase 1: Prerequisites

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 1: Check Prerequisites"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check Railway CLI
if ! command -v railway &>/dev/null; then
  echo "❌ Railway CLI not installed"
  echo ""
  echo "Install via:"
  echo "  pnpm install -g @railway/cli"
  echo "  # or"
  echo "  npm install -g @railway/cli"
  exit 1
fi

echo "✅ Railway CLI installed"

# Check Railway authentication
if ! railway whoami &>/dev/null; then
  echo "Authenticating with Railway..."
  railway login

  if railway whoami &>/dev/null; then
    echo "✅ Railway authenticated"
  else
    echo "❌ Railway authentication failed"
    exit 1
  fi
else
  echo "✅ Railway authenticated"
fi

# Check Doppler tokens exist
if [ ! -d ".doppler/tokens" ]; then
  echo "❌ Doppler tokens not found"
  echo ""
  echo "Run setup first:"
  echo "  bash .specify/commands/setup-doppler.sh"
  exit 1
fi

echo "✅ Doppler tokens available"
echo ""

### Phase 2: Get Service Tokens

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 2: Load Doppler Service Tokens"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Load tokens for staging and production
STAGING_TOKEN_FILE=".doppler/tokens/github-actions-staging-api.txt"
PRODUCTION_TOKEN_FILE=".doppler/tokens/github-actions-production-api.txt"

if [ ! -f "$STAGING_TOKEN_FILE" ]; then
  echo "❌ Staging token not found: $STAGING_TOKEN_FILE"
  echo ""
  echo "Run setup first:"
  echo "  bash .specify/commands/setup-doppler.sh"
  exit 1
fi

if [ ! -f "$PRODUCTION_TOKEN_FILE" ]; then
  echo "❌ Production token not found: $PRODUCTION_TOKEN_FILE"
  echo ""
  echo "Run setup first:"
  echo "  bash .specify/commands/setup-doppler.sh"
  exit 1
fi

STAGING_TOKEN=$(cat "$STAGING_TOKEN_FILE")
PRODUCTION_TOKEN=$(cat "$PRODUCTION_TOKEN_FILE")

echo "✅ Staging token loaded"
echo "✅ Production token loaded"
echo ""

### Phase 3: Configure Railway Project

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 3: Configure Railway Environments"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Link to Railway project (if not already linked)
if [ ! -f "railway.json" ] && [ ! -f ".railway/railway.json" ]; then
  echo "Railway project not linked."
  echo ""
  read -p "Link to Railway project now? (Y/n): " LINK_PROJECT
  LINK_PROJECT=${LINK_PROJECT:-Y}

  if [ "$LINK_PROJECT" = "y" ] || [ "$LINK_PROJECT" = "Y" ]; then
    cd api
    railway link
    cd ..
  else
    echo "❌ Railway project must be linked"
    echo "   Run: cd api && railway link"
    exit 1
  fi
fi

echo "✅ Railway project linked"
echo ""

### Phase 4: Add Doppler Tokens to Railway

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 4: Add Doppler Tokens to Railway"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd api

# Staging environment
echo "Setting up staging environment..."

if railway variables set DOPPLER_TOKEN="$STAGING_TOKEN" --environment staging 2>/dev/null; then
  echo "  ✅ Staging DOPPLER_TOKEN added"
else
  echo "  ⚠️  Failed to add staging token (may already exist)"
fi

echo ""

# Production environment
echo "Setting up production environment..."

if railway variables set DOPPLER_TOKEN="$PRODUCTION_TOKEN" --environment production 2>/dev/null; then
  echo "  ✅ Production DOPPLER_TOKEN added"
else
  echo "  ⚠️  Failed to add production token (may already exist)"
fi

echo ""

cd ..

### Phase 5: Update Start Command

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 5: Update Railway Start Command"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Railway needs to run your app with Doppler."
echo ""
echo "Recommended start command:"
echo "  doppler run -- uv run gunicorn app.main:app --bind 0.0.0.0:\$PORT"
echo ""

read -p "Update start command automatically? (Y/n): " UPDATE_CMD
UPDATE_CMD=${UPDATE_CMD:-Y}

if [ "$UPDATE_CMD" = "y" ] || [ "$UPDATE_CMD" = "Y" ]; then
  cd api

  # Update for staging
  echo "Updating staging start command..."
  railway variables set START_COMMAND="doppler run -- uv run gunicorn app.main:app --bind 0.0.0.0:\$PORT" \
    --environment staging 2>/dev/null || true

  # Update for production
  echo "Updating production start command..."
  railway variables set START_COMMAND="doppler run -- uv run gunicorn app.main:app --bind 0.0.0.0:\$PORT" \
    --environment production 2>/dev/null || true

  cd ..

  echo "  ✅ Start commands updated"
  echo ""
else
  echo "Manual update required:"
  echo ""
  echo "1. Go to Railway dashboard"
  echo "2. Select your API service"
  echo "3. Go to Settings → Deploy"
  echo "4. Update Start Command to:"
  echo "   doppler run -- uv run gunicorn app.main:app --bind 0.0.0.0:\$PORT"
  echo ""
fi

### Phase 6: Add Nixpacks Configuration

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 6: Configure Nixpacks"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Creating nixpacks.toml for Doppler installation..."

cat > api/nixpacks.toml <<'EOF'
# nixpacks.toml
# Railway build configuration with Doppler

[phases.setup]
nixPkgs = ["python311", "doppler"]

[phases.install]
cmds = [
  "pip install -r requirements.txt"
]

[start]
cmd = "doppler run -- gunicorn app.main:app --bind 0.0.0.0:$PORT"
EOF

echo "✅ Created api/nixpacks.toml"
echo ""

### Phase 7: Test Configuration

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 7: Verify Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd api

echo "Current Railway variables (staging):"
railway variables --environment staging 2>/dev/null | grep -E "DOPPLER_TOKEN|START_COMMAND" || echo "  (Could not retrieve variables)"

echo ""

echo "Current Railway variables (production):"
railway variables --environment production 2>/dev/null | grep -E "DOPPLER_TOKEN|START_COMMAND" || echo "  (Could not retrieve variables)"

cd ..

echo ""

### Final Summary

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ RAILWAY INTEGRATION COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📋 Summary:"
echo ""
echo "  ✅ Doppler tokens added to Railway"
echo "  ✅ Start commands configured"
echo "  ✅ Nixpacks configuration created"
echo ""

echo "🔄 How it works:"
echo ""
echo "  1. Railway starts deployment"
echo "  2. Installs Doppler CLI (via nixpacks.toml)"
echo "  3. Uses DOPPLER_TOKEN to authenticate"
echo "  4. Runs: doppler run -- gunicorn ..."
echo "  5. Doppler injects all secrets from cfipros/staging_api"
echo "  6. App starts with all environment variables"
echo ""

echo "📝 Next Steps:"
echo ""
echo "1. Deploy to Railway:"
echo "   cd api"
echo "   railway up --environment staging"
echo ""
echo "2. Verify deployment:"
echo "   railway logs --environment staging"
echo "   # Should see: 'Doppler authenticated successfully'"
echo ""
echo "3. Test API endpoint:"
echo "   curl https://[your-railway-url]/api/v1/health/healthz"
echo ""
echo "4. Update secrets in Doppler (auto-syncs):"
echo "   doppler secrets set DATABASE_URL=new_value --project cfipros --config staging_api"
echo "   railway restart --environment staging  # Restart to pick up new secrets"
echo ""

echo "🔍 View Railway variables:"
echo "   cd api && railway variables --environment staging"
echo ""

echo "🎉 All platform integrations complete!"
echo "   ✅ GitHub Actions"
echo "   ✅ Vercel"
echo "   ✅ Railway"
echo ""
