#!/usr/bin/env bash
# Smoke test: upload → transcode → stream for HLS video feature.
#
# Prerequisites:
#   - Docker stack running (make up or docker compose up)
#   - ffmpeg installed locally (to generate a test video)
#   - An Admin or Moderator account exists in the DB
#
# Usage:
#   ./scripts/smoke_test_video.sh \
#     --email admin@example.com \
#     --password yourpassword \
#     --movie-id 1
  
set -euo pipefail

# --- defaults (override via flags) ---
BASE_URL="http://localhost:8000/api/v1/cinema"
EMAIL=""
PASSWORD=""
MOVIE_ID=""
POLL_INTERVAL=5   # seconds between status polls
POLL_TIMEOUT=300  # give up after 5 minutes

# --- colour helpers ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }
info() { echo -e "${YELLOW}[INFO]${NC} $*"; }

# --- parse args ---
while [[ $# -gt 0 ]]; do
  case $1 in
    --email)    EMAIL="$2";    shift 2 ;;
    --password) PASSWORD="$2"; shift 2 ;;
    --movie-id) MOVIE_ID="$2"; shift 2 ;;
    --base-url) BASE_URL="$2"; shift 2 ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

[[ -z "$EMAIL" ]]    && fail "--email is required"
[[ -z "$PASSWORD" ]] && fail "--password is required"
[[ -z "$MOVIE_ID" ]] && fail "--movie-id is required"

command -v python3 >/dev/null 2>&1 || fail "python3 is not installed"
command -v ffmpeg  >/dev/null 2>&1 || fail "ffmpeg is not installed"
command -v curl    >/dev/null 2>&1 || fail "curl is not installed"

json_get() { python3 -c "import sys,json; print(json.load(sys.stdin).get('$1',''))" <<< "$2"; }

# ---- Step 1: generate a tiny test video (5 s, 320x240) ----
info "Generating test video (5s, 320x240)..."
TMP_VIDEO=$(mktemp /tmp/smoke_test_XXXXXX.mp4)
ffmpeg -f lavfi -i "testsrc=duration=5:size=320x240:rate=24" \
       -f lavfi -i "sine=frequency=440:duration=5" \
       -c:v libx264 -b:v 200k \
       -c:a aac -b:a 64k \
       -y "$TMP_VIDEO" -loglevel error
ok "Test video: $TMP_VIDEO ($(du -h "$TMP_VIDEO" | cut -f1))"

# ---- Step 2: login ----
info "Logging in as $EMAIL..."
LOGIN_RESP=$(curl -sf -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")
ACCESS_TOKEN=$(json_get access_token "$LOGIN_RESP")
[[ -z "$ACCESS_TOKEN" ]] && fail "Login failed. Response: $LOGIN_RESP"
ok "Login successful"

AUTH_HEADER="Authorization: Bearer $ACCESS_TOKEN"

# ---- Step 3: upload video ----
info "Uploading test video to movie $MOVIE_ID..."
UPLOAD_RESP=$(curl -sf -X POST "$BASE_URL/movies/$MOVIE_ID/video" \
  -H "$AUTH_HEADER" \
  -F "file=@$TMP_VIDEO;type=video/mp4")
UPLOAD_STATUS=$(python3 -c "import sys,json; d=json.loads(sys.argv[1]); print(d.get('video',{}).get('status',''))" "$UPLOAD_RESP")
VIDEO_ID=$(python3 -c "import sys,json; d=json.loads(sys.argv[1]); print(d.get('video',{}).get('id',''))" "$UPLOAD_RESP")
[[ -z "$UPLOAD_STATUS" ]] && fail "Upload failed. Response: $UPLOAD_RESP"
ok "Upload accepted — video_id=$VIDEO_ID, status=$UPLOAD_STATUS"

# ---- Step 4: poll status until READY or FAILED ----
info "Polling transcode status (timeout=${POLL_TIMEOUT}s)..."
ELAPSED=0
while true; do
  STATUS_RESP=$(curl -sf "$BASE_URL/movies/$MOVIE_ID/video/status" \
    -H "$AUTH_HEADER")
  CURRENT_STATUS=$(json_get status "$STATUS_RESP")
  info "  status=$CURRENT_STATUS (${ELAPSED}s elapsed)"

  if [[ "$CURRENT_STATUS" == "ready" ]]; then
    ok "Transcode complete"
    break
  fi

  if [[ "$CURRENT_STATUS" == "failed" ]]; then
    ERROR=$(json_get error_message "$STATUS_RESP")
    fail "Transcode FAILED: $ERROR"
  fi

  if [[ $ELAPSED -ge $POLL_TIMEOUT ]]; then
    fail "Timed out after ${POLL_TIMEOUT}s. Last status: $CURRENT_STATUS"
  fi

  sleep "$POLL_INTERVAL"
  ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

# ---- Step 5: verify stream redirect ----
info "Checking stream endpoint..."
STREAM_URL=$(curl -sf -o /dev/null -w "%{redirect_url}" \
  "$BASE_URL/movies/$MOVIE_ID/stream" \
  -H "$AUTH_HEADER")
[[ -z "$STREAM_URL" ]] && fail "Stream endpoint did not return a redirect URL"
ok "Stream redirects to: $STREAM_URL"

# Replace internal Docker hostname with localhost so the playlist is reachable from the host
LOCAL_STREAM_URL="${STREAM_URL//minio:/localhost:}"

# ---- Step 6: verify master playlist is reachable ----
info "Fetching master playlist from $LOCAL_STREAM_URL..."
PLAYLIST=$(curl -sf "$LOCAL_STREAM_URL")
echo "$PLAYLIST" | grep -q "#EXTM3U" || fail "master.m3u8 is not a valid HLS playlist"
echo "$PLAYLIST" | grep -q "360p"    || fail "master.m3u8 missing 360p variant"
echo "$PLAYLIST" | grep -q "720p"    || fail "master.m3u8 missing 720p variant"
ok "master.m3u8 is valid"

# ---- cleanup ----
rm -f "$TMP_VIDEO"

echo ""
ok "=== Smoke test PASSED ==="
echo "   Stream URL: $STREAM_URL"
