#!/bin/bash

git submodule update --init

MAIN_BRANCH=$(git branch --show-current)

if [ "$MAIN_BRANCH" = "fm_staging" ]; then
    TARGET_BRANCH="staging"
elif [ "$MAIN_BRANCH" = "main" ]; then
    TARGET_BRANCH="main"
else
    TARGET_BRANCH="dev"
fi

# Switch fm_plugins to the desired branch
cd fm_plugins
git fetch origin
git checkout "$TARGET_BRANCH"
git pull origin "$TARGET_BRANCH"

echo "Main repo is on $MAIN_BRANCH"
echo "fm_plugins set to $TARGET_BRANCH"