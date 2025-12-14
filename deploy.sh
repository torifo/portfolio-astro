#!/bin/bash

# Portfolio Deployment Script with Version Management
# Usage: ./deploy.sh [version]
# Example: ./deploy.sh 20251215-0028  (deploys specific version)
#          ./deploy.sh                 (deploys latest)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default version
VERSION="${1:-latest}"

echo -e "${GREEN}=== Portfolio Deployment Script ===${NC}"
echo -e "Target version: ${YELLOW}${VERSION}${NC}"
echo ""

# Step 1: Pull the specified version
echo -e "${GREEN}Step 1: Pulling container image${NC}"
IMAGE_TAG=${VERSION} docker compose pull
echo -e "✓ Image pulled successfully"
echo ""

# Step 2: Stop current container
echo -e "${GREEN}Step 2: Stopping current container${NC}"
docker compose down
echo -e "✓ Container stopped"
echo ""

# Step 3: Start new container
echo -e "${GREEN}Step 3: Starting new container with version ${VERSION}${NC}"
IMAGE_TAG=${VERSION} docker compose up -d
echo -e "✓ Container started"
echo ""

# Step 4: Verify deployment
echo -e "${GREEN}Step 4: Verifying deployment${NC}"
sleep 3
if docker compose ps | grep -q "portfolio-frontend.*Up"; then
    echo -e "${GREEN}✓ Deployment successful!${NC}"
    echo ""
    echo -e "Container details:"
    docker compose ps
    echo ""
    echo -e "Recent logs:"
    docker compose logs --tail=20 portfolio-frontend
else
    echo -e "${RED}✗ Deployment failed. Check logs:${NC}"
    docker compose logs portfolio-frontend
    exit 1
fi

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo -e "Website: ${YELLOW}https://portorifo.riumu.net${NC}"
echo -e "Version: ${YELLOW}${VERSION}${NC}"
echo ""
echo -e "Current running image:"
docker inspect portfolio-frontend --format='{{.Config.Image}}'
