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
    print_step "Pysäytetään palvelu päivityksen ajaksi..."
    systemctl stop $SERVICE_NAME || true
    
    # 3. Varmuuskopioi konfiguraatiot ja data
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
        # Kopioi takaisin, mutta älä ylikirjoita uudempia tiedostoja jos niitä on tullut päivityksen mukana (esim. uudet oletustiedostot)
        # Tässä tapauksessa haluamme säilyttää käyttäjän datan ensisijaisesti.
        cp -r $TEMP_DIR/data.bak/* $INSTALL_DIR/data/
    fi
    
    if [ -d "$TEMP_DIR/models.bak" ]; then
        print_step "Palautetaan models-hakemisto..."
        # Palautetaan käyttäjän kouluttamat mallit
        cp -r $TEMP_DIR/models.bak/* $INSTALL_DIR/models/
    fi
    
    # Varmista oikeudet
    chown -R pp2:pp2 $INSTALL_DIR
    chmod 755 $INSTALL_DIR
    chmod 600 $INSTALL_DIR/.env 2>/dev/null || true
    
    # Varmista ban-listan oikeudet (luetaan config.yaml:sta)
    if [ -f "$INSTALL_DIR/config.yaml" ]; then
        # Yritetään etsiä banlist_path yksinkertaisella grep-komennolla
        BANLIST_PATH=$(grep "banlist_path:" "$INSTALL_DIR/config.yaml" | head -n 1 | awk -F': ' '{print $2}' | tr -d '"' | tr -d "'" | tr -d '\r')
        
        if [ ! -z "$BANLIST_PATH" ] && [ -f "$BANLIST_PATH" ]; then
             print_step "Varmistetaan ban-listan kirjoitusoikeudet: $BANLIST_PATH"
             chmod 666 "$BANLIST_PATH" || true
        fi
    fi
    
    # 5. Päivitä riippuvuudet
    print_step "Päivitetään Python-riippuvuudet..."
    if [ -f "$INSTALL_DIR/original_venv_bin_python" ]; then
         # Jos käytössä oli joku custom venv, yritä arvata. Oletetaan standardi sijainti.
         VENV_PYTHON="$INSTALL_DIR/venv/bin/python"
    else
         VENV_PYTHON="$INSTALL_DIR/venv/bin/python"
    fi
    
    if [ -f "$VENV_PYTHON" ]; then
        $INSTALL_DIR/venv/bin/pip install -r $INSTALL_DIR/requirements.txt -q
    else
        print_warning "Virtuaaliympäristöä ei löytynyt. Riippuvuuksia ei voitu päivittää automaattisesti."
    fi

    # 6. Käynnistä palvelu
    print_step "Käynnistetään palvelu..."
    systemctl start $SERVICE_NAME
    
    # Siivous
    rm -rf $TEMP_DIR
    
    echo ""
    echo -e "${GREEN}Päivitys valmis!${NC}"
    echo "Tarkista status komennolla: sudo systemctl status $SERVICE_NAME"
}

main
