#!/usr/bin/env bash
# Hardware smoke test for vlinker web API
# Usage: CLEAR=true ./hw_smoke.sh
BASE=http://127.0.0.1:8000
echo "Serial status:"; curl -sS $BASE/api/serial/status | jq
echo
echo "Ensure connected (auto-connect to /dev/ttyUSB0 if not):"
curl -sS -X POST "$BASE/api/serial/connect" -H "Content-Type: application/json" -d '{"device":"/dev/ttyUSB0","baud":115200}' | jq
echo
echo "Discover (live):"
curl -sS "$BASE/api/diag/discover" | jq
echo
echo "Read DTCs (live):"
curl -sS "$BASE/api/diag/read_dtcs?ecu=ECU_ENGINE" | jq || true
echo
echo "Read measures (live) for PIDs 0C,0D:"
curl -sS -X POST "$BASE/api/diag/read_measures" -H "Content-Type: application/json" -d '{"ecu":"ECU_ENGINE","pids":["0C","0D"]}' | jq || true

if [ "$CLEAR" = "true" ]; then
  echo
  echo "CLEARING DTCs (destructive):"
  curl -sS -X POST "$BASE/api/diag/clear_dtcs" -H "Content-Type: application/json" -d '{"ecu":"ECU_ENGINE","force":true}' | jq || true
else
  echo
  echo "Skipping destructive clear. To enable, run: CLEAR=true ./hw_smoke.sh"
fi
