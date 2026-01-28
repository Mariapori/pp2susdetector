# PP2 Suspicious Detector

Prototyyppi hahmoteltu ja testailtu Google AntiGravityn avulla.

Sovellus joka valvoo PP2 (Pro Pilkki 2) host serverin lokia reaaliaikaisesti ja analysoi pelaajien käyttäytymistä LLM:n (OpenAI) avulla. Rikkomukset kategorisoidaan vakavuuden mukaan ja raportoidaan Discord-kanavalle.

## Ominaisuudet

- 🎣 **Reaaliaikainen valvonta**: Seuraa PP2 hostin chat- ja pelaajalokeja
- 🤖 **LLM-analyysi**: Käyttää OpenAI GPT-4o-mini -mallia rikkomusten havaitsemiseen
- 📊 **Kolme vakavuustasoa**:
  - 🚨 **SEVERE**: Vakavat rikkomukset (rasismi, sotapropaganda, epäsiveellisyys)
  - ⚠️ **MODERATE**: Keskivakavat rikkomukset (kiroilu, lokitus)
  - 📝 **MINOR**: Lievät rikkomukset (vain lokitus)
- 💬 **Discord-integraatio**: Lähettää ilmoitukset vakavista rikkomuksista
- 💾 **Tietokanta**: Tallentaa kaikki rikkomukset SQLite-tietokantaan
- 🐳 **Docker-tuki**: Helppo käyttöönotto Docker Composella

## Vaatimukset

- Docker ja Docker Compose
- OpenAI API-avain
- Discord webhook URL (valinnainen)

## Asennus

1. **Kloonaa tai kopioi projekti**:
```bash
cd /Users/mariapori/Projektit/pp2susdetector
```

2. **Luo `.env` tiedosto**:
```bash
cp .env.example .env
```

3. **Muokkaa `.env` tiedostoa**:
```env
OPENAI_API_KEY=sk-your-openai-api-key-here
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your-webhook-url
```

4. **Käynnistä palvelut**:
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

Muokkaa `config.yaml` tiedostoa:

```yaml
pp2:
  chatlog_path: "/etc/pp2host/static/chatlog.txt"
  playlog_path: "/etc/pp2host/static/playlog.txt"
  
llm:
  provider: "openai"
  model: "gpt-4o-mini"
  
discord:
  enabled: true
  
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

## Discord-ilmoitukset

Vakavat ja keskivakavat rikkomukset lähetetään Discordiin. Ilmoitus sisältää:
- Pelaajan nimen
- IP-osoitteen
- Rikkomuksen sisällön
- LLM:n perustelun
- Ehdotetun toimenpiteen
- Valmiin ban-komennon (vakavissa tapauksissa)

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
   - Luo `.env` tiedosto (`cp .env.example .env`) ja aseta `OPENAI_API_KEY`, `DISCORD_WEBHOOK_URL` jne.
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

## Tietoturva

- OpenAI API-avain ja Discord webhook URL tallennetaan `.env` tiedostoon (ei versionhallinnassa)
- Lokitiedostot ovat read-only detectorille
- Tietokanta tallennetaan paikallisesti `data/` kansioon

## Lisenssi

Tämä on henkilökohtainen projekti PP2 pelin moderointiin.

## Tekijä

Topias Mariapori
