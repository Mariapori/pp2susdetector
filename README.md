# PP2 Suspicious Detector

Prototyyppi hahmoteltu ja testailtu Google AntiGravityn avulla.

Sovellus joka valvoo PP2 (Pro Pilkki 2) host serverin lokia reaaliaikaisesti ja analysoi pelaajien käyttäytymistä ML:n avulla. Rikkomukset kategorisoidaan vakavuuden mukaan ja raportoidaan Discord- ja/tai Stoat (Revolt) -kanavalle.

## Ominaisuudet

- 🎣 **Reaaliaikainen valvonta**: Seuraa PP2 hostin chat- ja pelaajalokeja
- 🤖 **ML-analyysi**
- 📊 **Kolme vakavuustasoa**:
  - 🚨 **SEVERE**: Vakavat rikkomukset -> **Banni** (rasismi, sotapropaganda, epäsiveellisyys)
  - ⚠️ **MODERATE**: Keskivakavat rikkomukset -> **Kick** (0 min, ei bannia) (kiroilu, lokitus)
  - 📝 **MINOR**: Lievät rikkomukset -> **Varoitus** (vain lokitus ja yksityisviesti)
- 💬 **Discord-integraatio**: Lähettää ilmoitukset vakavista rikkomuksista (valinnainen)
- 🦦 **Stoat/Revolt-integraatio**: Vaihtoehtoinen tai rinnakkainen chat-alusta (valinnainen)
- 💾 **Tietokanta**: Tallentaa kaikki rikkomukset SQLite-tietokantaan
- 🐳 **Docker-tuki**: Helppo käyttöönotto Docker Composella

## Komennot

### Discord
- `!unban` - Poista banni pelaajalta (avaa valikon, jossa näkyy palvelin)
- `!verify [on/off/status]` - Säädä tai tarkista kaikkien viestien tarkastus
- `!c [palvelin] [komento]` - Suorita konsolikomento (esim. `!c /kick 1` tai `!c server2 /kick 1`)
- `!train` - Käynnistä koneoppimismallin uudelleenkoulutus

### Stoat (Revolt)
- `!unban [pelaaja]` - Listaa tai poista banneja
- `!verify [on/off/status]` - Säädä tai tarkista kaikkien viestien tarkastus
- `!c [palvelin] [komento]` - Suorita konsolikomento
- `!train` - Käynnistä koneoppimismallin uudelleenkoulutus
- `!vahvista <pelaaja> [taso]` - Vahvista moderointitoimenpide (SEVERE/MODERATE/MINOR/OK)
- `!hylkaa <pelaaja>` - Hylätä moderointitoimenpide

### Pelaajat
- `!yllapitaja [viesti]` - Lähetä avunpyyntö ylläpidolle (Discordiin)

## Vaatimukset

- Docker ja Docker Compose (Valinnainen)
- Vähintään yksi: Discord webhook/bot URL **tai** Stoat (Revolt) bot token

## Asennus

1. **Kloonaa tai kopioi projekti**:
```bash
cd /Users/mariapori/Projektit/pp2susdetector
```

2. **Luo `.env` tiedosto**:
```bash
cp .env.example .env
```

3. **Muokkaa `.env` tiedostoa** (Discord, Stoat tai molemmat):
```env
# Discord (valinnainen)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your-webhook-url
DISCORD_BOT_TOKEN=your_discord_bot_token

# Stoat / Revolt (valinnainen)
STOAT_BOT_TOKEN=your_stoat_bot_token
STOAT_CHANNEL_ID=your_stoat_channel_id
```

4. **Muokkaa `config.yaml`** (aseta käytössä olevat alustat):
```yaml
discord:
  enabled: false  # tai true

stoat:
  enabled: true   # tai false
```

5. **Käynnistä palvelut**:
```bash
docker-compose up -d
```

## Käyttö

### Käynnistä palvelut
```bash
docker-compose up -d
```

### Seuraa lokeja
```bash
# Kaikki palvelut
docker-compose logs -f

# Vain detector
docker-compose logs -f pp2detector

# Vain PP2 host
docker-compose logs -f pp2host
```

### Pysäytä palvelut
```bash
docker-compose down
```

### Rakenna uudelleen muutosten jälkeen
```bash
docker-compose up -d --build
```

## Konfiguraatio

Muokkaa `config.yaml` tiedostoa. Voit lisätä useampia palvelimia `servers`-listaan:

```yaml
servers:
  - name: "Main Server"
    chatlog_path: "/etc/pp2host/static/chatlog.txt"
    playlog_path: "/etc/pp2host/static/playlog.txt"
    banlist_path: "/etc/pp2host/static/ban.dat"
    container_name: "pp2host"
    admin_url: "http://localhost:4500/Admin.html"
    admin_user: "admin"
    admin_password: "PASSWORD"

discord:
  enabled: true    # false jos ei käytössä
  verify_all: true

stoat:
  enabled: false   # true jos käytössä
  api_url: "https://api.revolt.chat"
  ws_url: "wss://ws.revolt.chat"

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
```

## Tietokanta

Rikkomukset tallennetaan `data/violations.db` SQLite-tietokantaan. Voit tarkastella tietokantaa esim. DB Browser for SQLite -ohjelmalla.

## Ilmoitukset

Vakavat ja keskivakavat rikkomukset lähetetään konfiguroituihin alustoihin (Discord ja/tai Stoat). Ilmoitus sisältää:
- Pelaajan nimen
- IP-osoitteen
- Rikkomuksen sisällön
- ML:n perustelun
- Ehdotetun toimenpiteen
- Valmiin ban-komennon (vakavissa tapauksissa)

> **Huom:** Discordissa moderointitoimenpiteet vahvistetaan interaktiivisilla napeilla. Stoatissa käytetään tekstikomentoja (`!vahvista` / `!hylkaa`) koska Revolt ei tue interaktiivisia elementtejä.

## Kehitys

### Aja ilman Dockeria

Voit ajaa detectoria suoraan Pythonilla, vaikka PP2-hosti ei olisi Dockerissa.

1. **Huolehdi lokien sijainnista**:
   - Varmista, että detectorilla on lukuoikeus PP2-hostin `chatlog.txt` ja `playlog.txt` tiedostoihin.

2. **Asenna riippuvuudet**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Määritä asetukset**:
   - Luo `.env` tiedosto (`cp .env.example .env`) ja aseta `DISCORD_WEBHOOK_URL` jne.
   - **Tärkeää**: Aseta `ADMIN_PASSWORD` `.env` tiedostoon, sillä automaattinen salasanan haku toimii vain Dockerissa.
   - Muokkaa `config.yaml` tiedostoa ja aseta oikeat polut:
     ```yaml
     pp2:
       chatlog_path: "C:/PP2/static/chatlog.txt"  # Esimerkki Windows-polusta
       playlog_path: "C:/PP2/static/playlog.txt"
       admin_url: "http://localhost:4500/Admin.html"
     ```

4. **Käynnistä detector**:
   ```bash
   python detector.py
   ```

## Automaattinen asennus (suositeltu)

### Linux/macOS

Interaktiivinen asennusskripti joka kysyy kaikki tarvittavat asetukset ja konfiguroi systemd servicen:

```bash
# Tee skripti suoritettavaksi
chmod +x install.sh

# Suorita asennusskripti (vaatii sudo)
sudo ./install.sh
```

Skripti tekee seuraavat asiat:
- ✅ Asentaa järjestelmäriippuvuudet (Python, pip, venv, git)
- ✅ Luo `pp2` käyttäjän ja hakemistorakenteen `/opt/pp2susdetector`
- ✅ Kopioi kaikki tiedostot ja luo Python virtuaaliympäristön
- ✅ Kysyy ja tallentaa konfiguraation (Discord tokens, polut, jne.)
- ✅ Konfiguroi ja käynnistää systemd servicen

### Windows

PowerShell-asennusskripti joka asentaa Windows Servicen NSSM:n avulla:

```powershell
# Suorita PowerShell järjestelmänvalvojana
.\install.ps1

# Voit myös määrittää asennushakemiston
.\install.ps1 -InstallDir "D:\pp2susdetector"

# Ohita Windows Servicen asennus
.\install.ps1 -SkipService
```

Skripti tekee seuraavat asiat:
- ✅ Tarkistaa Python 3.10+ ja opastaa asennuksessa
- ✅ Luo hakemistorakenteen `C:\pp2susdetector` (tai määritetty polku)
- ✅ Kopioi tiedostot ja luo Python virtuaaliympäristön
- ✅ Kysyy ja tallentaa konfiguraation
- ✅ Asentaa Windows Servicen (vaatii NSSM:n)
- ✅ Luo `run.bat` manuaalista käynnistystä varten

---

## Manuaalinen Systemd-asennus (Linux)

Voit ajaa pp2susdetectoria taustalla systemd-palveluna:

### 1. Luo käyttäjä ja kopioi tiedostot

```bash
# Luo käyttäjä
sudo useradd -r -s /bin/false pp2

# Kopioi tiedostot
sudo mkdir -p /opt/pp2susdetector
sudo cp -r . /opt/pp2susdetector/
sudo chown -R pp2:pp2 /opt/pp2susdetector

# Luo virtuaaliympäristö
cd /opt/pp2susdetector
sudo -u pp2 python3 -m venv venv
sudo -u pp2 ./venv/bin/pip install -r requirements.txt
sudo -u pp2 ./venv/bin/pip install systemd-python
```

### 2. Asenna palvelu

```bash
sudo cp pp2susdetector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pp2susdetector
sudo systemctl start pp2susdetector
```

### 3. Seuraa lokeja

```bash
# Reaaliaikainen seuranta
journalctl -u pp2susdetector -f

# Viimeiset 100 riviä
journalctl -u pp2susdetector -n 100

# Vain virheet
journalctl -u pp2susdetector -p err
```

### 4. Hallinta

```bash
sudo systemctl status pp2susdetector   # Tila
sudo systemctl restart pp2susdetector  # Uudelleenkäynnistys
sudo systemctl stop pp2susdetector     # Pysäytys
```

## Tietoturva

- Discord/Stoat tokenit tallennetaan `.env` tiedostoon (ei versionhallinnassa)
- Lokitiedostot ovat read-only detectorille
- Tietokanta tallennetaan paikallisesti `data/` kansioon
