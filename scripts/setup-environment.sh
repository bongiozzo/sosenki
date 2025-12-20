
#!/bin/bash
# Note: When called as `bash ./setup-environment.sh`, this runs in a subshell
# To use exported variables in parent shell (Makefile), source it instead: source ./setup-environment.sh
set -e

# Load configuration from .env (single source of truth)
if [ -f ".env" ]; then
  set -a
  source .env
  set +a
fi

# PORT is loaded from .env above - no default needed
if [ -z "$PORT" ]; then
  echo "ERROR: PORT not set in .env file"
  exit 1
fi

# Export configuration variables from .env
export DATABASE_URL
export GOOGLE_CREDENTIALS_PATH
export TELEGRAM_BOT_NAME
export TELEGRAM_MINI_APP_ID

# Check if DOMAIN is set and ENV=dev for LAN development
if [ -n "$DOMAIN" ] && [ "$ENV" = "dev" ]; then
  # LAN development mode: use DOMAIN:PORT (no ngrok)
  echo "LAN development mode detected (DOMAIN=$DOMAIN, ENV=$ENV)"
  
  export WEBHOOK_URL="http://$DOMAIN:$PORT/webhook/telegram"
  export MINI_APP_URL="http://$DOMAIN:$PORT/mini-app/"
  
  echo "Configuration loaded from .env"
  echo "Domain: $DOMAIN:$PORT"
  echo "Webhook URL: $WEBHOOK_URL"
  echo "Mini App URL: $MINI_APP_URL"
  
  # Clean up any existing ngrok temp file
  TEMP_ENV_FILE="/tmp/.sosenki-env"
  if [ -f "$TEMP_ENV_FILE" ]; then
    echo "Removing old ngrok configuration: $TEMP_ENV_FILE"
    rm -f "$TEMP_ENV_FILE"
  fi
  
else
  # Original ngrok mode for local development
  echo "Local development mode (using ngrok tunnel)"
  
  # Start ngrok if not already running
  if ! pgrep -f "ngrok http $PORT" > /dev/null; then
    echo "Starting ngrok tunnel on port $PORT..."
    ngrok http $PORT > /dev/null 2>&1 &
    sleep 2
  fi

  # Get ngrok tunnel URL from API
  TUNNEL_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[0].public_url // empty')

  if [ -z "$TUNNEL_URL" ]; then
    echo "ERROR: Could not retrieve ngrok tunnel URL"
    echo "Make sure ngrok is running and accessible at http://127.0.0.1:4040"
    exit 1
  fi

  # Export ngrok-specific variables
  export NGROK_TUNNEL_URL="$TUNNEL_URL"
  export WEBHOOK_URL="$TUNNEL_URL/webhook/telegram"
  export MINI_APP_URL="$TUNNEL_URL/mini-app/"

  # Write dynamic environment variables to temp file for Python to load
  TEMP_ENV_FILE="/tmp/.sosenki-env"
  cat > "$TEMP_ENV_FILE" << EOF
NGROK_TUNNEL_URL=$TUNNEL_URL
WEBHOOK_URL=$WEBHOOK_URL
MINI_APP_URL=$MINI_APP_URL
EOF
  chmod 600 "$TEMP_ENV_FILE"

  echo "Configuration loaded from .env"
  echo "Tunnel URL: $TUNNEL_URL"
  echo "Webhook URL: $WEBHOOK_URL"
  echo "Mini App URL: $MINI_APP_URL"
  echo "Dynamic env file: $TEMP_ENV_FILE"
fi
