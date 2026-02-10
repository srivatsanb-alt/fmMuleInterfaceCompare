#!/bin/bash

# Custom MongoDB Entrypoint Script
# This script creates a secure replication key before starting MongoDB

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Validating environment variables...${NC}"

# Validate required environment variables
if [[ -z "$MONGO_INITDB_ROOT_PASSWORD" ]]; then
    echo -e "${RED}Error: MONGO_INITDB_ROOT_PASSWORD is not set${NC}"
    exit 1
fi

if [[ -z "$MONGO_INITDB_ROOT_USERNAME" ]]; then
    echo -e "${RED}Error: MONGO_INITDB_ROOT_USERNAME is not set${NC}"
    exit 1
fi

echo -e "${GREEN}Environment variables validated!${NC}"

# Check if keyfile already exists in persistent volume first
if [ -f "/data/db/mongodb-keyfile" ]; then
    echo -e "${GREEN}MongoDB replication keyfile found in persistent volume, copying to /etc/mongodb-keyfile${NC}"
    cp /data/db/mongodb-keyfile /etc/mongodb-keyfile
    # Set proper permissions and ownership
    MONGO_USER_ID=$(id -u mongodb 2>/dev/null || echo "999")
    MONGO_GROUP_ID=$(id -g mongodb 2>/dev/null || echo "999")
    chmod 400 /etc/mongodb-keyfile
    chown ${MONGO_USER_ID}:${MONGO_GROUP_ID} /etc/mongodb-keyfile
    echo -e "${YELLOW}Key file permissions: $(ls -la /etc/mongodb-keyfile)${NC}"
elif [ -f "/etc/mongodb-keyfile" ]; then
    echo -e "${GREEN}MongoDB replication keyfile already exists, using existing keyfile${NC}"
    echo -e "${YELLOW}Key file permissions: $(ls -la /etc/mongodb-keyfile)${NC}"
else
    echo -e "${YELLOW}Creating secure MongoDB replication key...${NC}"

    # Create a secure replication key (not the root password)
    # This should be at least 756 characters and contain only base64 characters
    openssl rand -base64 756 > /etc/mongodb-keyfile

    # Get the MongoDB user/group IDs dynamically instead of hardcoding
    MONGO_USER_ID=$(id -u mongodb 2>/dev/null || echo "999")
    MONGO_GROUP_ID=$(id -g mongodb 2>/dev/null || echo "999")

    # Set proper permissions and ownership
    chmod 400 /etc/mongodb-keyfile
    chown ${MONGO_USER_ID}:${MONGO_GROUP_ID} /etc/mongodb-keyfile

    # Copy to persistent volume for future use
    cp /etc/mongodb-keyfile /data/db/mongodb-keyfile
    chmod 400 /data/db/mongodb-keyfile
    chown ${MONGO_USER_ID}:${MONGO_GROUP_ID} /data/db/mongodb-keyfile

    echo -e "${GREEN}Secure replication key created successfully!${NC}"
    echo -e "${YELLOW}Key file permissions: $(ls -la /etc/mongodb-keyfile)${NC}"
    echo -e "${YELLOW}Key file saved to persistent volume: /data/db/mongodb-keyfile${NC}"
fi

# Call the official MongoDB entrypoint with all arguments
echo -e "${YELLOW}Starting MongoDB with official entrypoint...${NC}"
exec /usr/local/bin/docker-entrypoint.sh "$@"
