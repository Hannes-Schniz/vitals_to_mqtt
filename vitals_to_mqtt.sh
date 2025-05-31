#!/bin/bash

# Configuration
BROKER="192.168.188.74"      # Replace with your MQTT broker domain or IP
PORT="1883"                    # Replace with your MQTT broker port if not default
HOSTNAME=$(hostname)
DATE=$(date --iso-8601=seconds)
TOPIC="system/vitals/$HOSTNAME"          # Replace with your desired MQTT topic

SECRETS_FILE="/etc/mqtt_secrets"

# Read username and password from secrets file
if [[ -f "$SECRETS_FILE" ]]; then
  source "$SECRETS_FILE"
else
  echo "Secrets file $SECRETS_FILE not found!"
  exit 1
fi

# MQTT_USERNAME and MQTT_PASSWORD must be set in secrets file
if [[ -z "$MQTT_USERNAME" || -z "$MQTT_PASSWORD" ]]; then
  echo "MQTT_USERNAME or MQTT_PASSWORD not set in $SECRETS_FILE"
  exit 2
fi

UPTIME=$(awk '{print int($1)}' /proc/uptime)
CPU_LOAD=$(awk '{print $1}' /proc/loadavg)
HOSTNAME=$(hostname)
DATE=$(date --iso-8601=seconds)
UPTIME=$(awk '{print int($1)}' /proc/uptime)
CPU_LOAD=$(awk '{print $1}' /proc/loadavg)

# CPU Temperature(s) and Fan Speed(s) from sensors
SENSORS_JSON=$(sensors -j 2>/dev/null)
CPU_TEMP=$(echo "$SENSORS_JSON" | jq '..|.temp1_input? // empty' | head -n1)
if [[ -z "$CPU_TEMP" ]]; then
  CPU_TEMP="N/A"
fi
CPU_FAN_SPEED=$(echo "$SENSORS_JSON" | jq '..|.fan1_input? // empty' | head -n1)
if [[ -z "$CPU_FAN_SPEED" ]]; then
  CPU_FAN_SPEED="N/A"
fi

# GPU Temperature and Fan Speed (NVIDIA GPUs)
if command -v nvidia-smi >/dev/null 2>&1; then
  GPU_TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | head -n1)
  GPU_FAN_SPEED=$(nvidia-smi --query-gpu=fan.speed --format=csv,noheader,nounits | head -n1)
  GPU_USAGE=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits)
else
  # Try with sensors for AMD or integrated GPUs
  GPU_TEMP=$(echo "$SENSORS_JSON" | jq '..|.temp2_input? // empty' | head -n1)
  if [[ -z "$GPU_TEMP" ]]; then
    GPU_TEMP="N/A"
  fi
  GPU_FAN_SPEED="N/A"
fi

MEM_TOTAL=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
MEM_AVAILABLE=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
MEM_USED=$((MEM_TOTAL - MEM_AVAILABLE))

# Get all mounted drives (excluding tmpfs, devtmpfs, squashfs, etc)
DRIVES_JSON=$(df -hP -x tmpfs -x devtmpfs -x squashfs | awk 'NR>1 {print $6}' | while read mount; do
  usage=$(df -hPBM "$mount" | awk 'NR==2 {print $3}')
  avail=$(df -hPBM "$mount" | awk 'NR==2 {print $4}')
  size=$(df -hPBM "$mount" | awk 'NR==2 {print $2}')
  printf '{"mount":"%s","used":"%s","available":"%s","size":"%s"}\n' "$mount" "$usage" "$avail" "$size"
done | jq -s '.')

# Prepare JSON payload
PAYLOAD=$(jq -n \
  --arg hostname "$HOSTNAME" \
  --arg date "$DATE" \
  --arg uptime "$UPTIME" \
  --arg cpu_load "$CPU_LOAD" \
  --arg cpu_temp "$CPU_TEMP" \
  --arg cpu_fan_speed "$CPU_FAN_SPEED" \
  --arg gpu_temp "$GPU_TEMP" \
  --arg gpu_fan_speed "$GPU_FAN_SPEED" \
  --arg gpu_usage "$GPU_USAGE" \
  --arg mem_total "$MEM_TOTAL" \
  --arg mem_used "$MEM_USED" \
  --arg mem_available "$MEM_AVAILABLE" \
  --argjson drives "$DRIVES_JSON" \
  '{
    hostname: $hostname,
    time: $date,
    uptime_s: ($uptime|tonumber),
    cpu_load: ($cpu_load|tonumber),
    cpu_temp_C: ($cpu_temp|if . == "N/A" then . else tonumber end),
    cpu_fan_speed_rpm: ($cpu_fan_speed|if . == "N/A" then . else tonumber end),
    gpu_temp_C: ($gpu_temp|if . == "N/A" then . else tonumber end),
    gpu_fan_speed_percent: ($gpu_fan_speed|if . == "N/A" then . else tonumber end),
    mem_total_kb: ($mem_total|tonumber),
    gpu_usage: ($gpu_usage|if . == "N/A" then . else tonumber end),
    mem_used_kb: ($mem_used|tonumber),
    mem_available_kb: ($mem_available|tonumber),
    drives: $drives
  }'
)

# Publish to MQTT
mosquitto_pub -h "$BROKER" -p "$PORT" -t "$TOPIC" \
  -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" \
  -m "$PAYLOAD"
