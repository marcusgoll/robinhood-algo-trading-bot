#!/bin/bash
# Verification script for trading bot database setup
# Run this to verify database is properly configured

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

echo "=================================================="
echo "Trading Bot Database Verification"
echo "=================================================="
echo ""

# Load DATABASE_URL from .env if it exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | grep DATABASE_URL | xargs)
    if [ -n "$DATABASE_URL" ]; then
        print_success "DATABASE_URL loaded from .env"
    else
        print_error "DATABASE_URL not found in .env"
        exit 1
    fi
else
    print_error ".env file not found"
    exit 1
fi

# Parse DATABASE_URL
# Format: postgresql://user:password@host:port/database
DB_USER=$(echo $DATABASE_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
DB_PASSWORD=$(echo $DATABASE_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')

echo "Database Connection Details:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

# Test 1: Check PostgreSQL is running
echo "Test 1: PostgreSQL Service"
if systemctl is-active --quiet postgresql; then
    print_success "PostgreSQL service is running"
else
    if [ "$DB_HOST" != "localhost" ]; then
        print_warning "PostgreSQL service check skipped (remote host: $DB_HOST)"
    else
        print_error "PostgreSQL service is not running"
        exit 1
    fi
fi

# Test 2: Check database connection
echo ""
echo "Test 2: Database Connection"
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &> /dev/null; then
    print_success "Successfully connected to database"
else
    print_error "Failed to connect to database"
    echo "Check your DATABASE_URL in .env file"
    exit 1
fi

# Test 3: Check required tables exist
echo ""
echo "Test 3: Required Tables"
REQUIRED_TABLES=("agent_interactions" "agent_prompts" "trade_outcomes" "strategy_adjustments" "agent_daily_metrics" "trade_metadata")
MISSING_TABLES=()

for table in "${REQUIRED_TABLES[@]}"; do
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='$table';" | grep -q 1; then
        print_success "Table '$table' exists"
    else
        print_error "Table '$table' is missing"
        MISSING_TABLES+=("$table")
    fi
done

if [ ${#MISSING_TABLES[@]} -gt 0 ]; then
    echo ""
    print_error "Missing ${#MISSING_TABLES[@]} required table(s)"
    echo "Run database migrations to create missing tables:"
    echo "  alembic upgrade head"
    exit 1
fi

# Test 4: Check Alembic version
echo ""
echo "Test 4: Database Migrations"
ALEMBIC_VERSION=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT version_num FROM alembic_version;" 2>/dev/null || echo "")

if [ -n "$ALEMBIC_VERSION" ]; then
    print_success "Alembic migrations applied (version: $ALEMBIC_VERSION)"
else
    print_warning "Alembic version table not found"
    echo "This might be expected if migrations haven't been run yet"
fi

# Test 5: Check table row counts
echo ""
echo "Test 5: Table Statistics"
for table in "${REQUIRED_TABLES[@]}"; do
    ROW_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "0")
    echo "  $table: $ROW_COUNT rows"
done

# Test 6: Check database permissions
echo ""
echo "Test 6: Database Permissions"
CAN_INSERT=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT has_table_privilege('$DB_USER', 'agent_interactions', 'INSERT');" 2>/dev/null || echo "f")

if [ "$CAN_INSERT" = "t" ]; then
    print_success "User has INSERT permissions"
else
    print_error "User lacks INSERT permissions"
    echo "Grant permissions with:"
    echo "  sudo -u postgres psql -d $DB_NAME -c 'GRANT ALL ON SCHEMA public TO $DB_USER;'"
    exit 1
fi

# Test 7: Check PostgreSQL version
echo ""
echo "Test 7: PostgreSQL Version"
PG_VERSION=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT version();" | cut -d' ' -f2)
print_success "PostgreSQL $PG_VERSION"

# Test 8: Check disk space usage
echo ""
echo "Test 8: Database Size"
DB_SIZE=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));" 2>/dev/null || echo "unknown")
echo "  Database size: $DB_SIZE"

# Test 9: Test write operations
echo ""
echo "Test 9: Write Operations"
TEST_UUID=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid)
INSERT_TEST=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "
    INSERT INTO agent_interactions (
        id, agent_name, action, context, result, tokens_used, cost_usd, latency_ms, created_at
    ) VALUES (
        '$TEST_UUID', 'test_agent', 'test_action', '{\"test\": true}', '{\"success\": true}', 100, 0.001, 50, NOW()
    ) RETURNING id;
" 2>/dev/null || echo "")

if [ -n "$INSERT_TEST" ]; then
    print_success "Successfully inserted test record"

    # Clean up test record
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "DELETE FROM agent_interactions WHERE id='$TEST_UUID';" &> /dev/null
    print_success "Successfully deleted test record"
else
    print_error "Failed to insert test record"
    exit 1
fi

# Summary
echo ""
echo "=================================================="
echo "Verification Summary"
echo "=================================================="
echo ""
print_success "All tests passed! Database is ready for use."
echo ""
echo "Next steps:"
echo "  1. Enable multi-agent system: MULTI_AGENT_ENABLED=true in .env"
echo "  2. Test multi-agent workflow: python -m trading_bot.llm.examples.multi_agent_consensus_workflow"
echo "  3. Start trading bot with multi-agent mode enabled"
echo ""
echo "Monitor database with:"
echo "  psql $DATABASE_URL"
echo ""
