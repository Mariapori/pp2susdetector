#!/bin/bash
#
# PP2SusDetector - Päivitysskripti
# Päivittää asennuksen uusimpaan versioon GitHubista
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
GITHUB_ZIP_URL="https://github.com/Mariapori/pp2susdetector/archive/refs/heads/main.zip"
TEMP_DIR="/tmp/pp2update"

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║           PP2SusDetector - Päivitysskripti                   ║"
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
        print_error "Tämä skripti vaatii root-oikeudet. Suorita: sudo ./update.sh"
        exit 1
    fi
}

# Tarkistaa ja lisää puuttuvat .env-kentät
migrate_env() {
    local ENV_FILE="$INSTALL_DIR/.env"
    
    if [ ! -f "$ENV_FILE" ]; then
        print_warning ".env-tiedostoa ei löydy, ohitetaan migraatio"
        return
    fi
    
    local CHANGES_MADE=false
    
    # Tarkista Stoat-asetukset
    if ! grep -q "^STOAT_BOT_TOKEN=" "$ENV_FILE" 2>/dev/null; then
        echo "" >> "$ENV_FILE"
        echo "# Stoat / Revolt (valinnainen)" >> "$ENV_FILE"
        echo "STOAT_BOT_TOKEN=" >> "$ENV_FILE"
        CHANGES_MADE=true
        print_step "Lisättiin STOAT_BOT_TOKEN .env-tiedostoon"
    fi
    
    if ! grep -q "^STOAT_CHANNEL_ID=" "$ENV_FILE" 2>/dev/null; then
        echo "STOAT_CHANNEL_ID=" >> "$ENV_FILE"
        CHANGES_MADE=true
        print_step "Lisättiin STOAT_CHANNEL_ID .env-tiedostoon"
    fi
    
    if ! grep -q "^#.*STOAT_WEBHOOK_URL=" "$ENV_FILE" 2>/dev/null && ! grep -q "^STOAT_WEBHOOK_URL=" "$ENV_FILE" 2>/dev/null; then
        echo "# STOAT_WEBHOOK_URL=  # Valinnainen, suoraan REST API -ilmoituksiin ilman bottia" >> "$ENV_FILE"
        CHANGES_MADE=true
        print_step "Lisättiin STOAT_WEBHOOK_URL (kommentoitu) .env-tiedostoon"
    fi
    
    # Tarkista ML_MODEL_PATH
    if ! grep -q "^ML_MODEL_PATH=" "$ENV_FILE" 2>/dev/null; then
        echo "" >> "$ENV_FILE"
        echo "# ML Model Path" >> "$ENV_FILE"
        echo "ML_MODEL_PATH=models/violation_model.joblib" >> "$ENV_FILE"
        CHANGES_MADE=true
        print_step "Lisättiin ML_MODEL_PATH .env-tiedostoon"
    fi
    
    if [ "$CHANGES_MADE" = true ]; then
        print_step ".env-tiedosto päivitetty uusilla kentillä"
    else
        print_step ".env-tiedosto on ajan tasalla"
    fi
}

# Tarkistaa ja lisää puuttuvan stoat-osion config.yaml:iin
migrate_config_yaml() {
    local CONFIG_FILE="$INSTALL_DIR/config.yaml"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        print_warning "config.yaml-tiedostoa ei löydy, ohitetaan migraatio"
        return
    fi
    
    local CHANGES_MADE=false
    
    # Tarkista onko stoat-osio olemassa
    if ! grep -q "^stoat:" "$CONFIG_FILE" 2>/dev/null; then
        echo "" >> "$CONFIG_FILE"
        cat >> "$CONFIG_FILE" << 'STOAT_EOF'
stoat:
  enabled: false
  api_url: "https://api.revolt.chat"
  ws_url: "wss://ws.revolt.chat"
STOAT_EOF
        CHANGES_MADE=true
        print_step "Lisättiin stoat-osio config.yaml-tiedostoon"
    fi
    
    # Tarkista onko discord-osiossa verify_all
    if grep -q "^discord:" "$CONFIG_FILE" 2>/dev/null; then
        if ! grep -q "verify_all:" "$CONFIG_FILE" 2>/dev/null; then
            # Lisää verify_all discord-osion alle
            sed -i.tmp '/^discord:/a\  verify_all: true' "$CONFIG_FILE"
            rm -f "$CONFIG_FILE.tmp"
            CHANGES_MADE=true
            print_step "Lisättiin verify_all discord-osioon"
        fi
    fi
    
    if [ "$CHANGES_MADE" = true ]; then
        print_step "config.yaml päivitetty uusilla asetuksilla"
    else
        print_step "config.yaml on ajan tasalla"
    fi
}

# Päivittää systemd service-tiedoston
update_systemd_service() {
    local SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
    
    # Ohita macOS
    if [ "$(uname)" == "Darwin" ]; then
        print_warning "macOS ei tue systemd:tä, ohitetaan service-päivitys"
        return
    fi
    
    if [ ! -f "$SERVICE_FILE" ]; then
        print_warning "systemd service-tiedostoa ei löydy, ohitetaan päivitys"
        return
    fi
    
    print_step "Päivitetään systemd service-tiedosto..."
    
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

    systemctl daemon-reload
    print_step "systemd service päivitetty ja ladattu uudelleen"
}

main() {
    print_header
    check_root

    echo -e "Asennushakemisto: ${BLUE}$INSTALL_DIR${NC}"
    
    if [ ! -d "$INSTALL_DIR" ]; then
        print_error "Asennushakemistoa ei löydy. Asenna sovellus ensin install.sh -skriptillä."
        exit 1
    fi

    echo ""
    read -p "Aloitetaanko päivitys? (k/e): " CONTINUE
    if [ "$CONTINUE" != "k" ] && [ "$CONTINUE" != "K" ]; then
        echo "Päivitys peruttu."
        exit 0
    fi

    # 1. Lataa uusin versio
    echo ""
    print_step "Ladataan päivityspakettia..."
    rm -rf $TEMP_DIR
    mkdir -p $TEMP_DIR
    
    if ! curl -L $GITHUB_ZIP_URL -o $TEMP_DIR/update.zip; then
        print_error "Lataus epäonnistui. Tarkista internetyhteys."
        exit 1
    fi
    
    print_step "Puretaan pakettia..."
    unzip -q $TEMP_DIR/update.zip -d $TEMP_DIR
    
    # Etsi purettu kansio (yleensä pp2susdetector-main)
    SOURCE_DIR=$(find $TEMP_DIR -maxdepth 1 -type d -name "pp2susdetector-*")
    
    # 2. Pysäytä palvelu
    echo ""
    print_step "Pysäytetään palvelu päivityksen ajaksi..."
    systemctl stop $SERVICE_NAME 2>/dev/null || true
    
    # 3. Varmuuskopioi konfiguraatiot ja data
    echo ""
    print_step "Varmuuskopioidaan konfiguraatiot ja data..."
    cp $INSTALL_DIR/config.yaml $TEMP_DIR/config.yaml.bak 2>/dev/null || true
    cp $INSTALL_DIR/.env $TEMP_DIR/.env.bak 2>/dev/null || true
    
    # Varmuuskopioi data ja models hakemistot
    if [ -d "$INSTALL_DIR/data" ]; then
        print_step "Varmuuskopioidaan data-hakemisto..."
        cp -r $INSTALL_DIR/data $TEMP_DIR/data.bak
    fi
    
    if [ -d "$INSTALL_DIR/models" ]; then
        print_step "Varmuuskopioidaan models-hakemisto..."
        cp -r $INSTALL_DIR/models $TEMP_DIR/models.bak
    fi
    
    # 4. Päivitä tiedostot
    echo ""
    print_step "Päivitetään tiedostot..."
    # Kopioi uudet tiedostot päälle
    cp -r $SOURCE_DIR/* $INSTALL_DIR/
    
    # Palauta konfiguraatiot
    if [ -f "$TEMP_DIR/config.yaml.bak" ]; then
        cp $TEMP_DIR/config.yaml.bak $INSTALL_DIR/config.yaml
        print_step "Palautettiin config.yaml"
    fi
    
    if [ -f "$TEMP_DIR/.env.bak" ]; then
        cp $TEMP_DIR/.env.bak $INSTALL_DIR/.env
        print_step "Palautettiin .env"
    fi
    
    # Palauta data ja models
    if [ -d "$TEMP_DIR/data.bak" ]; then
        print_step "Palautetaan data-hakemisto..."
        cp -r $TEMP_DIR/data.bak/* $INSTALL_DIR/data/
    fi
    
    if [ -d "$TEMP_DIR/models.bak" ]; then
        print_step "Palautetaan models-hakemisto..."
        cp -r $TEMP_DIR/models.bak/* $INSTALL_DIR/models/
    fi
    
    # 5. Migraatiot - lisää puuttuvat konfiguraatiokentät
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}               KONFIGURAATIOMIGRAATIOT                            ${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    migrate_env
    migrate_config_yaml
    
    # 6. Oikeudet
    echo ""
    chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
    chmod 755 $INSTALL_DIR
    chmod 600 $INSTALL_DIR/.env 2>/dev/null || true
    
    # Varmista ban-listan oikeudet (luetaan config.yaml:sta)
    if [ -f "$INSTALL_DIR/config.yaml" ]; then
        BANLIST_PATH=$(grep "banlist_path:" "$INSTALL_DIR/config.yaml" | head -n 1 | awk -F': ' '{print $2}' | tr -d '"' | tr -d "'" | tr -d '\r')
        
        if [ ! -z "$BANLIST_PATH" ] && [ -f "$BANLIST_PATH" ]; then
             print_step "Varmistetaan ban-listan kirjoitusoikeudet: $BANLIST_PATH"
             chmod 666 "$BANLIST_PATH" || true
        fi
    fi
    
    # 7. Päivitä riippuvuudet
    echo ""
    print_step "Päivitetään Python-riippuvuudet..."
    VENV_PYTHON="$INSTALL_DIR/venv/bin/python"
    
    if [ -f "$VENV_PYTHON" ]; then
        $INSTALL_DIR/venv/bin/pip install -r $INSTALL_DIR/requirements.txt -q
        print_step "Python-riippuvuudet päivitetty"
    else
        print_warning "Virtuaaliympäristöä ei löytynyt. Riippuvuuksia ei voitu päivittää automaattisesti."
    fi

    # 8. Päivitä systemd service
    echo ""
    update_systemd_service

    # 9. Käynnistä palvelu
    echo ""
    print_step "Käynnistetään palvelu..."
    systemctl start $SERVICE_NAME 2>/dev/null || true
    
    # Siivous
    rm -rf $TEMP_DIR
    
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║               PÄIVITYS VALMIS!                              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Tarkista status komennolla: sudo systemctl status $SERVICE_NAME"
    echo ""
    echo -e "${YELLOW}Huom:${NC} Jos päivitit vanhasta versiosta, tarkista uudet asetukset:"
    echo "  $INSTALL_DIR/.env          - Stoat-asetukset (STOAT_BOT_TOKEN, STOAT_CHANNEL_ID)"
    echo "  $INSTALL_DIR/config.yaml   - stoat:-osio"
    echo ""
}

main
