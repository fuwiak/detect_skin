#!/bin/bash

# Test Pixelbin API endpoint
# Usage: ./test_pixelbin_endpoint.sh <path_to_image_file>
# Requires PIXELBIN_ACCESS_TOKEN environment variable

ENDPOINT="https://api.pixelbin.io/service/platform/transformation/v1.0/predictions/skinAnalysisInt/generate"

# Load .env file if it exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if PIXELBIN_ACCESS_TOKEN is set
if [ -z "$PIXELBIN_ACCESS_TOKEN" ]; then
    echo "Error: PIXELBIN_ACCESS_TOKEN environment variable is not set"
    echo "Please set it in .env file or export it:"
    echo "  export PIXELBIN_ACCESS_TOKEN=your_token_here"
    exit 1
fi

# Convert access token to bearer token using base64
BEARER_TOKEN=$(echo -n "$PIXELBIN_ACCESS_TOKEN" | base64)

if [ -z "$1" ]; then
    echo "Usage: $0 <path_to_image_file>"
    echo "Example: $0 test_image.jpg"
    exit 1
fi

if [ ! -f "$1" ]; then
    echo "Error: File '$1' not found"
    exit 1
fi

echo "Testing Pixelbin endpoint..."
echo "Endpoint: $ENDPOINT"
echo "File: $1"
echo ""

curl -X POST "$ENDPOINT" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -F "input.image=@$1" \
  -w "\n\nHTTP Status: %{http_code}\n" \
  | python -m json.tool 2>/dev/null || cat























