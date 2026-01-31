#!/bin/bash
#
# PP2SusDetector - Linux/macOS asennusskripti
# Asentaa kaikki tarvittavat riippuvuudet ja konfiguroi systemd servicen
#

set -e

# Värit terminaaliin
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

INSTALL_DIR="/opt/pp2susdetector"
SERVICE_USER="pp2"
SERVICE_NAME="pp2susdetector"

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║           PP2SusDetector - Asennusskripti                   ║"
    echo "║        Chat moderation with Machine Learning                 ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "Tämä skripti vaatii root-oikeudet. Suorita: sudo ./install.sh"
        exit 1
    fi
}

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    elif [ "$(uname)" == "Darwin" ]; then
        OS="macos"
    else
        OS="unknown"
    fi
    echo -e "Käyttöjärjestelmä: ${BLUE}$OS${NC}"
}

install_dependencies() {
    print_step "Asennetaan järjestelmäriippuvuudet..."
    
    case $OS in
        ubuntu|debian)
            apt-get update -qq
            apt-get install -y python3 python3-pip python3-venv python3-dev git curl pkg-config libsystemd-dev gcc
            ;;
        fedora|rhel|centos|rocky|almalinux)
            dnf install -y python3 python3-pip python3-devel git curl pkgconfig systemd-devel gcc
            ;;
        arch|manjaro)
            pacman -Sy --noconfirm python python-pip git curl pkgconf systemd gcc
            ;;
        opensuse*|sles)
            zypper install -y python3 python3-pip python3-devel git curl pkg-config systemd-devel gcc
            ;;
        macos)
            if ! command -v brew &> /dev/null; then
                print_warning "Homebrew ei ole asennettu. Asenna se ensin: https://brew.sh"
                exit 1
            fi
            brew install python3 git curl
            ;;
        *)
            print_warning "Tuntematon käyttöjärjestelmä. Varmista että Python 3.10+ on asennettu."
            ;;
    esac
}

create_user() {
    if [ "$OS" != "macos" ]; then
        if ! id "$SERVICE_USER" &>/dev/null; then
            print_step "Luodaan käyttäjä: $SERVICE_USER"
            useradd -r -s /bin/false -d $INSTALL_DIR $SERVICE_USER
        else
            print_step "Käyttäjä $SERVICE_USER on jo olemassa"
        fi
    fi
}

create_directories() {
    print_step "Luodaan hakemistorakenne: $INSTALL_DIR"
    
    mkdir -p $INSTALL_DIR
    mkdir -p $INSTALL_DIR/data
    mkdir -p $INSTALL_DIR/models
    mkdir -p $INSTALL_DIR/logs
}

copy_files() {
    print_step "Kopioidaan tiedostot..."
    
    # Määritä lähdepolku (missä tämä skripti sijaitsee)
    SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Kopioi Python-tiedostot
    cp "$SOURCE_DIR"/*.py $INSTALL_DIR/ 2>/dev/null || true
    cp "$SOURCE_DIR"/requirements.txt $INSTALL_DIR/
    cp "$SOURCE_DIR"/pp2_rules.txt $INSTALL_DIR/ 2>/dev/null || true
    
    # Kopioi data ja models jos niitä on
    cp -r "$SOURCE_DIR"/data/* $INSTALL_DIR/data/ 2>/dev/null || true
    cp -r "$SOURCE_DIR"/models/* $INSTALL_DIR/models/ 2>/dev/null || true
    
    print_step "Tiedostot kopioitu"
}

setup_virtualenv() {
    print_step "Luodaan Python virtuaaliympäristö..."
    
    python3 -m venv $INSTALL_DIR/venv
    
    # Aktivoi venv ja asenna riippuvuudet
    source $INSTALL_DIR/venv/bin/activate
    pip install --upgrade pip -q
    
    print_step "Asennetaan Python-riippuvuudet (requirements.txt)..."
    pip install -r $INSTALL_DIR/requirements.txt -q
    
    # Yritetään asentaa systemd-python erikseen jos ollaan Linuxilla
    if [ "$OS" != "macos" ]; then
        print_step "Yritetään asentaa systemd-python..."
        if pip install systemd-python -q 2>/dev/null; then
            print_step "systemd-python asennettu onnistuneesti"
        else
            print_warning "systemd-python asennus epäonnistui. Journal-logit eivät ole käytössä."
            print_warning "Tämä ei estä ohjelman toimintaa, mutta logit näkyvät vain konsolissa."
        fi
    fi
    
    deactivate
    
    print_step "Virtuaaliympäristö valmis"
}

configure_env() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}             YMPÄRISTÖMUUTTUJIEN KONFIGUROINTI                   ${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    ENV_FILE="$INSTALL_DIR/.env"
    
    # Discord Bot Token
    echo -e "${YELLOW}Discord Bot Token${NC}"
    echo "Saat tämän Discord Developer Portalista (https://discord.com/developers/applications)"
    read -p "DISCORD_BOT_TOKEN: " DISCORD_BOT_TOKEN
    
    # Discord Webhook URL
    echo ""
    echo -e "${YELLOW}Discord Webhook URL${NC}"
    echo "Luo webhook Discord-palvelimellesi kanava-asetuksista"
    read -p "DISCORD_WEBHOOK_URL: " DISCORD_WEBHOOK_URL
    
    # Admin Password
    echo ""
    echo -e "${YELLOW}PP2 Admin Password${NC}"
    echo "PP2Host admin-paneelin salasana (jätä tyhjäksi jos haet Dockerista automaattisesti)"
    read -sp "ADMIN_PASSWORD: " ADMIN_PASSWORD
    echo ""
    
    # Kirjoita .env tiedosto
    cat > $ENV_FILE << EOF
# PP2SusDetector Environment Configuration
# Luotu: $(date)

# Discord Bot Token (Vaaditaan)
DISCORD_BOT_TOKEN=$DISCORD_BOT_TOKEN

# Discord Webhook URL (Vaaditaan)
DISCORD_WEBHOOK_URL=$DISCORD_WEBHOOK_URL

# PP2 Admin Password (Valinnainen - jos tyhjä, haetaan Dockerista)
ADMIN_PASSWORD=$ADMIN_PASSWORD

# ML Model Path (Oletusarvo)
ML_MODEL_PATH=models/violation_model.joblib
EOF

    chmod 600 $ENV_FILE
    print_step ".env tiedosto luotu: $ENV_FILE"
}

configure_yaml() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}               CONFIG.YAML KONFIGUROINTI                         ${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    CONFIG_FILE="$INSTALL_DIR/config.yaml"
    
    # Chatlog Path
    echo -e "${YELLOW}PP2 Chatlog polku${NC}"
    echo "Polku chatlog.txt tiedostoon (esim. /etc/pp2host/static/chatlog.txt)"
    read -p "chatlog_path [/etc/pp2host/static/chatlog.txt]: " CHATLOG_PATH
    CHATLOG_PATH=${CHATLOG_PATH:-"/etc/pp2host/static/chatlog.txt"}
    
    # Playlog Path
    echo ""
    echo -e "${YELLOW}PP2 Playlog polku${NC}"
    read -p "playlog_path [/etc/pp2host/static/playlog.txt]: " PLAYLOG_PATH
    PLAYLOG_PATH=${PLAYLOG_PATH:-"/etc/pp2host/static/playlog.txt"}
    
    # Container Name
    echo ""
    echo -e "${YELLOW}PP2Host Docker Container nimi${NC}"
    echo "(Jätä tyhjäksi jos et käytä Dockeria)"
    read -p "container_name [pp2host]: " CONTAINER_NAME
    CONTAINER_NAME=${CONTAINER_NAME:-"pp2host"}
    
    # Admin URL
    echo ""
    echo -e "${YELLOW}PP2 Admin Panel URL${NC}"
    read -p "admin_url [http://localhost:4500/Admin.html]: " ADMIN_URL
    ADMIN_URL=${ADMIN_URL:-"http://localhost:4500/Admin.html"}
    
    # Discord verify_all
    echo ""
    echo -e "${YELLOW}Tarkista kaikki viestit Discordissa?${NC}"
    read -p "verify_all (true/false) [true]: " VERIFY_ALL
    VERIFY_ALL=${VERIFY_ALL:-"true"}
    
    # Banlist Path
    echo ""
    echo -e "${YELLOW}PP2 Banlist polku${NC}"
    read -p "banlist_path [/etc/pp2host/static/ban.dat]: " BANLIST_PATH
    BANLIST_PATH=${BANLIST_PATH:-"/etc/pp2host/static/ban.dat"}

    # Kirjoita config.yaml
    cat > $CONFIG_FILE << EOF
# PP2SusDetector Configuration
# Luotu: $(date)

# Palvelimien asetukset
servers:
  - name: "Main Server"
    chatlog_path: "$CHATLOG_PATH"
    playlog_path: "$PLAYLOG_PATH"
    banlist_path: "$BANLIST_PATH"
    container_name: "$CONTAINER_NAME"
    admin_url: "$ADMIN_URL"
    admin_user: "admin"
    admin_password: "$ADMIN_PASSWORD"

ml:
  model_path: "models/violation_model.joblib"

discord:
  enabled: true
  verify_all: $VERIFY_ALL

rules:
  severe:
    - "Epäsiveelliset nikit"
    - "Rasistinen puhe"
    - "Vakava solvaaminen"
    - "Sotapropaganda"
  moderate:
    - "Sopimaton nikki"
    - "Kiroilu päiväsaikaan"
    - "Jatkuva lokitus"
  minor:
    - "Epäselvät tapaukset"
    - "Lievä epäkohteliaisuus"
EOF

    print_step "config.yaml luotu: $CONFIG_FILE"
}

setup_systemd() {
    if [ "$OS" == "macos" ]; then
        print_warning "macOS ei tue systemd:tä. Käytä launchd:tä tai suorita manuaalisesti."
        return
    fi
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}               SYSTEMD SERVICE KONFIGUROINTI                     ${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    read -p "Haluatko asentaa systemd servicen? (k/e) [k]: " INSTALL_SYSTEMD
    INSTALL_SYSTEMD=${INSTALL_SYSTEMD:-"k"}
    
    if [ "$INSTALL_SYSTEMD" != "k" ] && [ "$INSTALL_SYSTEMD" != "K" ]; then
        print_warning "systemd service ohitettu"
        return
    fi
    
    SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
    
    cat > $SERVICE_FILE << EOF
[Unit]
Description=PP2 Suspicious Detector - Chat moderation with ML
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python detector.py
Restart=always
RestartSec=10

# Environment file for secrets
EnvironmentFile=$INSTALL_DIR/.env

# Logging - goes to systemd journal
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR/data $INSTALL_DIR/logs $INSTALL_DIR/models

[Install]
WantedBy=multi-user.target
EOF

    print_step "systemd service luotu: $SERVICE_FILE"
    
    # Aseta oikeudet
    chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
    chmod 755 $INSTALL_DIR
    
    # Varmista ban-listan oikeudet jos polku on määritetty
    if [ ! -z "$BANLIST_PATH" ] && [ -f "$BANLIST_PATH" ]; then
        print_step "Asetetaan kirjoitusoikeudet ban-listaan: $BANLIST_PATH"
        # Annetaan luku- ja kirjoitusoikeudet kaikille (varmistaa että toimii sekä servicenä että manuaalisesti)
        chmod 666 "$BANLIST_PATH" || true
    fi
    
    # Lataa uudelleen ja ota käyttöön
    systemctl daemon-reload
    
    read -p "Haluatko käynnistää servicen nyt? (k/e) [k]: " START_NOW
    START_NOW=${START_NOW:-"k"}
    
    if [ "$START_NOW" == "k" ] || [ "$START_NOW" == "K" ]; then
        systemctl enable $SERVICE_NAME
        systemctl start $SERVICE_NAME
        print_step "Service käynnistetty ja asetettu käynnistymään automaattisesti"
        
        echo ""
        echo -e "${GREEN}Service status:${NC}"
        systemctl status $SERVICE_NAME --no-pager || true
    else
        print_step "Service on valmis, käynnistä se komennolla: sudo systemctl start $SERVICE_NAME"
    fi
}

print_completion() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║               ASENNUS VALMIS!                                ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Asennushakemisto: ${BLUE}$INSTALL_DIR${NC}"
    echo ""
    echo -e "${YELLOW}Hyödyllisiä komentoja:${NC}"
    if [ "$OS" != "macos" ]; then
        echo "  sudo systemctl status $SERVICE_NAME   - Tarkista status"
        echo "  sudo systemctl restart $SERVICE_NAME  - Käynnistä uudelleen"
        echo "  sudo journalctl -u $SERVICE_NAME -f   - Seuraa lokeja"
    fi
    echo "  cd $INSTALL_DIR && ./venv/bin/python detector.py  - Suorita manuaalisesti"
    echo ""
    echo -e "${YELLOW}Konfiguraatiotiedostot:${NC}"
    echo "  $INSTALL_DIR/.env          - Ympäristömuuttujat (salaiset)"
    echo "  $INSTALL_DIR/config.yaml   - Sovelluskonfiguraatio"
    echo ""
}

# Pääohjelma
main() {
    print_header
    check_root
    detect_os
    
    echo ""
    read -p "Jatketaanko asennusta? (k/e): " CONTINUE
    if [ "$CONTINUE" != "k" ] && [ "$CONTINUE" != "K" ]; then
        echo "Asennus peruttu."
        exit 0
    fi
    
    echo ""
    install_dependencies
    create_user
    create_directories
    copy_files
    setup_virtualenv
    configure_env
    configure_yaml
    setup_systemd
    print_completion
}

main "$@"
