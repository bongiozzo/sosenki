#!/bin/bash
set -e

# Directory for temporary env vars
ENV_FILE="/tmp/sosenki-ngrok-env.sh"

# Check if ngrok is already running
if pgrep -f 'ngrok http 8000' > /dev/null; then
  echo "ngrok is already running"
else
  echo "Starting ngrok tunnel on port 8000..."
  ngrok http 8000 > /dev/null 2>&1 &
  sleep 2
fi

# Get ngrok tunnel URL from API
TUNNEL_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[0].public_url // empty')

if [ -z "$TUNNEL_URL" ]; then
  echo "ERROR: Could not retrieve ngrok tunnel URL"
  echo "Make sure ngrok is running and accessible at http://127.0.0.1:4040"
  exit 1
fi

# Export environment variables
export NGROK_TUNNEL_URL="$TUNNEL_URL"
export WEBHOOK_URL="$TUNNEL_URL/webhook/telegram"
export MINI_APP_URL="$TUNNEL_URL/mini-app"

# Save to file for later use
cat > "$ENV_FILE" << EOF
export NGROK_TUNNEL_URL="$TUNNEL_URL"
export WEBHOOK_URL="$TUNNEL_URL/webhook/telegram"
export MINI_APP_URL="$TUNNEL_URL/mini-app"
EOF

echo "Tunnel URL: $TUNNEL_URL"
echo "Webhook URL: $WEBHOOK_URL"
echo "Mini App URL: $MINI_APP_URL"
echo "Logs: logs/server.log"
echo "Environment saved to: $ENV_FILE"
