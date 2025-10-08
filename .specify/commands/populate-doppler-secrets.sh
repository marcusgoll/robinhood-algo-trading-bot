#!/bin/bash
# .specify/commands/populate-doppler-secrets.sh
# Interactive script to populate Doppler with all required secrets

set -e

PROJECT_NAME="cfipros"

echo "=========================================="
echo "DOPPLER SECRETS POPULATION"
echo "=========================================="
echo ""

# Check if Doppler is installed and authenticated
if ! command -v doppler &>/dev/null; then
  echo "❌ Doppler CLI not found"
  echo "   Run: bash .specify/commands/setup-doppler.sh"
  exit 1
fi

if ! doppler me &>/dev/null; then
  echo "❌ Not authenticated with Doppler"
  echo "   Run: doppler login"
  exit 1
fi

echo "✅ Doppler CLI ready"
echo ""

# Function to set secret interactively
set_secret() {
  local config=$1
  local key=$2
  local description=$3
  local default_value=$4

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Config: $config"
  echo "Key: $key"
  echo "Description: $description"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  # Check if secret already exists
  EXISTING=$(doppler secrets get "$key" --project "$PROJECT_NAME" --config "$config" --plain 2>/dev/null || echo "")

  if [ -n "$EXISTING" ]; then
    echo "Current value: ${EXISTING:0:20}..." # Show first 20 chars
    read -p "Keep existing value? (Y/n): " KEEP
    if [ "$KEEP" = "n" ] || [ "$KEEP" = "N" ]; then
      :  # Continue to prompt for new value
    else
      echo "✅ Keeping existing value"
      echo ""
      return
    fi
  fi

  # Prompt for value
  if [ -n "$default_value" ]; then
    read -p "Enter value (default: $default_value): " VALUE
    VALUE=${VALUE:-$default_value}
  else
    read -p "Enter value: " VALUE
  fi

  if [ -z "$VALUE" ]; then
    echo "⚠️  Skipping empty value"
    echo ""
    return
  fi

  # Set the secret
  echo "$VALUE" | doppler secrets set "$key" --project "$PROJECT_NAME" --config "$config"

  if [ $? -eq 0 ]; then
    echo "✅ Secret set: $key"
  else
    echo "❌ Failed to set: $key"
  fi

  echo ""
}

# Function to bulk upload from file
bulk_upload() {
  local config=$1
  local file=$2

  if [ ! -f "$file" ]; then
    echo "❌ File not found: $file"
    return 1
  fi

  echo "Uploading secrets from: $file → $config"

  doppler secrets upload "$file" --project "$PROJECT_NAME" --config "$config"

  if [ $? -eq 0 ]; then
    echo "✅ Bulk upload successful"
  else
    echo "❌ Bulk upload failed"
    return 1
  fi
}

# Ask for upload method
echo "How would you like to populate secrets?"
echo ""
echo "1. Interactive (guided, one secret at a time)"
echo "2. Bulk upload from .env files"
echo "3. Skip (I'll do it manually later)"
echo ""
read -p "Choose method (1/2/3): " METHOD

if [ "$METHOD" = "3" ]; then
  echo ""
  echo "Manual setup instructions:"
  echo "  1. View template: .doppler/secrets-template.env"
  echo "  2. Set secrets: doppler secrets set KEY=value --project cfipros --config [config]"
  echo "  3. Bulk upload: doppler secrets upload .env --project cfipros --config [config]"
  echo ""
  exit 0
fi

# Select environment
echo ""
echo "Which environment?"
echo "1. Development (dev)"
echo "2. Staging"
echo "3. Production"
echo "4. All environments"
echo ""
read -p "Choose environment (1/2/3/4): " ENV_CHOICE

case $ENV_CHOICE in
  1) ENVIRONMENTS=("dev") ;;
  2) ENVIRONMENTS=("staging") ;;
  3) ENVIRONMENTS=("production") ;;
  4) ENVIRONMENTS=("dev" "staging" "production") ;;
  *)
    echo "❌ Invalid choice"
    exit 1
    ;;
esac

# Select service
echo ""
echo "Which service?"
echo "1. Marketing"
echo "2. App"
echo "3. API"
echo "4. All services"
echo ""
read -p "Choose service (1/2/3/4): " SERVICE_CHOICE

case $SERVICE_CHOICE in
  1) SERVICES=("marketing") ;;
  2) SERVICES=("app") ;;
  3) SERVICES=("api") ;;
  4) SERVICES=("marketing" "app" "api") ;;
  *)
    echo "❌ Invalid choice"
    exit 1
    ;;
esac

echo ""

# Process each environment + service combination
for env in "${ENVIRONMENTS[@]}"; do
  for service in "${SERVICES[@]}"; do
    CONFIG_NAME="${env}_${service}"

    echo "=========================================="
    echo "POPULATING: $CONFIG_NAME"
    echo "=========================================="
    echo ""

    if [ "$METHOD" = "2" ]; then
      # Bulk upload mode
      echo "Looking for .env file..."

      # Check common locations
      POSSIBLE_FILES=(
        ".doppler/${CONFIG_NAME}.env"
        ".doppler/${env}.env"
        "apps/${service}/.env.${env}"
        "apps/${service}/.env"
        "api/.env.${env}"
        "api/.env"
      )

      ENV_FILE=""
      for file in "${POSSIBLE_FILES[@]}"; do
        if [ -f "$file" ]; then
          ENV_FILE="$file"
          break
        fi
      done

      if [ -z "$ENV_FILE" ]; then
        echo "No .env file found. Please specify path:"
        read -p "Path to .env file (or skip): " USER_FILE

        if [ -n "$USER_FILE" ] && [ -f "$USER_FILE" ]; then
          ENV_FILE="$USER_FILE"
        else
          echo "⚠️  Skipping $CONFIG_NAME"
          echo ""
          continue
        fi
      fi

      bulk_upload "$CONFIG_NAME" "$ENV_FILE"
    else
      # Interactive mode
      echo "Setting secrets for: $CONFIG_NAME"
      echo ""

      case $service in
        marketing)
          # Marketing secrets
          set_secret "$CONFIG_NAME" "NODE_ENV" "Environment" "$env"

          if [ "$env" = "production" ]; then
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_MARKETING_URL" "Marketing site URL" "https://cfipros.com"
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_APP_URL" "App URL" "https://app.cfipros.com"
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_API_URL" "API URL" "https://api.cfipros.com"
          elif [ "$env" = "staging" ]; then
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_MARKETING_URL" "Marketing site URL" "https://staging.cfipros.com"
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_APP_URL" "App URL" "https://app.staging.cfipros.com"
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_API_URL" "API URL" "https://api.staging.cfipros.com"
          else
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_MARKETING_URL" "Marketing site URL" "http://localhost:3000"
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_APP_URL" "App URL" "http://localhost:3001"
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_API_URL" "API URL" "http://localhost:8000"
          fi

          set_secret "$CONFIG_NAME" "VERCEL_ORG_ID" "Vercel organization ID" ""
          set_secret "$CONFIG_NAME" "VERCEL_PROJECT_ID" "Vercel project ID (marketing)" ""
          ;;

        app)
          # App secrets
          set_secret "$CONFIG_NAME" "NODE_ENV" "Environment" "$env"

          if [ "$env" = "production" ]; then
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_APP_URL" "App URL" "https://app.cfipros.com"
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_MARKETING_URL" "Marketing URL" "https://cfipros.com"
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_API_URL" "API URL (public)" "https://api.cfipros.com"
            set_secret "$CONFIG_NAME" "BACKEND_API_URL" "API URL (server-side)" "https://api.cfipros.com"
          elif [ "$env" = "staging" ]; then
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_APP_URL" "App URL" "https://app.staging.cfipros.com"
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_MARKETING_URL" "Marketing URL" "https://staging.cfipros.com"
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_API_URL" "API URL (public)" "https://api.staging.cfipros.com"
            set_secret "$CONFIG_NAME" "BACKEND_API_URL" "API URL (server-side)" "https://api.staging.cfipros.com"
          else
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_APP_URL" "App URL" "http://localhost:3001"
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_MARKETING_URL" "Marketing URL" "http://localhost:3000"
            set_secret "$CONFIG_NAME" "NEXT_PUBLIC_API_URL" "API URL (public)" "http://localhost:8000"
            set_secret "$CONFIG_NAME" "BACKEND_API_URL" "API URL (server-side)" "http://localhost:8000"
          fi

          set_secret "$CONFIG_NAME" "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY" "Clerk publishable key" ""
          set_secret "$CONFIG_NAME" "CLERK_SECRET_KEY" "Clerk secret key" ""
          set_secret "$CONFIG_NAME" "UPSTASH_REDIS_REST_URL" "Upstash Redis URL" ""
          set_secret "$CONFIG_NAME" "UPSTASH_REDIS_REST_TOKEN" "Upstash Redis token" ""
          set_secret "$CONFIG_NAME" "NEXT_PUBLIC_HCAPTCHA_SITE_KEY" "hCaptcha site key" ""
          set_secret "$CONFIG_NAME" "HCAPTCHA_SECRET_KEY" "hCaptcha secret key" ""
          set_secret "$CONFIG_NAME" "JWT_SECRET" "JWT secret (min 32 chars)" ""
          set_secret "$CONFIG_NAME" "NEXT_PUBLIC_POSTHOG_KEY" "PostHog key" ""
          set_secret "$CONFIG_NAME" "NEXT_PUBLIC_POSTHOG_HOST" "PostHog host" "https://app.posthog.com"
          set_secret "$CONFIG_NAME" "VERCEL_ORG_ID" "Vercel organization ID" ""
          set_secret "$CONFIG_NAME" "VERCEL_PROJECT_ID" "Vercel project ID (app)" ""
          ;;

        api)
          # API secrets
          set_secret "$CONFIG_NAME" "ENVIRONMENT" "Environment" "$env"

          if [ "$env" = "development" ]; then
            set_secret "$CONFIG_NAME" "DATABASE_URL" "Database URL" "postgresql://postgres:postgres@localhost:5432/cfipros_dev"
            set_secret "$CONFIG_NAME" "DIRECT_URL" "Direct database URL" "postgresql://postgres:postgres@localhost:5432/cfipros_dev"
            set_secret "$CONFIG_NAME" "REDIS_URL" "Redis URL" "redis://localhost:6379"
            set_secret "$CONFIG_NAME" "ALLOWED_ORIGINS" "CORS origins" "http://localhost:3000,http://localhost:3001"
            set_secret "$CONFIG_NAME" "RAILWAY_STATIC_URL" "Railway static URL" "http://localhost:8000"
          else
            set_secret "$CONFIG_NAME" "DATABASE_URL" "Database URL (Supabase pooler)" ""
            set_secret "$CONFIG_NAME" "DIRECT_URL" "Direct database URL (Supabase)" ""
            set_secret "$CONFIG_NAME" "REDIS_URL" "Redis URL (Upstash)" ""

            if [ "$env" = "production" ]; then
              set_secret "$CONFIG_NAME" "ALLOWED_ORIGINS" "CORS origins" "https://app.cfipros.com,https://cfipros.com"
              set_secret "$CONFIG_NAME" "RAILWAY_STATIC_URL" "Railway static URL" "https://api.cfipros.com"
            else
              set_secret "$CONFIG_NAME" "ALLOWED_ORIGINS" "CORS origins" "https://app.staging.cfipros.com,https://staging.cfipros.com"
              set_secret "$CONFIG_NAME" "RAILWAY_STATIC_URL" "Railway static URL" "https://api-staging.railway.app"
            fi
          fi

          set_secret "$CONFIG_NAME" "OPENAI_API_KEY" "OpenAI API key" ""
          set_secret "$CONFIG_NAME" "VISION_MODEL" "Vision model" "gpt-4o-2024-08-06"
          set_secret "$CONFIG_NAME" "SECRET_KEY" "JWT secret key (min 32 chars)" ""
          set_secret "$CONFIG_NAME" "RAILWAY_PROJECT_ID" "Railway project ID" ""
          ;;
      esac
    fi

    echo ""
    echo "✅ $CONFIG_NAME populated"
    echo ""
  done
done

echo "=========================================="
echo "✅ SECRETS POPULATION COMPLETE"
echo "=========================================="
echo ""

echo "📋 Verify secrets:"
for env in "${ENVIRONMENTS[@]}"; do
  for service in "${SERVICES[@]}"; do
    CONFIG_NAME="${env}_${service}"
    echo "  doppler secrets list --project $PROJECT_NAME --config $CONFIG_NAME"
  done
done
echo ""

echo "📝 Next steps:"
echo "  1. Verify all secrets are set correctly"
echo "  2. Setup GitHub Actions: bash .specify/commands/setup-doppler-github.sh"
echo "  3. Setup Vercel: bash .specify/commands/setup-doppler-vercel.sh"
echo "  4. Setup Railway: bash .specify/commands/setup-doppler-railway.sh"
echo ""
