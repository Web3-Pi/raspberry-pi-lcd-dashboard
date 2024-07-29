#!/bin/bash

# Check if the script is run with sudo
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run with sudo"
   exit 1
fi

SERVICE_NAME="dashboard"
RUN_SCRIPT="$(pwd)/run.sh"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
REMOVE_SCRIPT="$(pwd)/remove_service.sh"

# Check if the run.sh file exists
if [ ! -f "$RUN_SCRIPT" ]; then
    echo "The file $RUN_SCRIPT does not exist in the current directory."
    exit 1
fi

# Check if the service already exists
if systemctl list-units --full -all | grep -Fq "$SERVICE_NAME.service"; then
    echo "The service $SERVICE_NAME already exists."
    exit 1
fi

# Make the run.sh file executable
chmod +x "$RUN_SCRIPT"
chmod +x "$REMOVE_SCRIPT"

# Create the service file
cat <<EOF > $SERVICE_FILE
[Unit]
Description=Run LCD Dashboard
After=network.target

[Service]
ExecStart=$RUN_SCRIPT
Restart=on-failure
RestartSec=120

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd daemons
systemctl daemon-reload

# Enable the service to start on boot
systemctl enable $SERVICE_NAME

# Start the service
systemctl start $SERVICE_NAME

echo "The service $SERVICE_NAME has been created and started."

BGreen='\033[1;32m'     # Green
NC='\033[0m'            # No Color
echo " "
echo -e "${BGreen}The first startup may take around a dozen seconds because a 'venv' is being created and the required packages are being installed.${NC}"
echo -e "${BGreen}Please wait...${NC}"
echo " "
