#!/bin/bash


SAVE_DIR="$HOME/Documents/sysinfo_project/syslog"
FILE_NAME="sysinfo.txt"
ENC_FILE="$FILE_NAME.enc"
PASSWORD="StrongPass#2025"  # CHANGE THIS if needed


mkdir -p "$SAVE_DIR"


{
  echo "=== SYSTEM OVERVIEW ==="
  system_profiler SPHardwareDataType

  echo -e "\n=== MEMORY STATS ==="
  vm_stat

  echo -e "\n=== DISK USAGE ==="
  df -h

  echo -e "\n=== NETWORK INTERFACES ==="
  ifconfig

  echo -e "\n=== ROUTING TABLE ==="
  netstat -nr

  echo -e "\n=== ACTIVE PROCESSES ==="
  ps aux

  echo -e "\n=== INSTALLED APPLICATIONS ==="
  ls /Applications

  echo -e "\n=== LOGGED-IN USERS ==="
  who

  echo -e "\n=== LAST LOGIN ==="
  last -1

  echo -e "\n=== KERNEL & OS INFO ==="
  uname -a
} > "$SAVE_DIR/$FILE_NAME"


openssl aes-256-cbc -salt -in "$SAVE_DIR/$FILE_NAME" -out "$SAVE_DIR/$ENC_FILE" -k "$PASSWORD"

rm "$SAVE_DIR/$FILE_NAME"

echo "✅ System info encrypted and emailed successfully."

