#!/bin/bash

# Docker Build and Push Script for EMS-IBR
# This script builds and pushes the Docker image to a registry

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGISTRY_TYPE=""
IMAGE_NAME=""
VERSION="latest"

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Build and push Docker image for EMS-IBR to a container registry.

OPTIONS:
    -r, --registry TYPE     Registry type: dockerhub, ghcr (required)
    -u, --username USER     Your registry username (required)
    -v, --version VERSION   Image version tag (default: latest)
    -h, --help              Show this help message

EXAMPLES:
    # Docker Hub
    $0 --registry dockerhub --username johndoe --version v1.0.0

    # GitHub Container Registry
    $0 --registry ghcr --username johndoe --version latest

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--registry)
            REGISTRY_TYPE="$2"
            shift 2
            ;;
        -u|--username)
            USERNAME="$2"
            shift 2
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate inputs
if [ -z "$REGISTRY_TYPE" ] || [ -z "$USERNAME" ]; then
    print_error "Registry type and username are required"
    show_usage
    exit 1
fi

# Set image name based on registry type
case $REGISTRY_TYPE in
    dockerhub)
        IMAGE_NAME="${USERNAME}/ems-ibr:${VERSION}"
        REGISTRY_URL=""
        print_info "Using Docker Hub registry"
        ;;
    ghcr)
        IMAGE_NAME="ghcr.io/${USERNAME}/ems-ibr:${VERSION}"
        REGISTRY_URL="ghcr.io"
        print_info "Using GitHub Container Registry"
        ;;
    *)
        print_error "Invalid registry type. Use 'dockerhub' or 'ghcr'"
        exit 1
        ;;
esac

print_info "Image will be tagged as: ${IMAGE_NAME}"

# Check and fix Docker credential store issue
print_info "Checking Docker credential configuration..."
if [ -f ~/.docker/config.json ]; then
    if grep -q '"credsStore"' ~/.docker/config.json; then
        print_warning "Docker is configured to use a credential store that may not be initialized"
        print_info "Temporarily disabling credential store for this login..."
        
        # Backup original config
        cp ~/.docker/config.json ~/.docker/config.json.backup
        
        # Remove credsStore from config to use file-based storage
        sed -i '/"credsStore"/d' ~/.docker/config.json
        
        print_info "Original config backed up to ~/.docker/config.json.backup"
        print_info "Credentials will be stored in ~/.docker/config.json (less secure but works)"
    fi
fi

# Login to registry
print_info "Logging in to registry..."
if [ "$REGISTRY_TYPE" = "dockerhub" ]; then
    docker login
elif [ "$REGISTRY_TYPE" = "ghcr" ]; then
    echo ""
    print_warning "For GHCR, you need a Personal Access Token with 'write:packages' scope"
    print_info "Generate one at: https://github.com/settings/tokens"
    echo ""
    docker login ghcr.io -u "$USERNAME"
fi

if [ $? -ne 0 ]; then
    print_error "Failed to login to registry"
    print_error "If you get 'pass not initialized' error, run: ./fix-docker-credentials.sh"
    exit 1
fi

print_info "Login successful!"

# Build the Docker image
print_info "Building Docker image..."
docker build -t "$IMAGE_NAME" .

if [ $? -ne 0 ]; then
    print_error "Failed to build Docker image"
    exit 1
fi

print_info "Build completed successfully!"

# Also tag as latest if building a version
if [ "$VERSION" != "latest" ]; then
    if [ "$REGISTRY_TYPE" = "dockerhub" ]; then
        LATEST_TAG="${USERNAME}/ems-ibr:latest"
    else
        LATEST_TAG="ghcr.io/${USERNAME}/ems-ibr:latest"
    fi
    print_info "Tagging as latest: ${LATEST_TAG}"
    docker tag "$IMAGE_NAME" "$LATEST_TAG"
fi

# Push to registry
print_info "Pushing image to registry..."
docker push "$IMAGE_NAME"

if [ $? -ne 0 ]; then
    print_error "Failed to push Docker image"
    exit 1
fi

# Push latest tag if exists
if [ "$VERSION" != "latest" ]; then
    print_info "Pushing latest tag..."
    docker push "$LATEST_TAG"
fi

print_info "✅ Successfully pushed Docker image!"
echo ""
print_info "Image URL: ${IMAGE_NAME}"
echo ""
print_info "To deploy on Railway:"
print_info "1. Go to your Railway project"
print_info "2. Create/update service"
print_info "3. Select 'Docker Image' as source"
print_info "4. Enter image: ${IMAGE_NAME}"
print_info "5. Configure environment variables"
print_info "6. Deploy!"
echo ""
