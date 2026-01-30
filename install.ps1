# PP2SusDetector - Windows asennusskripti (PowerShell)
# Asentaa kaikki tarvittavat riippuvuudet ja konfiguroi Windows Service
#
# Suorita: .\install.ps1
# Vaatii: PowerShell 5.1+ ja järjestelmänvalvojan oikeudet

#Requires -RunAsAdministrator

param(
    [string]$InstallDir = "C:\pp2susdetector",
    [switch]$SkipService
)

$ErrorActionPreference = "Stop"
$ServiceName = "PP2SusDetector"

# Värit
function Write-Header {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║           PP2SusDetector - Windows Asennus                   ║" -ForegroundColor Cyan
    Write-Host "║        Chat moderation with Machine Learning                 ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host "[✓] $Message" -ForegroundColor Green
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "[!] $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[✗] $Message" -ForegroundColor Red
}

function Test-PythonInstalled {
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 10) {
                Write-Step "Python löydetty: $pythonVersion"
                return $true
            }
        }
    } catch {}
    
    # Kokeile py launcher
    try {
        $pythonVersion = py -3 --version 2>&1
        if ($pythonVersion -match "Python 3") {
            Write-Step "Python löydetty (py launcher): $pythonVersion"
            return $true
        }
    } catch {}
    
    return $false
}

function Install-Python {
    Write-Warning-Custom "Python 3.10+ ei ole asennettu."
    Write-Host ""
    Write-Host "Asenna Python:" -ForegroundColor Yellow
    Write-Host "  1. Lataa: https://www.python.org/downloads/"
    Write-Host "  2. Varmista 'Add Python to PATH' on valittuna asennuksessa"
    Write-Host "  3. Suorita tämä skripti uudelleen"
    Write-Host ""
    
    $installNow = Read-Host "Haluatko avata Python-lataussivun nyt? (k/e)"
    if ($installNow -eq "k" -or $installNow -eq "K") {
        Start-Process "https://www.python.org/downloads/"
    }
    
    exit 1
}

function Get-PythonCommand {
    # Etsi toimiva Python-komento
    try {
        python --version 2>&1 | Out-Null
        return "python"
    } catch {}
    
    try {
        py -3 --version 2>&1 | Out-Null
        return "py -3"
    } catch {}
    
    return $null
}

function New-Directories {
    Write-Step "Luodaan hakemistorakenne: $InstallDir"
    
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    New-Item -ItemType Directory -Path "$InstallDir\data" -Force | Out-Null
    New-Item -ItemType Directory -Path "$InstallDir\models" -Force | Out-Null
    New-Item -ItemType Directory -Path "$InstallDir\logs" -Force | Out-Null
}

function Copy-ProjectFiles {
    Write-Step "Kopioidaan tiedostot..."
    
    $SourceDir = $PSScriptRoot
    
    # Kopioi Python-tiedostot
    Get-ChildItem -Path $SourceDir -Filter "*.py" | Copy-Item -Destination $InstallDir -Force
    
    # Kopioi muut tiedostot
    if (Test-Path "$SourceDir\requirements.txt") {
        Copy-Item "$SourceDir\requirements.txt" -Destination $InstallDir -Force
    }
    if (Test-Path "$SourceDir\pp2_rules.txt") {
        Copy-Item "$SourceDir\pp2_rules.txt" -Destination $InstallDir -Force
    }
    
    # Kopioi data ja models
    if (Test-Path "$SourceDir\data") {
        Copy-Item "$SourceDir\data\*" -Destination "$InstallDir\data\" -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path "$SourceDir\models") {
        Copy-Item "$SourceDir\models\*" -Destination "$InstallDir\models\" -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    Write-Step "Tiedostot kopioitu"
}

function New-VirtualEnvironment {
    Write-Step "Luodaan Python virtuaaliympäristö..."
    
    $pythonCmd = Get-PythonCommand
    
    Push-Location $InstallDir
    try {
        # Luo venv
        & cmd /c "$pythonCmd -m venv venv"
        
        # Aktivoi ja asenna riippuvuudet
        & "$InstallDir\venv\Scripts\python.exe" -m pip install --upgrade pip -q
        & "$InstallDir\venv\Scripts\pip.exe" install -r requirements.txt -q
        
        Write-Step "Python-riippuvuudet asennettu"
    } finally {
        Pop-Location
    }
}

function Set-EnvironmentConfig {
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "             YMPÄRISTÖMUUTTUJIEN KONFIGUROINTI                   " -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    
    $EnvFile = "$InstallDir\.env"
    
    # Discord Bot Token
    Write-Host "Discord Bot Token" -ForegroundColor Yellow
    Write-Host "Saat tämän Discord Developer Portalista (https://discord.com/developers/applications)"
    $DiscordBotToken = Read-Host "DISCORD_BOT_TOKEN"
    
    # Discord Webhook URL
    Write-Host ""
    Write-Host "Discord Webhook URL" -ForegroundColor Yellow
    Write-Host "Luo webhook Discord-palvelimellesi kanava-asetuksista"
    $DiscordWebhookUrl = Read-Host "DISCORD_WEBHOOK_URL"
    
    # Admin Password
    Write-Host ""
    Write-Host "PP2 Admin Password" -ForegroundColor Yellow
    Write-Host "(Jätä tyhjäksi jos haet Dockerista automaattisesti)"
    $AdminPassword = Read-Host "ADMIN_PASSWORD" -AsSecureString
    $AdminPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($AdminPassword))
    
    # Kirjoita .env tiedosto
    $envContent = @"
# PP2SusDetector Environment Configuration
# Luotu: $(Get-Date)

# Discord Bot Token (Vaaditaan)
DISCORD_BOT_TOKEN=$DiscordBotToken

# Discord Webhook URL (Vaaditaan)
DISCORD_WEBHOOK_URL=$DiscordWebhookUrl

# PP2 Admin Password (Valinnainen - jos tyhjä, haetaan Dockerista)
ADMIN_PASSWORD=$AdminPasswordPlain

# ML Model Path (Oletusarvo)
ML_MODEL_PATH=models/violation_model.joblib
"@

    Set-Content -Path $EnvFile -Value $envContent -Encoding UTF8
    Write-Step ".env tiedosto luotu: $EnvFile"
}

function Set-YamlConfig {
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "               CONFIG.YAML KONFIGUROINTI                         " -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    
    $ConfigFile = "$InstallDir\config.yaml"
    
    # Chatlog Path
    Write-Host "PP2 Chatlog polku" -ForegroundColor Yellow
    Write-Host "Polku chatlog.txt tiedostoon Windowsissa (esim. C:\PP2\static\chatlog.txt)"
    $defaultChatlog = "C:\PP2\static\chatlog.txt"
    $chatlogInput = Read-Host "chatlog_path [$defaultChatlog]"
    $ChatlogPath = if ($chatlogInput) { $chatlogInput } else { $defaultChatlog }
    
    # Playlog Path
    Write-Host ""
    Write-Host "PP2 Playlog polku" -ForegroundColor Yellow
    $defaultPlaylog = "C:\PP2\static\playlog.txt"
    $playlogInput = Read-Host "playlog_path [$defaultPlaylog]"
    $PlaylogPath = if ($playlogInput) { $playlogInput } else { $defaultPlaylog }
    
    # Container Name
    Write-Host ""
    Write-Host "PP2Host Docker Container nimi" -ForegroundColor Yellow
    Write-Host "(Jätä tyhjäksi jos et käytä Dockeria)"
    $containerInput = Read-Host "container_name [pp2host]"
    $ContainerName = if ($containerInput) { $containerInput } else { "pp2host" }
    
    # Admin URL
    Write-Host ""
    Write-Host "PP2 Admin Panel URL" -ForegroundColor Yellow
    $defaultAdminUrl = "http://localhost:4500/Admin.html"
    $adminUrlInput = Read-Host "admin_url [$defaultAdminUrl]"
    $AdminUrl = if ($adminUrlInput) { $adminUrlInput } else { $defaultAdminUrl }
    
    # Discord verify_all
    Write-Host ""
    Write-Host "Tarkista kaikki viestit Discordissa?" -ForegroundColor Yellow
    $verifyInput = Read-Host "verify_all (true/false) [true]"
    $VerifyAll = if ($verifyInput) { $verifyInput } else { "true" }
    
    # Banlist Path
    Write-Host ""
    Write-Host "PP2 Banlist polku" -ForegroundColor Yellow
    $defaultBanlist = "C:\PP2\static\ban.dat"
    $banlistInput = Read-Host "banlist_path [$defaultBanlist]"
    $BanlistPath = if ($banlistInput) { $banlistInput } else { $defaultBanlist }

    $yamlContent = @"
# PP2SusDetector Configuration
# Luotu: $(Get-Date)

# Palvelimien asetukset
servers:
  - name: "Main Server"
    chatlog_path: "$ChatlogPath"
    playlog_path: "$PlaylogPath"
    banlist_path: "$BanlistPath"
    container_name: "$ContainerName"
    admin_url: "$AdminUrl"
    admin_user: "admin"
    admin_password: "$AdminPasswordPlain"

ml:
  model_path: "models/violation_model.joblib"

discord:
  enabled: true
  verify_all: $VerifyAll

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
"@

    Set-Content -Path $ConfigFile -Value $yamlContent -Encoding UTF8
    Write-Step "config.yaml luotu: $ConfigFile"
}

function Install-WindowsService {
    if ($SkipService) {
        Write-Warning-Custom "Windows Service ohitettu (-SkipService)"
        return
    }
    
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "               WINDOWS SERVICE KONFIGUROINTI                     " -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    
    $installService = Read-Host "Haluatko asentaa Windows Servicen? (k/e) [k]"
    if ($installService -eq "e" -or $installService -eq "E") {
        Write-Warning-Custom "Windows Service ohitettu"
        return
    }
    
    # Tarkista onko NSSM asennettu
    $nssmPath = Get-Command nssm -ErrorAction SilentlyContinue
    
    if (-not $nssmPath) {
        Write-Warning-Custom "NSSM (Non-Sucking Service Manager) ei ole asennettu."
        Write-Host ""
        Write-Host "Windows Service vaatii NSSM:n:" -ForegroundColor Yellow
        Write-Host "  1. Asenna Chocolatey: https://chocolatey.org/install"
        Write-Host "  2. Suorita: choco install nssm"
        Write-Host "  TAI"
        Write-Host "  Lataa manuaalisesti: https://nssm.cc/download"
        Write-Host ""
        
        $installNssm = Read-Host "Haluatko asentaa NSSM:n Chocolateyllä nyt? (vaatii Chocolateyn) (k/e)"
        if ($installNssm -eq "k" -or $installNssm -eq "K") {
            try {
                choco install nssm -y
                $nssmPath = "nssm"
            } catch {
                Write-Error-Custom "NSSM:n asennus epäonnistui. Asenna manuaalisesti."
                return
            }
        } else {
            Write-Warning-Custom "Windows Service ohitettu (NSSM puuttuu)"
            Create-BatchRunner  # Luo .bat tiedosto manuaalista käynnistystä varten
            return
        }
    }
    
    # Poista vanha service jos on
    $existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($existingService) {
        Write-Warning-Custom "Vanha service löydetty, poistetaan..."
        nssm stop $ServiceName 2>$null
        nssm remove $ServiceName confirm 2>$null
    }
    
    # Asenna service
    $pythonExe = "$InstallDir\venv\Scripts\python.exe"
    $scriptPath = "$InstallDir\detector.py"
    
    nssm install $ServiceName $pythonExe $scriptPath
    nssm set $ServiceName AppDirectory $InstallDir
    nssm set $ServiceName DisplayName "PP2 Suspicious Detector"
    nssm set $ServiceName Description "Chat moderation with Machine Learning"
    nssm set $ServiceName Start SERVICE_AUTO_START
    nssm set $ServiceName AppStdout "$InstallDir\logs\stdout.log"
    nssm set $ServiceName AppStderr "$InstallDir\logs\stderr.log"
    nssm set $ServiceName AppRotateFiles 1
    nssm set $ServiceName AppRotateBytes 10485760
    
    Write-Step "Windows Service asennettu: $ServiceName"
    
    $startNow = Read-Host "Haluatko käynnistää servicen nyt? (k/e) [k]"
    if ($startNow -ne "e" -and $startNow -ne "E") {
        nssm start $ServiceName
        Write-Step "Service käynnistetty"
        
        Write-Host ""
        Write-Host "Service status:" -ForegroundColor Green
        Get-Service -Name $ServiceName | Format-Table Name, Status, StartType
    } else {
        Write-Step "Service on valmis, käynnistä: nssm start $ServiceName"
    }
}

function Create-BatchRunner {
    $batchFile = "$InstallDir\run.bat"
    
    $batchContent = @"
@echo off
title PP2SusDetector
echo Starting PP2SusDetector...
cd /d "$InstallDir"
call venv\Scripts\activate.bat
python detector.py
pause
"@

    Set-Content -Path $batchFile -Value $batchContent -Encoding ASCII
    Write-Step "Käynnistysskripti luotu: $batchFile"
}

function Show-Completion {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║               ASENNUS VALMIS!                                ║" -ForegroundColor Green
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "Asennushakemisto: " -NoNewline
    Write-Host $InstallDir -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Hyödyllisiä komentoja:" -ForegroundColor Yellow
    Write-Host "  nssm status $ServiceName          - Tarkista status"
    Write-Host "  nssm restart $ServiceName         - Käynnistä uudelleen"
    Write-Host "  Get-Content $InstallDir\logs\stdout.log -Tail 50  - Katso lokeja"
    Write-Host "  $InstallDir\run.bat               - Suorita manuaalisesti"
    Write-Host ""
    Write-Host "Konfiguraatiotiedostot:" -ForegroundColor Yellow
    Write-Host "  $InstallDir\.env          - Ympäristömuuttujat (salaiset)"
    Write-Host "  $InstallDir\config.yaml   - Sovelluskonfiguraatio"
    Write-Host ""
}

# Pääohjelma
function Main {
    Write-Header
    
    if (-not (Test-PythonInstalled)) {
        Install-Python
    }
    
    Write-Host ""
    $continue = Read-Host "Jatketaanko asennusta hakemistoon $InstallDir ? (k/e)"
    if ($continue -ne "k" -and $continue -ne "K") {
        Write-Host "Asennus peruttu."
        exit 0
    }
    
    Write-Host ""
    New-Directories
    Copy-ProjectFiles
    New-VirtualEnvironment
    Set-EnvironmentConfig
    Set-YamlConfig
    Create-BatchRunner
    Install-WindowsService
    Show-Completion
}

Main
