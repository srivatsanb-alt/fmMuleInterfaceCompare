#!/bin/bash
set -e
OUTPUT_FILE="fm-airgap-images-amd64.tar.zst"
OUTPUT_DIR="./output_tar"
BUILD_IMAGES=1

# Initialize image mappings
setup_image_config() {
    branch=$(git rev-parse --abbrev-ref HEAD)
    
    declare -A IMAGES_CONFIG=(
        ["fleet_manager:$branch"]="fm-backend:rootless-main"
        ["plugin:$branch"]="fm-plugin:rootless-main"
        ["mongo-express:1.0.0-alpha"]="fm-mongo-express:rootless-main"
        ["fm_nginx:$branch"]="fm-nginx:rootless-main"
    )
    
    ORIGINAL_IMAGES=(
        "fleet_manager:$branch"
        "plugin:$branch"
        "mongo-express:1.0.0-alpha"
        "fm_nginx:$branch"
    )
    
    RETAGGED_IMAGES=(
        "fm-backend:rootless-main"
        "fm-plugin:rootless-main"
        "fm-mongo-express:rootless-main"
        "fm-nginx:rootless-main"
    )
    
    echo "Original images:${IMAGES_CONFIG[@]}"
    echo "Original images:${ORIGINAL_IMAGES[@]}"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

check_dependencies() {
    if ! command_exists docker; then
        echo "Error: Docker is not installed"
        exit 1
    fi

    if ! command_exists zstd; then
        echo "Error: zstd is not installed"
        echo "Installing zstd..."
        apt-get update && apt-get install -y zstd || yum install -y zstd
    fi
}


setup_environment() {
    mkdir -p $OUTPUT_DIR
    chmod 755 "$OUTPUT_DIR"
}


verify_original_images() {
    echo "Verifying original images exist..."
    MISSING_IMAGES=0
    for image in "${ORIGINAL_IMAGES[@]}"; do
        if ! docker image inspect "$image" >/dev/null 2>&1; then
            echo "Error: Original image $image does not exist"
            MISSING_IMAGES=1
        else
            echo "Original image $image exists"
        fi
    done

    if [ $MISSING_IMAGES -eq 1 ]; then
        echo "Some original images are missing. Please check image names and tags."
        exit 1
    fi
}


retag_images() {
    echo "Retagging images with registry address..."
    for i in "${!ORIGINAL_IMAGES[@]}"; do
        original="${ORIGINAL_IMAGES[$i]}"
        retagged="${RETAGGED_IMAGES[$i]}"
        
        echo "Retagging $original to $retagged"
        docker tag "$original" "$retagged"
        
        if [ $? -ne 0 ]; then
            echo "Failed to retag $original to $retagged. Exiting."
            exit 1
        fi
    done
}


verify_retagged_images() {
    echo "Verifying retagged images exist..."
    for image in "${RETAGGED_IMAGES[@]}"; do
        if ! docker image inspect "$image" >/dev/null 2>&1; then
            echo "Error: Retagged image $image does not exist"
            exit 1
        else
            echo "Retagged image $image exists"
            creation_time=$(docker inspect --format='{{.Created}}' "$image")
            echo "  Created: $creation_time"
        fi
    done
}


save_and_compress_images() {
    echo "Saving and compressing retagged images..."
    echo "This may take a few minutes depending on image sizes..."

    echo "Saving all images to a single tar file..."
    docker save ${RETAGGED_IMAGES[@]} -o "$OUTPUT_DIR/temp_all_images.tar"
    SAVE_RESULT=$?

    if [ $SAVE_RESULT -eq 0 ]; then
        echo "Compressing tar file with zstd..."
        zstd -f "$OUTPUT_DIR/temp_all_images.tar" -o "$OUTPUT_DIR/$OUTPUT_FILE"
        COMPRESS_RESULT=$?

        rm -f "$OUTPUT_DIR/temp_all_images.tar"
    else
        COMPRESS_RESULT=1
    fi
    
    if [ $SAVE_RESULT -eq 0 ] && [ $COMPRESS_RESULT -eq 0 ]; then
        return 0
    else
        echo "Error: Failed to save and compress images"
        return 1
    fi
}

display_results_and_cleanup() {
    if [ -f "$OUTPUT_DIR/$OUTPUT_FILE" ]; then
        # Get the file size
        FILE_SIZE=$(du -h "$OUTPUT_DIR/$OUTPUT_FILE" | cut -f1)
        
        echo "Success! All retagged images saved and compressed to:"
        echo "$OUTPUT_DIR/$OUTPUT_FILE"
        echo "File size: $FILE_SIZE"
        echo ""
        echo "You can load these images using:"
        echo "zstd -d \"$OUTPUT_DIR/$OUTPUT_FILE\" -c | docker load"
        
        echo ""
        echo "Images included in the archive (with registry prefix):"
        for image in "${RETAGGED_IMAGES[@]}"; do
            echo "- $image"
        done
        echo ""
        echo "Removing retagged images..."

        echo "docker rmi ${RETAGGED_IMAGES[*]}"
        return 0
    else
        echo "Error: Failed to save and compress images"
        return 1
    fi
}
