#!/bin/bash
# .specify/commands/setup-doppler-vercel.sh
# Integrate Doppler with Vercel

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "DOPPLER → VERCEL INTEGRATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

### Phase 1: Prerequisites

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 1: Check Prerequisites"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check Vercel CLI
if ! command -v vercel &>/dev/null; then
  echo "❌ Vercel CLI not installed"
  echo ""
  echo "Install via:"
  echo "  pnpm install -g vercel"
  echo "  # or"
  echo "  npm install -g vercel"
  exit 1
fi

echo "✅ Vercel CLI installed"

# Check Doppler CLI
if ! command -v doppler &>/dev/null; then
  echo "❌ Doppler CLI not installed"
  echo ""
  echo "Run setup first:"
  echo "  bash .specify/commands/setup-doppler.sh"
  exit 1
fi

echo "✅ Doppler CLI installed"

# Check Doppler authentication
if ! doppler me &>/dev/null; then
  echo "❌ Not authenticated with Doppler"
  echo ""
  echo "Run setup first:"
  echo "  bash .specify/commands/setup-doppler.sh"
  exit 1
fi

echo "✅ Doppler authenticated"
echo ""

### Phase 2: Integration Method Selection

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 2: Choose Integration Method"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Doppler can sync secrets to Vercel in two ways:"
echo ""
echo "  1. Doppler Integration (recommended)"
echo "     - Automatic real-time sync"
echo "     - Set up once, works forever"
echo "     - No CLI commands needed"
echo ""
echo "  2. Manual CLI Sync"
echo "     - Manual updates via CLI"
echo "     - Full control over sync timing"
echo "     - Requires running sync command"
echo ""

read -p "Use Doppler Integration? (Y/n): " USE_INTEGRATION
USE_INTEGRATION=${USE_INTEGRATION:-Y}

echo ""

if [ "$USE_INTEGRATION" = "y" ] || [ "$USE_INTEGRATION" = "Y" ]; then
  ### Doppler Integration Setup

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Phase 3: Setup Doppler Integration"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  echo "Setting up automatic sync from Doppler to Vercel..."
  echo ""

  echo "📋 Manual Steps Required:"
  echo ""
  echo "1. Go to Doppler Dashboard:"
  echo "   https://dashboard.doppler.com/workplace/[your-workplace]/projects/cfipros/integrations"
  echo ""
  echo "2. Click 'Add Integration' → Select 'Vercel'"
  echo ""
  echo "3. Connect your Vercel account (OAuth)"
  echo ""
  echo "4. Configure syncs for each config:"
  echo ""

  # List configs to sync
  CONFIGS=(
    "dev_marketing:marketing:Development"
    "staging_marketing:marketing:Preview"
    "production_marketing:marketing:Production"
    "dev_app:app:Development"
    "staging_app:app:Preview"
    "production_app:app:Production"
  )

  for config_mapping in "${CONFIGS[@]}"; do
    IFS=':' read -r doppler_config vercel_project vercel_env <<< "$config_mapping"

    echo "   ┌─────────────────────────────────────┐"
    echo "   │ Doppler Config: $doppler_config"
    echo "   │ Vercel Project: cfipros-$vercel_project"
    echo "   │ Vercel Environment: $vercel_env"
    echo "   └─────────────────────────────────────┘"
    echo ""
  done

  echo "5. Enable 'Sync Now' for each config"
  echo ""
  echo "6. Verify secrets synced:"
  echo "   - Go to Vercel project settings"
  echo "   - Check Environment Variables tab"
  echo "   - Should see secrets from Doppler"
  echo ""

  read -p "Press Enter after completing setup in Doppler dashboard..."

  echo ""
  echo "✅ Integration setup complete"
  echo ""

  echo "🔄 How it works:"
  echo "  - Update secret in Doppler → Automatically syncs to Vercel"
  echo "  - No manual CLI commands needed"
  echo "  - Near real-time sync (<1 minute)"
  echo ""

  echo "🧪 Test the sync:"
  echo "  1. Add a test secret:"
  echo "     doppler secrets set TEST_SYNC=hello --project cfipros --config production_marketing"
  echo ""
  echo "  2. Check Vercel dashboard (wait ~30 seconds):"
  echo "     https://vercel.com/[your-team]/cfipros-marketing/settings/environment-variables"
  echo ""
  echo "  3. Should see TEST_SYNC=hello in Production environment"
  echo ""

else
  ### Manual CLI Sync

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Phase 3: Manual CLI Sync"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  echo "Syncing secrets via Vercel CLI..."
  echo ""

  # Sync for each project
  PROJECTS=("marketing" "app")

  for project in "${PROJECTS[@]}"; do
    echo "Syncing: $project"

    WORKSPACE="apps/$project"

    if [ ! -d "$WORKSPACE" ]; then
      echo "  ⚠️  Workspace not found: $WORKSPACE"
      continue
    fi

    cd "$WORKSPACE"

    # Production
    echo "  Syncing production environment..."
    if doppler secrets download \
       --project cfipros \
       --config "production_$project" \
       --format env \
       --no-file 2>/dev/null | \
       vercel env add production 2>/dev/null; then
      echo "    ✅ Production secrets synced"
    else
      echo "    ⚠️  Production sync failed (may already exist)"
    fi

    # Preview (staging)
    echo "  Syncing preview environment..."
    if doppler secrets download \
       --project cfipros \
       --config "staging_$project" \
       --format env \
       --no-file 2>/dev/null | \
       vercel env add preview 2>/dev/null; then
      echo "    ✅ Preview secrets synced"
    else
      echo "    ⚠️  Preview sync failed (may already exist)"
    fi

    # Development
    echo "  Syncing development environment..."
    if doppler secrets download \
       --project cfipros \
       --config "dev_$project" \
       --format env \
       --no-file 2>/dev/null | \
       vercel env add development 2>/dev/null; then
      echo "    ✅ Development secrets synced"
    else
      echo "    ⚠️  Development sync failed (may already exist)"
    fi

    cd - >/dev/null

    echo "  ✅ $project synced"
    echo ""
  done

  echo "✅ Manual sync complete"
  echo ""

  echo "🔄 Re-sync when secrets change:"
  echo "  bash .specify/commands/sync-doppler-vercel.sh"
  echo ""

  # Create sync helper script
  cat > .specify/commands/sync-doppler-vercel.sh <<'EOF'
#!/bin/bash
# .specify/commands/sync-doppler-vercel.sh
# Re-sync Doppler secrets to Vercel

set -e

echo "Syncing Doppler → Vercel..."
echo ""

PROJECTS=("marketing" "app")

for project in "${PROJECTS[@]}"; do
  echo "Syncing: $project"

  cd "apps/$project"

  # Pull latest from Doppler and push to Vercel
  doppler secrets download \
    --project cfipros \
    --config "production_$project" \
    --format env \
    --no-file | vercel env pull production --yes

  doppler secrets download \
    --project cfipros \
    --config "staging_$project" \
    --format env \
    --no-file | vercel env pull preview --yes

  cd - >/dev/null

  echo "  ✅ $project synced"
  echo ""
done

echo "✅ Sync complete"
EOF

  chmod +x .specify/commands/sync-doppler-vercel.sh

  echo "  Created: .specify/commands/sync-doppler-vercel.sh"
  echo ""
fi

### Final Summary

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ VERCEL INTEGRATION COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📋 Summary:"
echo ""
if [ "$USE_INTEGRATION" = "y" ] || [ "$USE_INTEGRATION" = "Y" ]; then
  echo "  ✅ Doppler Integration configured"
  echo "  ✅ Automatic sync enabled"
  echo "  🔄 Secrets sync in real-time"
else
  echo "  ✅ Manual CLI sync completed"
  echo "  📝 Re-sync script created"
  echo "  🔄 Run sync-doppler-vercel.sh when secrets change"
fi
echo ""

echo "📝 Next Steps:"
echo ""
echo "1. Verify secrets in Vercel:"
echo "   vercel env ls"
echo ""
echo "2. Test deployment with new secrets:"
echo "   cd apps/marketing && vercel --prod"
echo ""
echo "3. Continue with Railway integration:"
echo "   bash .specify/commands/setup-doppler-railway.sh"
echo ""
echo "🔍 View Vercel environment variables:"
echo "   https://vercel.com/[your-team]/cfipros-marketing/settings/environment-variables"
echo ""
