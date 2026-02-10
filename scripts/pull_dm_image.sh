#!/bin/bash

# Script to pull deployment manager docker image from AWS ECR
# Usage: ./pull_dm_image.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ECR repository details
ECR_REGION="ap-south-1" 
ECR_REPO_NAME="dm/deployment_manager"
ECR_ACCOUNT_ID="131891766286"

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

# Function to validate input parameters
validate_aws_credentials() {
    if [[ -z "$1" ]]; then
        print_error "AWS Access Key ID cannot be empty"
        return 1
    fi
    
    if [[ -z "$2" ]]; then
        print_error "AWS Secret Access Key cannot be empty"
        return 1
    fi
    
    return 0
}

# Function to validate version input
validate_version() {
    if [[ -z "$1" ]]; then
        print_error "Docker image version cannot be empty"
        return 1
    fi
    
    return 0
}

# Function to check if AWS CLI is installed
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        print_status "Installation guide: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        exit 1
    fi
    print_status "AWS CLI is installed"
}

# Function to check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install it first."
        exit 1
    fi
    print_status "Docker is installed"
}

# Function to check if jq is installed
check_jq() {
    if ! command -v jq &> /dev/null; then
        print_error "jq is not installed. Please install it first."
        print_status "Installation: sudo apt-get install jq (Ubuntu/Debian) or brew install jq (macOS)"
        exit 1
    fi
    print_status "jq is installed"
}

# Function to cleanup authentication data
cleanup_auth() {
    print_status "Cleaning up authentication data..."
    
    # Logout from ECR
    if [[ -n "$ECR_ACCOUNT_ID" && -n "$ECR_REGION" ]]; then
        docker logout "$ECR_ACCOUNT_ID.dkr.ecr.$ECR_REGION.amazonaws.com" 2>/dev/null || true
    fi
    
    # Remove temporary docker config
    if [[ -n "$DOCKER_CONFIG" && -d "$DOCKER_CONFIG" ]]; then
        rm -rf "$DOCKER_CONFIG"
        print_status "Temporary Docker config cleaned up"
    fi
    
    # Unset AWS credentials from environment
    unset AWS_ACCESS_KEY_ID
    unset AWS_SECRET_ACCESS_KEY
    unset AWS_DEFAULT_REGION
}

# Function to setup docker authentication environment
setup_docker_auth() {
    # Clean up any existing temporary docker config
    if [[ -n "$DOCKER_CONFIG" && -d "$DOCKER_CONFIG" ]]; then
        rm -rf "$DOCKER_CONFIG"
    fi
    
    # Create fresh temporary docker config directory to avoid credential helper issues
    export DOCKER_CONFIG=$(mktemp -d)
    
    # Create a minimal docker config without credential helpers and empty auths
    cat > "$DOCKER_CONFIG/config.json" << 'INNER_EOF'
{
    "auths": {},
    "HttpHeaders": {
        "User-Agent": "Docker-Client/20.10.0 (linux)"
    }
}
INNER_EOF
    
    print_status "Fresh Docker authentication environment configured (no cached credentials)"
}

# Function to get AWS credentials from user
get_aws_credentials() {
    print_header "AWS Credentials Setup"
    print_status "Please provide your AWS credentials to access ECR repository"
    print_warning "These credentials will be used temporarily and cleared after the script completes"
    
    echo
    echo -n "Enter AWS Access Key ID: "
    read -r AWS_ACCESS_KEY_ID_INPUT
    
    echo -n "Enter AWS Secret Access Key: "
    read -rs AWS_SECRET_ACCESS_KEY_INPUT
    echo  # New line after password input
    
    # Validate credentials input
    if ! validate_aws_credentials "$AWS_ACCESS_KEY_ID_INPUT" "$AWS_SECRET_ACCESS_KEY_INPUT"; then
        exit 1
    fi
    
    # Set AWS credentials as environment variables for this session
    export AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID_INPUT"
    export AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY_INPUT"
    export AWS_DEFAULT_REGION="$ECR_REGION"
    
    # Clear the input variables for security
    unset AWS_ACCESS_KEY_ID_INPUT
    unset AWS_SECRET_ACCESS_KEY_INPUT
    
    print_status "AWS credentials configured for this session"
    
    # Test the credentials by trying to list ECR repositories
    if ! aws ecr describe-repositories --region "$ECR_REGION" &>/dev/null; then
        print_error "AWS credentials authentication failed!"
        print_error "Please check your credentials and try again."
        exit 1
    fi
    
    print_status "AWS credentials are valid and working"
}

# Function to authenticate with ECR using AWS CLI
authenticate_ecr() {
    print_status "Authenticating with ECR using provided AWS credentials..."
    
    # Clear any existing auth for this registry before attempting new login
    docker logout "$ECR_ACCOUNT_ID.dkr.ecr.$ECR_REGION.amazonaws.com" 2>/dev/null || true
    
    # Use AWS CLI to get ECR login token and authenticate with Docker
    aws ecr get-login-password --region "$ECR_REGION" | \
        docker login --username AWS --password-stdin "$ECR_ACCOUNT_ID.dkr.ecr.$ECR_REGION.amazonaws.com" || {
        print_error "Failed to authenticate with ECR. Please check your AWS credentials."
        print_error "Make sure your AWS credentials have the necessary permissions to access ECR."
        exit 1
    }
    
    print_status "Successfully authenticated with ECR"
}

# Function to list top 5 recent deployment manager versions
list_available_versions() {
    print_header "Top 5 Recent Deployment Manager Versions"
    
    print_status "Fetching recent images from ECR repository..."
    
    # Get the top 5 most recent images based on imagePushedAt
    local images_json
    images_json=$(aws ecr describe-images \
        --repository-name "$ECR_REPO_NAME" \
        --region "$ECR_REGION" \
        --output json 2>/dev/null)
    
    if [[ $? -ne 0 ]]; then
        print_error "Failed to fetch images from ECR repository"
        return 1
    fi
    
    # Parse and display the top 5 recent images
    echo "$images_json" | jq -r '
        .imageDetails | 
        sort_by(.imagePushedAt) | 
        reverse | 
        .[0:5] | 
        .[] | 
        "\(.imageTags[0] // "untagged") | \(.imagePushedAt) | \(.imageSizeInBytes / 1024 / 1024 | floor) MB"
    ' 2>/dev/null | {
        echo "Version | Pushed Date | Size"
        echo "--------|-------------|------"
        while IFS='|' read -r tag date size; do
            printf "%-20s | %-19s | %s\n" "$tag" "$date" "$size"
        done
    } || {
        print_error "Failed to parse image data. Please check if jq is installed."
        return 1
    }
    
    return 0
}

# Function to check if specific version exists
check_version_exists() {
    local version="$1"
    
    print_status "Checking if version '$version' exists in ECR repository..."
    
    # Check if the image tag exists
    if aws ecr describe-images --repository-name "$ECR_REPO_NAME" --region "$ECR_REGION" --image-ids imageTag="$version" &>/dev/null; then
        print_status "Version '$version' found in ECR repository"
        return 0
    else
        print_error "Version '$version' not found in ECR repository"
        return 1
    fi
}

# Function to pull docker image
pull_docker_image() {
    local version="$1"
    
    print_status "Pulling deployment manager image version '$version'..."
    
    # Full ECR image name
    local full_image_name="$ECR_ACCOUNT_ID.dkr.ecr.$ECR_REGION.amazonaws.com/$ECR_REPO_NAME:$version"
    
    # Pull the image (authentication already done)
    docker pull "$full_image_name" || {
        print_error "Failed to pull docker image"
        exit 1
    }
    
    print_status "Successfully pulled deployment manager image version '$version'"
    
    # Tag the image with a simpler name
    print_status "Tagging image with simple name..."
    docker tag "$full_image_name" "deployment_manager:$version" || {
        print_error "Failed to tag docker image"
        exit 1
    }
    
    print_status "Successfully tagged image as 'deployment_manager:$version'"
    
    # Remove the original image with full path to keep only the simplified name
    print_status "Removing original image with full registry path..."
    docker rmi "$full_image_name" || {
        print_warning "Failed to remove original image with full path"
    }
}

# Function to update deployment manager version in docker-compose file
update_docker_compose_with_dm_version() {
    local dm_version="$1"
    
    if [[ -z "$dm_version" ]]; then
        print_warning "No deployment manager version provided, keeping default"
        return 0
    fi
    
    # Get FM_VERSION from environment or determine it
    local fm_version
    if [[ -n "$FM_VERSION" ]]; then
        fm_version="$FM_VERSION"
    else
        # Determine FM_VERSION similar to build_fm_images.sh
        local git_des=$(git describe --all)
        local git_tag=$(git describe --all | awk '{split($0,a,"/"); print a[2];}')
        if [[ $git_des =~ "tags/" ]]; then
            fm_version="$git_tag"
        else
            fm_version=$(git rev-parse --abbrev-ref HEAD)
        fi
    fi
    
    local compose_file="static/docker_compose_v${fm_version}.yml"
    
    if [[ ! -f "$compose_file" ]]; then
        print_error "Docker compose file not found: $compose_file"
        print_status "Please run build_fm_images.sh first to create the docker-compose file"
        return 1
    fi
    
    print_status "Updating deployment manager version to: $dm_version in $compose_file"
    
    # Update the deployment manager image version in docker-compose file
    if [ "$(uname)" = "Darwin" ]; then
        sed -i.bak "s/deployment_manager:dm_version/deployment_manager:$dm_version/g" "$compose_file"
    else
        sed -i "s/deployment_manager:dm_version/deployment_manager:$dm_version/g" "$compose_file"
    fi
    
    print_status "Successfully updated deployment manager image version in $compose_file"
}

# Main execution
main() {
    print_header "Deployment Manager ECR Pull Script"
    
    # Check prerequisites
    check_aws_cli
    check_docker
    check_jq
    
    # Setup docker authentication environment
    setup_docker_auth
    
    # Get AWS credentials from user
    get_aws_credentials
    
    # Authenticate with ECR using AWS CLI
    authenticate_ecr
    
    # List available versions after successful authentication
    if ! list_available_versions; then
        print_error "Failed to list available versions. Cannot proceed."
        exit 1
    fi
    
    # Get deployment manager version from user
    echo
    echo -n "Enter Deployment Manager Docker Image Version (from the list above): "
    read -r DM_VERSION
    
    # Validate version input
    if ! validate_version "$DM_VERSION"; then
        exit 1
    fi
    
    # Check if version exists
    if ! check_version_exists "$DM_VERSION"; then
        print_error "Version '$DM_VERSION' not found. Please check the available versions above and try again."
        exit 1
    fi
    
    # Pull the docker image
    pull_docker_image "$DM_VERSION"
    
    print_header "Script completed successfully!"
    print_status "Deployment manager image version '$DM_VERSION' has been pulled successfully"
    
    # Update docker-compose file with the pulled version
    update_docker_compose_with_dm_version "$DM_VERSION"
    
    # Output the version for use by other scripts
    echo "DM_VERSION=$DM_VERSION"
    
    # Clean up authentication data
    cleanup_auth
}

# Set up trap to cleanup on script exit
trap cleanup_auth EXIT

# Run main function
main "$@"
