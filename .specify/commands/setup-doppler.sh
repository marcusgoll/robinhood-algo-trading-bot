#!/bin/bash
# .specify/commands/setup-doppler.sh
# Install Doppler CLI and configure secret management

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "DOPPLER SETUP - Centralized Secret Management"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

### Phase 1: Install Doppler CLI

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 1: Install Doppler CLI"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if already installed
if command -v doppler &>/dev/null; then
  echo "✅ Doppler CLI already installed"
  doppler --version
else
  echo "Installing Doppler CLI..."

  # Detect OS
  if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if command -v brew &>/dev/null; then
      brew install dopplerhq/cli/doppler
    else
      echo "❌ Homebrew not found. Install from: https://docs.doppler.com/docs/install-cli"
      exit 1
    fi
  elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    curl -sLf --retry 3 --tlsv1.2 --proto "=https" 'https://packages.doppler.com/public/cli/install.sh' | sudo sh
  elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    echo "For Windows, install via:"
    echo "  scoop install doppler"
    echo "Or download from: https://docs.doppler.com/docs/install-cli"
    exit 1
  else
    echo "❌ Unsupported OS: $OSTYPE"
    echo "   Install manually: https://docs.doppler.com/docs/install-cli"
    exit 1
  fi

  if command -v doppler &>/dev/null; then
    echo "✅ Doppler CLI installed"
  else
    echo "❌ Installation failed"
    exit 1
  fi
fi

echo ""

### Phase 2: Authentication

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 2: Authenticate Doppler"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if already authenticated
if doppler me &>/dev/null; then
  echo "✅ Already authenticated"
  doppler me
else
  echo "Authenticating with Doppler..."
  echo ""
  echo "This will open your browser for login."
  echo ""
  read -p "Press Enter to continue..."

  doppler login

  if doppler me &>/dev/null; then
    echo ""
    echo "✅ Authentication successful"
    doppler me
  else
    echo "❌ Authentication failed"
    exit 1
  fi
fi

echo ""

### Phase 3: Create Project Structure

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 3: Create Doppler Project"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

PROJECT_NAME="cfipros"

# Check if project exists
if doppler projects list --json 2>/dev/null | jq -e ".[] | select(.name==\"$PROJECT_NAME\")" >/dev/null 2>&1; then
  echo "✅ Project '$PROJECT_NAME' already exists"
else
  echo "Creating project: $PROJECT_NAME"
  doppler projects create "$PROJECT_NAME" --description "CFI Pros monorepo secrets"

  if [ $? -eq 0 ]; then
    echo "✅ Project created"
  else
    echo "❌ Project creation failed"
    exit 1
  fi
fi

echo ""

### Phase 4: Create Environments and Configs

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 4: Create Environments and Configs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create environments: dev, staging, production
ENVIRONMENTS=("dev" "staging" "production")

for env in "${ENVIRONMENTS[@]}"; do
  echo "Setting up environment: $env"

  # Check if environment exists
  if doppler environments list --project "$PROJECT_NAME" --json 2>/dev/null | \
     jq -e ".[] | select(.slug==\"$env\")" >/dev/null 2>&1; then
    echo "  ✅ Environment '$env' exists"
  else
    echo "  Creating environment: $env"
    doppler environments create "$env" --project "$PROJECT_NAME"
  fi

  # Create configs for each service
  SERVICES=("marketing" "app" "api")

  for service in "${SERVICES[@]}"; do
    CONFIG_NAME="${env}_${service}"

    echo "  Checking config: $CONFIG_NAME"

    if doppler configs list --project "$PROJECT_NAME" --json 2>/dev/null | \
       jq -e ".[] | select(.name==\"$CONFIG_NAME\")" >/dev/null 2>&1; then
      echo "    ✅ Config exists: $CONFIG_NAME"
    else
      echo "    Creating config: $CONFIG_NAME"
      doppler configs create "$CONFIG_NAME" \
        --project "$PROJECT_NAME" \
        --environment "$env"
    fi
  done

  echo ""
done

echo "✅ All environments and configs created"
echo ""

### Phase 5: Setup Local Development

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 5: Configure Local Development"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Setup doppler.yaml for each service
WORKSPACES=(
  "apps/marketing:marketing"
  "apps/app:app"
  "api:api"
)

for workspace_config in "${WORKSPACES[@]}"; do
  IFS=':' read -r workspace service <<< "$workspace_config"

  echo "Configuring: $workspace"

  # Create doppler.yaml
  cat > "$workspace/doppler.yaml" <<EOF
# Doppler configuration for $service
setup:
  project: $PROJECT_NAME
  config: dev_$service
EOF

  # Setup Doppler for workspace
  (
    cd "$workspace"
    doppler setup --project "$PROJECT_NAME" --config "dev_$service" --no-interactive
  )

  echo "  ✅ $workspace configured"
  echo ""
done

echo "✅ Local development configured"
echo ""

### Phase 6: Migrate Existing Secrets

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 6: Migrate Existing Secrets"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "Do you want to upload existing .env files to Doppler? (y/N): " MIGRATE

if [ "$MIGRATE" = "y" ] || [ "$MIGRATE" = "Y" ]; then
  for workspace_config in "${WORKSPACES[@]}"; do
    IFS=':' read -r workspace service <<< "$workspace_config"
    ENV_FILE="$workspace/.env"

    if [ -f "$ENV_FILE" ]; then
      echo "Uploading: $ENV_FILE → dev_$service"

      doppler secrets upload "$ENV_FILE" \
        --project "$PROJECT_NAME" \
        --config "dev_$service"

      if [ $? -eq 0 ]; then
        echo "  ✅ Secrets uploaded"

        # Backup and remove .env
        mv "$ENV_FILE" "$ENV_FILE.backup"
        echo "  📦 Original saved to: $ENV_FILE.backup"
      else
        echo "  ⚠️  Upload failed, keeping .env file"
      fi
    else
      echo "  ℹ️  No .env file found: $ENV_FILE"
    fi

    echo ""
  done
else
  echo "Skipping migration"
  echo ""
  echo "Manual upload later:"
  echo "  doppler secrets upload .env --project $PROJECT_NAME --config [config]"
fi

echo ""

### Phase 7: Create Service Tokens

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 7: Create Service Tokens"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Service tokens allow CI/CD and platforms to access secrets."
echo ""

# Create .doppler directory for tokens
mkdir -p .doppler/tokens
chmod 700 .doppler

# Create tokens for staging and production
for env in staging production; do
  for service in marketing app api; do
    CONFIG_NAME="${env}_${service}"
    TOKEN_NAME="github-actions-${env}-${service}"

    echo "Creating token: $TOKEN_NAME"

    # Create service token (capture output, suppress errors if already exists)
    TOKEN=$(doppler configs tokens create "$TOKEN_NAME" \
      --project "$PROJECT_NAME" \
      --config "$CONFIG_NAME" \
      --plain 2>/dev/null || true)

    if [ -n "$TOKEN" ]; then
      # Save to secure location
      echo "$TOKEN" > ".doppler/tokens/${TOKEN_NAME}.txt"
      chmod 600 ".doppler/tokens/${TOKEN_NAME}.txt"

      echo "  ✅ Token created and saved"
      echo "  📝 Token saved to: .doppler/tokens/${TOKEN_NAME}.txt"
    else
      # Token may already exist, try to list existing tokens
      echo "  ⚠️  Token may already exist or creation failed"
      echo "  💡 Check existing tokens:"
      echo "      doppler configs tokens list --project $PROJECT_NAME --config $CONFIG_NAME"
    fi

    echo ""
  done
done

# Ensure .doppler is in .gitignore
if [ -f .gitignore ]; then
  if ! grep -q "^\.doppler/$" .gitignore 2>/dev/null; then
    echo ".doppler/" >> .gitignore
    echo "✅ Added .doppler/ to .gitignore"
  fi
else
  echo ".doppler/" > .gitignore
  echo "✅ Created .gitignore with .doppler/"
fi

echo ""

### Phase 8: Update Dev Scripts

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 8: Create Dev Wrapper Scripts"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create dev-with-doppler.sh wrapper
cat > scripts/dev-with-doppler.sh <<'EOF'
#!/bin/bash
# scripts/dev-with-doppler.sh
# Start dev server with Doppler secrets

set -e

if [ ! -f "doppler.yaml" ]; then
  echo "❌ Not in a workspace directory with doppler.yaml"
  echo "   Run from: apps/marketing, apps/app, or api"
  exit 1
fi

SERVICE=$(basename "$(pwd)")

echo "Starting $SERVICE with Doppler secrets..."
echo ""

# Different commands for different services
if [ "$SERVICE" = "api" ]; then
  doppler run -- uv run uvicorn app.main:app --reload
else
  doppler run -- pnpm dev
fi
EOF

chmod +x scripts/dev-with-doppler.sh

echo "✅ Created scripts/dev-with-doppler.sh"
echo ""

### Final Summary

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DOPPLER SETUP COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📋 Setup Summary:"
echo ""
echo "  ✅ Doppler CLI installed"
echo "  ✅ Authenticated"
echo "  ✅ Project 'cfipros' created"
echo "  ✅ Environments: dev, staging, production"
echo "  ✅ Configs: [env]_[service] (9 total)"
echo "  ✅ Local workspaces configured"
echo "  ✅ Service tokens created"
echo ""

echo "📝 Next Steps:"
echo ""
echo "1. Add secrets to Doppler:"
echo "   doppler secrets set KEY=value --project cfipros --config dev_marketing"
echo ""
echo "2. Run dev server with Doppler:"
echo "   cd apps/marketing"
echo "   doppler run -- pnpm dev"
echo "   # Or use wrapper:"
echo "   bash ../../scripts/dev-with-doppler.sh"
echo ""
echo "3. Setup GitHub Actions:"
echo "   bash .specify/commands/setup-doppler-github.sh"
echo ""
echo "4. Setup Vercel integration:"
echo "   bash .specify/commands/setup-doppler-vercel.sh"
echo ""
echo "5. Setup Railway integration:"
echo "   bash .specify/commands/setup-doppler-railway.sh"
echo ""
echo "🔐 Service tokens location: .doppler/tokens/"
echo "   ⚠️  These are sensitive! Add to GitHub Secrets, Vercel, Railway"
echo ""
echo "📚 View all configs:"
echo "   doppler configs list --project cfipros"
echo ""
echo "🔍 View secrets:"
echo "   doppler secrets list --project cfipros --config dev_marketing"
echo ""
