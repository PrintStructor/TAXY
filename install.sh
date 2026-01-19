#!/bin/bash

#
# TAXY Installation Script
# AI-Powered Tool Alignment for Klipper Toolchangers
#
# This script installs TAXY (server + Klipper extension) on your system.
#

set -e  # Exit on error

# ==============================================================================
# CONFIGURATION
# ==============================================================================

TAXY_REPO_DIR=$(realpath $(dirname "$0"))
TAXY_ENV="${HOME}/taxy-env"
KLIPPER_HOME="${HOME}/klipper"
KLIPPER_CONFIG_HOME="${HOME}/printer_data/config"
SYSTEMD_DIR="/etc/systemd/system"
PORT="${PORT:-8085}"

PKGLIST="python3 python3-pip python3-venv virtualenv curl python3-matplotlib python3-numpy python3-opencv python3-pil python3-flask libatlas-base-dev python3-waitress python3-jinja2 python3-requests"

# ==============================================================================
# HELPER FUNCTIONS (Define BEFORE use!)
# ==============================================================================

c_default=$(echo -en "\e[39m")
c_green=$(echo -en "\e[92m")
c_yellow=$(echo -en "\e[93m")
c_red=$(echo -en "\e[91m")
c_cyan=$(echo -en "\e[96m")

log_header() {
    echo -e "${c_cyan}$1${c_default}"
}

log_info() {
    echo -e "${c_green}✓${c_default} $1"
}

log_error() {
    echo -e "${c_red}✗${c_default} $1"
}

log_blank() {
    echo ""
}

# ==============================================================================
# INSTALLATION STEPS
# ==============================================================================

install_system_packages() {
    log_header "Installing system packages..."

    # Update apt if last update was >24h ago
    if [ ! -f /var/lib/apt/periodic/update-success-stamp ] || \
       [ $(find /var/lib/apt/periodic/update-success-stamp -mmin +1440 2>/dev/null) ]; then
        log_info "Updating package list..."
        sudo apt-get update -y || log_error "apt-get update failed (continuing anyway)"
    fi

    log_info "Installing required packages..."
    sudo apt-get install -y ${PKGLIST} || {
        log_error "Some packages failed to install. Continuing..."
    }

    log_info "System packages installed"
}

create_virtualenv() {
    log_header "Setting up Python virtual environment..."

    if [ -d "${TAXY_ENV}" ]; then
        log_info "Virtual environment already exists at ${TAXY_ENV}"
    else
        log_info "Creating virtual environment at ${TAXY_ENV}..."
        python3 -m venv "${TAXY_ENV}" || {
            log_error "venv creation failed, trying virtualenv..."
            virtualenv -p /usr/bin/python3 --system-site-packages "${TAXY_ENV}"
        }
    fi

    log_info "Installing Python dependencies..."
    "${TAXY_ENV}/bin/pip" install --upgrade pip
    "${TAXY_ENV}/bin/pip" install -r "${TAXY_REPO_DIR}/requirements.txt" || {
        log_error "Some Python packages failed to install"
        return 1
    }

    log_info "Virtual environment ready"
}

install_klipper_extension() {
    log_header "Installing Klipper extension..."

    if [ ! -d "${KLIPPER_HOME}" ]; then
        log_error "Klipper not found at ${KLIPPER_HOME}"
        log_error "Please install Klipper first: https://www.klipper3d.org/Installation.html"
        return 1
    fi

    # Create symlinks for extension files (auto-updates with git pull)
    log_info "Creating symlinks in ${KLIPPER_HOME}/klippy/extras/"
    ln -sf "${TAXY_REPO_DIR}/extension/taxy.py" "${KLIPPER_HOME}/klippy/extras/taxy.py"
    ln -sf "${TAXY_REPO_DIR}/extension/taxy_utl.py" "${KLIPPER_HOME}/klippy/extras/taxy_utl.py"

    log_info "Klipper extension installed"
}

install_systemd_service() {
    log_header "Installing systemd service..."

    # Check if port is already in use
    if sudo lsof -i :${PORT} 2>/dev/null | grep -q LISTEN; then
        log_error "Port ${PORT} is already in use!"
        log_info "Stopping any existing services on port ${PORT}..."
        sudo systemctl stop TAXY_server 2>/dev/null || true
        sudo systemctl stop taxy 2>/dev/null || true
        sudo systemctl stop ktay8 2>/dev/null || true
        sleep 2
    fi

    log_info "Creating systemd service file..."
    sudo tee "${SYSTEMD_DIR}/TAXY_server.service" > /dev/null <<EOF
[Unit]
Description=TAXY Server - AI-based Tool Alignment
After=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${TAXY_REPO_DIR}/server
ExecStart=${TAXY_ENV}/bin/python3 taxy_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    log_info "Enabling and starting TAXY service..."
    sudo systemctl daemon-reload
    sudo systemctl enable TAXY_server
    sudo systemctl start TAXY_server

    sleep 3

    if sudo systemctl is-active --quiet TAXY_server; then
        log_info "TAXY service is running"
    else
        log_error "TAXY service failed to start"
        log_error "Check logs: sudo journalctl -u TAXY_server -n 50"
        return 1
    fi
}

install_macros() {
    log_header "Installing macros..."

    if [ ! -d "${KLIPPER_CONFIG_HOME}" ]; then
        log_error "Klipper config directory not found: ${KLIPPER_CONFIG_HOME}"
        return 1
    fi

    log_info "Copying taxy-macros.cfg to ${KLIPPER_CONFIG_HOME}/"
    cp "${TAXY_REPO_DIR}/taxy-macros.cfg" "${KLIPPER_CONFIG_HOME}/taxy-macros.cfg" 2>/dev/null || {
        log_error "taxy-macros.cfg not found in repo, skipping..."
    }

    log_info "Macros installed (remember to include in printer.cfg!)"
}

# ==============================================================================
# MAIN INSTALLATION
# ==============================================================================

main() {
    log_blank
    log_header "╔════════════════════════════════════════════════════════════╗"
    log_header "║         TAXY Installation Script                           ║"
    log_header "║   AI-Powered Tool Alignment for Klipper Toolchangers       ║"
    log_header "╚════════════════════════════════════════════════════════════╝"
    log_blank

    install_system_packages
    log_blank

    create_virtualenv
    log_blank

    install_klipper_extension
    log_blank

    install_systemd_service
    log_blank

    install_macros
    log_blank

    log_header "╔════════════════════════════════════════════════════════════╗"
    log_header "║                  Installation Complete!                    ║"
    log_header "╚════════════════════════════════════════════════════════════╝"
    log_blank
    log_info "Next steps:"
    log_info "1. Add to printer.cfg:"
    echo ""
    echo "    [taxy]"
    echo "    nozzle_cam_url: http://localhost/webcam/snapshot?max_delay=0"
    echo "    server_url: http://localhost:8085"
    echo "    move_speed: 1800"
    echo "    save_training_images: false"
    echo "    detection_tolerance: 0"
    echo ""
    echo "    [include taxy-macros.cfg]"
    echo ""
    log_info "2. Restart Klipper: sudo systemctl restart klipper"
    log_info "3. Test with: KTAY_START_PREVIEW (or CALIB_CAMERA_KTAY8 macro)"
    log_blank
    log_info "Server status: sudo systemctl status TAXY_server"
    log_info "Server logs: sudo journalctl -u TAXY_server -f"
    log_blank
}

# Run installation
main
