#!/bin/bash

# Test Pixelbin API endpoint
# Usage: ./test_pixelbin_endpoint.sh <path_to_image_file>

ENDPOINT="https://api.pixelbin.io/service/platform/transformation/v1.0/predictions/skinAnalysisInt/generate"
BEARER_TOKEN="YzVlMTVkZjctNzNhNi00Nzk2LWFjMDctYjNiNmE2Y2NmYjk3"

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





