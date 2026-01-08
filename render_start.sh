#!/bin/bash
set -e

# Define persistent paths
DATA_DIR="/var/data"
DB_FILE="$DATA_DIR/cms.db"
UPLOADS_DIR="$DATA_DIR/uploads"

echo "--- Starting Render Deployment Setup ---"

# 1. Database Setup
if [ ! -f "$DB_FILE" ]; then
    echo "No database found in persistent storage."
    if [ -f "cms.db" ]; then
        echo "Copying default database from repository..."
        cp cms.db "$DB_FILE"
    else
        echo "No repository database found. App will create a new one."
    fi
else
    echo "Existing database found in persistent storage."
fi

# 2. Uploads Directory Setup
echo "Configuring uploads directory..."
mkdir -p "$UPLOADS_DIR"

# Path where the app expects uploads to be
APP_UPLOADS_PATH="cms_app/static/uploads"

# Remove the existing directory/symlink if it exists
if [ -d "$APP_UPLOADS_PATH" ] || [ -L "$APP_UPLOADS_PATH" ]; then
    echo "Removing ephemeral uploads directory..."
    rm -rf "$APP_UPLOADS_PATH"
fi

# Create symlink: cms_app/static/uploads -> /var/data/uploads
echo "Linking $APP_UPLOADS_PATH -> $UPLOADS_DIR"
ln -s "$UPLOADS_DIR" "$APP_UPLOADS_PATH"

# 3. Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn app:app --bind 0.0.0.0:$PORT
