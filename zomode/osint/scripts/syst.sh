#!/bin/bash

# Output path
OUTPUT_DIR="$HOME/Documents/sysinfo_logs"
mkdir -p "$OUTPUT_DIR"
OUTPUT_FILE="$OUTPUT_DIR/system_info.txt"

echo "[*] Collecting system information..."

{
  echo "========== SYSTEM REPORT =========="
  echo "Date: $(date)"
  echo "Hostname: $(scutil --get LocalHostName 2>/dev/null || echo 'N/A')"
  echo "User: $USER"
  echo "OS Version: $(sw_vers 2>/dev/null || echo 'N/A')"
  echo "Uptime: $(uptime)"
  echo

  echo "========== HARDWARE INFO =========="
  sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "CPU Info N/A"
  sysctl -n hw.memsize 2>/dev/null | awk '{print "RAM: " $1/1024/1024/1024 " GB"}'
  sysctl -n hw.model 2>/dev/null || echo "Model Info N/A"
  echo

  echo "========== STORAGE =========="
  df -h /
  echo

  echo "========== MEMORY USAGE =========="
  vm_stat
  echo

  echo "========== NETWORK =========="
  ifconfig
  echo

  echo "========== ACTIVE CONNECTIONS =========="
  netstat -ant | grep ESTABLISHED || echo "No active connections"
  echo

  echo "========== BATTERY INFO =========="
  pmset -g batt 2>/dev/null || echo "Battery Info N/A"
  echo

  echo "========== USERS =========="
  who
  echo

  echo "========== RUNNING PROCESSES =========="
  ps aux | head -n 20
  echo

  echo "========== CONNECTED USB DEVICES =========="
  ioreg -p IOUSB -l -w 0 2>/dev/null || echo "USB Info N/A"
  echo

} > "$OUTPUT_FILE"

echo "[*] System information saved to $OUTPUT_FILE"