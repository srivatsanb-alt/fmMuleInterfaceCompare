#!/bin/bash

# Script to push deployment manager docker image to remote server
# Usage: ./push_dm_image_to_remote_server.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Function to check if required variables are set
check_required_vars() {
    if [[ -z "$DM_VERSION" ]]; then
        print_error "DM_VERSION is not set. Please run pull_dm_image.sh first."
        exit 1
    fi
    
    if [[ -z "$remote_server_addr" ]]; then
        print_error "remote_server_addr is not set."
        exit 1
    fi
}

# Function to check if DM image exists locally
check_dm_image_exists() {
    print_status "Checking if deployment manager image exists locally..."
    
    if ! docker image inspect "deployment_manager:$DM_VERSION" &>/dev/null; then
        print_error "Deployment manager image 'deployment_manager:$DM_VERSION' not found locally!"
        print_error "Please run pull_dm_image.sh first to pull the image from ECR."
        exit 1
    fi
    
    print_status "✓ Deployment manager image found locally"
}

# Function to get image size
get_image_size() {
    local image_name="deployment_manager:$DM_VERSION"
    local size_bytes=$(docker image inspect "$image_name" --format='{{.Size}}')
    local size_mb=$((size_bytes / 1024 / 1024))
    echo "${size_mb}MB"
}

# Function to save DM image locally
save_dm_image() {
    print_status "Step 1/3: Saving deployment manager image locally..."
    print_status "⏳ Creating tarball..."
    
    local temp_file="/tmp/dm_$DM_VERSION.tar"
    
    if docker save "deployment_manager:$DM_VERSION" > "$temp_file"; then
        local actual_size=$(du -h "$temp_file" | cut -f1)
        print_status "✅ Saved DM image: $actual_size"
        echo "$temp_file"
    else
        print_error "❌ Failed to save DM image"
        exit 1
    fi
}

# Function to transfer image to remote server
transfer_to_remote() {
    local temp_file="$1"
    
    print_status "Step 2/3: Transferring image to remote server..."
    print_status "🌐 Uploading to $remote_server_addr..."
    
    # Try different methods for progress indication
    if command -v pv &> /dev/null; then
        print_status "📊 Using pv for transfer progress..."
        if pv "$temp_file" | ssh "$remote_server_addr" "cat > /tmp/dm_$DM_VERSION.tar"; then
            print_status "✅ Transfer completed with progress bar"
        else
            print_error "❌ Transfer failed"
            return 1
        fi
    elif command -v rsync &> /dev/null; then
        print_status "📊 Using rsync for transfer progress..."
        if rsync -avz --progress "$temp_file" "$remote_server_addr:/tmp/"; then
            print_status "✅ Transfer completed with progress"
        else
            print_error "❌ Transfer failed"
            return 1
        fi
    else
        print_warning "📤 Using scp for transfer (install 'pv' or 'rsync' for progress bar)..."
        if scp "$temp_file" "$remote_server_addr:/tmp/"; then
            print_status "✅ Transfer completed"
        else
            print_error "❌ Transfer failed"
            return 1
        fi
    fi
}

# Function to load image on remote server
load_on_remote() {
    print_status "Step 3/3: Loading image on remote server..."
    print_status "🐳 Loading Docker image..."
    
    if ssh "$remote_server_addr" "docker load -i /tmp/dm_$DM_VERSION.tar && rm /tmp/dm_$DM_VERSION.tar"; then
        print_status "✅ Image loaded on remote server"
    else
        print_error "❌ Failed to load image on remote server"
        return 1
    fi
}

# Function to cleanup local files
cleanup_local() {
    local temp_file="$1"
    
    if [[ -f "$temp_file" ]]; then
        rm -f "$temp_file"
        print_status "✅ Cleanup completed"
    fi
}

# Function to display summary
display_summary() {
    local image_size="$1"
    
    print_header "Transfer Summary"
    print_status "🎉 Deployment manager image transferred successfully!"
    echo
    print_status "📋 Summary:"
    echo "   • Image: deployment_manager:$DM_VERSION"
    echo "   • Size: $image_size"
    echo "   • Destination: $remote_server_addr"
    echo "   • Status: Ready for deployment"
    echo
}

# Main execution
main() {
    print_header "Deployment Manager Remote Server Push Script"
    
    # Check required variables
    check_required_vars
    
    # Check if DM image exists locally
    check_dm_image_exists
    
    # Get image size for display
    local image_size=$(get_image_size)
    
    print_status "🚀 Transferring deployment manager image to remote server..."
    print_status "📦 DM Image Size: $image_size - This may take a few minutes depending on connection speed"
    echo
    
    # Step 1: Save DM image locally
    local temp_file=$(save_dm_image)
    echo
    
    # Step 2: Transfer to remote server
    if ! transfer_to_remote "$temp_file"; then
        cleanup_local "$temp_file"
        exit 1
    fi
    echo
    
    # Step 3: Load on remote server
    if ! load_on_remote; then
        cleanup_local "$temp_file"
        exit 1
    fi
    echo
    
    # Cleanup local files
    cleanup_local "$temp_file"
    
    # Display summary
    display_summary "$image_size"
}

# Run main function
main "$@"
