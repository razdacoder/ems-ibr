#!/bin/bash

# Fix Docker credential storage issue on Linux
# This script removes the credential store configuration that causes "pass not initialized" error

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo ""
print_warning "Docker Credential Storage Fix"
echo ""
print_info "This script fixes the 'pass not initialized' error when using docker login"
echo ""

# Check if config exists
if [ ! -f ~/.docker/config.json ]; then
    print_info "Creating Docker config directory..."
    mkdir -p ~/.docker
    echo '{}' > ~/.docker/config.json
    print_info "✅ Docker config created"
    exit 0
fi

# Backup existing config
print_info "Backing up current config..."
cp ~/.docker/config.json ~/.docker/config.json.backup.$(date +%Y%m%d_%H%M%S)

# Check if credsStore exists
if grep -q '"credsStore"' ~/.docker/config.json; then
    print_warning "Found 'credsStore' configuration that may cause issues"
    print_info "Removing 'credsStore' from config..."
    
    # Remove credsStore line
    sed -i '/"credsStore"/d' ~/.docker/config.json
    
    # Also remove credHelpers if present
    if grep -q '"credHelpers"' ~/.docker/config.json; then
        print_info "Removing 'credHelpers' from config..."
        sed -i '/"credHelpers"/d' ~/.docker/config.json
    fi
    
    print_info "✅ Fixed! Docker will now store credentials in ~/.docker/config.json"
    echo ""
    print_warning "⚠️  Note: Credentials will be stored in plain text (base64 encoded)"
    print_info "This is less secure but necessary if you don't have 'pass' configured"
    echo ""
    print_info "To use 'pass' instead (more secure):"
    echo "  1. Install pass: sudo apt install pass gnupg"
    echo "  2. Generate GPG key: gpg --generate-key"
    echo "  3. Initialize pass: pass init <your-gpg-key-id>"
    echo "  4. Revert this fix by restoring the backup"
    echo ""
else
    print_info "✅ No problematic credential store configuration found"
    print_info "Your Docker config is already using file-based storage"
fi

echo ""
print_info "You can now run docker login successfully!"
print_info "Try: docker login"
echo ""
