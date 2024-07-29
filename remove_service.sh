#!/bin/bash

# Check if the script is run with sudo
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run with sudo."
    exit 1
fi

SERVICE_NAME="dashboard"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

# Stop and disable the service
if systemctl list-units --full -all | grep -Fq "$SERVICE_NAME.service"; then
    systemctl stop $SERVICE_NAME
    systemctl disable $SERVICE_NAME
else
    echo "Service $SERVICE_NAME does not exist."
    exit 1
fi

# Remove the service file
rm -f $SERVICE_FILE

# Reload systemd manager configuration
systemctl daemon-reload

echo "Service $SERVICE_NAME removed successfully."