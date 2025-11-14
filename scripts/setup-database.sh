#!/bin/bash
# Setup script for trading bot database on existing PostgreSQL instance
# Run this on your VPS: bash scripts/setup-database.sh

set -e  # Exit on error

echo "=================================================="
echo "Trading Bot Database Setup"
echo "=================================================="
echo ""

# Configuration
DB_NAME="trading_bot"
DB_USER="trading_bot"
DB_PASSWORD="${POSTGRES_PASSWORD:-change_me_in_production}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if PostgreSQL is running
echo "Checking PostgreSQL status..."
if systemctl is-active --quiet postgresql; then
    print_success "PostgreSQL is running"
else
    print_error "PostgreSQL is not running"
    echo "Start PostgreSQL with: sudo systemctl start postgresql"
    exit 1
fi

# Check if database already exists
echo ""
echo "Checking if database already exists..."
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    print_warning "Database '$DB_NAME' already exists"
    echo "Do you want to drop and recreate it? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "Dropping database '$DB_NAME'..."
        sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;"
        print_success "Database dropped"
    else
        echo "Skipping database creation"
        DB_EXISTS=true
    fi
fi

# Create database if it doesn't exist
if [ "$DB_EXISTS" != "true" ]; then
    echo ""
    echo "Creating database '$DB_NAME'..."
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"
    print_success "Database created"
fi

# Check if user already exists
echo ""
echo "Checking if user already exists..."
if sudo -u postgres psql -t -c "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
    print_warning "User '$DB_USER' already exists"
    echo "Do you want to update the password? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "Enter new password for user '$DB_USER' (leave empty to use default from .env):"
        read -rs NEW_PASSWORD
        if [ -n "$NEW_PASSWORD" ]; then
            DB_PASSWORD="$NEW_PASSWORD"
        fi
        sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
        print_success "Password updated"
    fi
else
    echo ""
    echo "Creating user '$DB_USER'..."
    echo "Enter password for user '$DB_USER' (leave empty to use default from .env):"
    read -rs NEW_PASSWORD
    if [ -n "$NEW_PASSWORD" ]; then
        DB_PASSWORD="$NEW_PASSWORD"
    fi
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    print_success "User created"
fi

# Grant privileges
echo ""
echo "Granting privileges..."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO $DB_USER;"
print_success "Privileges granted"

# Display database info
echo ""
echo "=================================================="
echo "Database Setup Complete"
echo "=================================================="
echo ""
echo "Database Connection Details:"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Password: [hidden - saved in .env]"
echo ""
echo "Add this to your .env file:"
echo ""
echo "DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
echo ""
echo "=================================================="
echo ""

# Check if we're in the trading bot directory
if [ -f "alembic.ini" ]; then
    echo "Alembic configuration found. Do you want to run migrations now? (Y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Nn]$ ]]; then
        echo ""
        echo "Running database migrations..."

        # Set DATABASE_URL for migrations
        export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"

        # Check if alembic command exists
        if command -v alembic &> /dev/null; then
            alembic upgrade head
            print_success "Migrations completed"

            # Show created tables
            echo ""
            echo "Created tables:"
            sudo -u postgres psql -d "$DB_NAME" -c "\dt"
        else
            print_warning "Alembic not found. Install with: pip install alembic"
            echo "Then run migrations manually with: alembic upgrade head"
        fi
    fi
else
    print_warning "Not in trading bot directory. Run migrations manually:"
    echo "  1. cd /path/to/trading-bot"
    echo "  2. export DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
    echo "  3. alembic upgrade head"
fi

echo ""
echo "=================================================="
echo "Next Steps:"
echo "=================================================="
echo ""
echo "1. Update .env file with DATABASE_URL"
echo "2. Run migrations: alembic upgrade head"
echo "3. Test connection: psql -d $DB_NAME -U $DB_USER"
echo "4. Start trading bot with multi-agent system enabled"
echo ""
print_success "Setup complete!"
