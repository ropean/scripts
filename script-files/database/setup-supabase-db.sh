#!/bin/bash
# @title Supabase PostgreSQL Database & User Setup
# @description Interactive script to create a dedicated database and user with full privileges in Supabase PostgreSQL
# @author Wei
# @version 1.1.0
#
# This script creates a project-specific database and user account with complete
# privileges in a Dockerized Supabase PostgreSQL instance. It handles existing
# databases/users gracefully and provides detailed feedback throughout the process.
#
# Features:
# - Two-phase setup: admin connection validation, then database/user creation
# - Checks for existing databases and users before creation
# - PostgreSQL 15+ compatible: properly handles new public schema ownership model
# - Transfers database ownership to user for full public schema access
# - Grants comprehensive permissions with explicit error checking
# - Provides connection strings and detailed permission summary
#
# @example
# Usage:
#   chmod +x setup-supabase-db.sh
#   ./setup-supabase-db.sh
#
# @requires docker, bash 4.0+
# @see https://scripts.aceapp.dev/database/setup-supabase-db

# Color definitions
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🐘 Supabase PostgreSQL Setup Tool${NC}"
echo -e "${BLUE}   (PostgreSQL 15+ Compatible)${NC}"
echo -e "${BLUE}========================================${NC}\n"

# ===== Phase 1: Admin Account Connection =====
echo -e "${CYAN}📋 Phase 1: PostgreSQL Admin Connection${NC}\n"

read -p "Container name [supabase_db_supabase-svc]: " CONTAINER_NAME
CONTAINER_NAME=${CONTAINER_NAME:-supabase_db_supabase-svc}

read -p "Host [127.0.0.1]: " DB_HOST
DB_HOST=${DB_HOST:-127.0.0.1}

read -p "Port [54322]: " DB_PORT
DB_PORT=${DB_PORT:-54322}

read -p "Admin username [postgres]: " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-postgres}

read -p "Admin password [postgres]: " ADMIN_PASSWORD
ADMIN_PASSWORD=${ADMIN_PASSWORD:-postgres}
echo

# Verify container is running
echo -e "${YELLOW}🔍 Checking container status...${NC}"
if ! docker ps | grep -q "$CONTAINER_NAME"; then
  echo -e "${RED}✗ Error: Container '$CONTAINER_NAME' is not running${NC}"
  echo -e "${YELLOW}💡 Tip: Use 'docker ps' to view running containers${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Container is running${NC}\n"

# Test database connection
echo -e "${YELLOW}🔌 Testing database connection...${NC}"
if ! docker exec $CONTAINER_NAME psql -U $ADMIN_USER -c "SELECT 1;" >/dev/null 2>&1; then
  echo -e "${RED}✗ Connection failed, please check admin credentials${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Connection successful${NC}\n"

# ===== Phase 2: Create Project-Specific Account =====
echo -e "${CYAN}📋 Phase 2: Create Project Database & User${NC}\n"

read -p "Database name: " DB_NAME
if [ -z "$DB_NAME" ]; then
  echo -e "${RED}✗ Database name cannot be empty${NC}"
  exit 1
fi

read -p "Username: " DB_USER
if [ -z "$DB_USER" ]; then
  echo -e "${RED}✗ Username cannot be empty${NC}"
  exit 1
fi

read -p "Password: " DB_PASSWORD
if [ -z "$DB_PASSWORD" ]; then
  echo -e "${RED}✗ Password cannot be empty${NC}"
  exit 1
fi

# ===== Execute Database & User Creation =====
echo -e "\n${YELLOW}🚀 Creating database and user...${NC}\n"

# Check if database exists
DB_EXISTS=$(docker exec $CONTAINER_NAME psql -U $ADMIN_USER -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';")

if [ "$DB_EXISTS" = "1" ]; then
  echo -e "${YELLOW}ℹ️  Database '$DB_NAME' already exists${NC}"
else
  docker exec $CONTAINER_NAME psql -U $ADMIN_USER -c "CREATE DATABASE $DB_NAME;"
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database '$DB_NAME' created${NC}"
  else
    echo -e "${RED}✗ Failed to create database${NC}"
    exit 1
  fi
fi

# Check if user exists
USER_EXISTS=$(docker exec $CONTAINER_NAME psql -U $ADMIN_USER -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER';")

if [ "$USER_EXISTS" = "1" ]; then
  echo -e "${YELLOW}ℹ️  User '$DB_USER' already exists${NC}"
  # Update password for existing user
  docker exec $CONTAINER_NAME psql -U $ADMIN_USER -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
  echo -e "${GREEN}✓ Password updated for user '$DB_USER'${NC}"
else
  docker exec $CONTAINER_NAME psql -U $ADMIN_USER -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ User '$DB_USER' created${NC}"
  else
    echo -e "${RED}✗ Failed to create user${NC}"
    exit 1
  fi
fi

# Grant privileges
echo -e "${YELLOW}🔐 Granting privileges...${NC}"

# ===== IMPORTANT: PostgreSQL 15+ Schema Ownership Model =====
# In PostgreSQL 15 and later, the 'public' schema is owned by the predefined
# role 'pg_database_owner', which represents the owner of the database.
# To grant full access to the public schema, the user must become the database owner.
#
# Step 1: Grant role membership to allow admin to transfer ownership
# This is required because ALTER DATABASE ... OWNER requires the ability to SET ROLE
echo -e "${YELLOW}  → Preparing role membership for ownership transfer...${NC}"
docker exec $CONTAINER_NAME psql -U $ADMIN_USER -c "GRANT $DB_USER TO $ADMIN_USER;" 2>&1 | grep -v "^GRANT ROLE$" || true

# Step 2: Grant basic privileges and user attributes
echo -e "${YELLOW}  → Granting database privileges and user attributes...${NC}"
docker exec $CONTAINER_NAME psql -U $ADMIN_USER <<EOF
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER USER $DB_USER CREATEDB;
ALTER USER $DB_USER CREATEROLE;
EOF

if [ $? -ne 0 ]; then
  echo -e "${RED}✗ Failed to grant basic privileges${NC}"
  exit 1
fi

# Step 3: Transfer database ownership
# This is CRITICAL for PostgreSQL 15+ as it gives the user automatic access to
# the 'public' schema through the 'pg_database_owner' role
echo -e "${YELLOW}  → Transferring database ownership to $DB_USER...${NC}"
docker exec $CONTAINER_NAME psql -U $ADMIN_USER -c "ALTER DATABASE $DB_NAME OWNER TO $DB_USER;"

if [ $? -ne 0 ]; then
  echo -e "${RED}✗ Failed to transfer database ownership${NC}"
  exit 1
fi

# Step 4: Grant explicit schema permissions
# While the user now owns the database (and thus has access to public schema),
# we explicitly grant permissions for clarity and compatibility
echo -e "${YELLOW}  → Setting schema permissions...${NC}"
docker exec $CONTAINER_NAME psql -U $ADMIN_USER -d $DB_NAME <<EOF
-- Grant usage and creation rights on public schema
GRANT CREATE ON SCHEMA public TO $DB_USER;
GRANT USAGE ON SCHEMA public TO $DB_USER;

-- Grant all privileges on existing objects
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO $DB_USER;

-- Set default privileges for future objects created by postgres role
ALTER DEFAULT PRIVILEGES FOR ROLE $ADMIN_USER IN SCHEMA public
  GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES FOR ROLE $ADMIN_USER IN SCHEMA public
  GRANT ALL ON SEQUENCES TO $DB_USER;
ALTER DEFAULT PRIVILEGES FOR ROLE $ADMIN_USER IN SCHEMA public
  GRANT ALL ON FUNCTIONS TO $DB_USER;

-- Set default privileges for future objects created by the user itself
ALTER DEFAULT PRIVILEGES FOR ROLE $DB_USER IN SCHEMA public
  GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES FOR ROLE $DB_USER IN SCHEMA public
  GRANT ALL ON SEQUENCES TO $DB_USER;
ALTER DEFAULT PRIVILEGES FOR ROLE $DB_USER IN SCHEMA public
  GRANT ALL ON FUNCTIONS TO $DB_USER;
EOF

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ All privileges granted${NC}\n"

  echo -e "${GREEN}========================================${NC}"
  echo -e "${GREEN}✅ Setup completed successfully!${NC}"
  echo -e "${GREEN}========================================${NC}\n"

  echo -e "${BLUE}📝 Connection Information:${NC}"
  echo -e "  Database: ${GREEN}$DB_NAME${NC}"
  echo -e "  Username: ${GREEN}$DB_USER${NC}"
  echo -e "  Password: ${GREEN}$DB_PASSWORD${NC}"
  echo -e "  Host:     ${GREEN}$DB_HOST${NC}"
  echo -e "  Port:     ${GREEN}$DB_PORT${NC}\n"

  echo -e "${BLUE}🔗 Connection String:${NC}"
  echo -e "  ${GREEN}postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME${NC}\n"

  echo -e "${BLUE}🔑 Granted Permissions:${NC}"
  echo -e "  ✓ Database owner (provides full access to public schema)"
  echo -e "  ✓ CREATE DATABASE privilege"
  echo -e "  ✓ CREATE ROLE privilege"
  echo -e "  ✓ Full control over public schema"
  echo -e "  ✓ Full control over all tables, sequences, and functions"
  echo -e "  ✓ Default privileges for future objects\n"

  echo -e "${CYAN}📚 Note: PostgreSQL 15+ Schema Ownership${NC}"
  echo -e "  In PostgreSQL 15+, the 'public' schema is owned by 'pg_database_owner'."
  echo -e "  User '$DB_USER' has been made the database owner, which automatically"
  echo -e "  grants full access to the public schema. This ensures compatibility"
  echo -e "  with modern ORMs like Prisma.\n"
else
  echo -e "\n${RED}========================================${NC}"
  echo -e "${RED}✗ Setup failed, please check error messages above${NC}"
  echo -e "${RED}========================================${NC}"
  exit 1
fi
