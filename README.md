# ParkCheaper

Algorithmic parking tariff optimization and automated sequential ticket purchasing suite for PayByPhone.

---

## Overview

Municipal parking tariffs are frequently non-linear, with progressive pricing tiers, free initial quotas (such as 30 minutes free per day), and specific free time windows (including evening periods, Sundays, and public holidays).

ParkCheaper analyzes real-time tariff restrictions and rate policies for a given parking zone, computes the mathematically optimal combination of tickets using dynamic programming, and manages automated sequential renewal in the background without requiring user intervention.

Key capabilities:
- Dynamic Programming Optimizer: Computes optimal ticket duration combinations to minimize total parking cost.
- Tariff Rule and Quota Detection: Automatically accounts for complimentary daily quotas, free time windows, and maximum stay constraints.
- Background Daemon and System Tray: Runs quietly in the Windows notification area while monitoring ticket expiration.
- Standalone CLI Executable: Offers complete feature parity for terminal scripting and headless environments.
- Zero-Configuration First Launch: Does not require pre-existing configuration files. Prompts for credentials directly via the graphical interface or interactive console and stores them securely in `%APPDATA%\ParkCheaper\.env`.

---

## 1. Graphical Interface (GUI) - Recommended

The graphical workbench is the primary interface for desktop users.

### Installation on Windows

Binaries are available on the project Releases page:
- `ParkCheaper.msi` (Recommended): Windows installer package. Installs to `Program Files`, registers Start Menu and Desktop shortcuts, and handles clean updates.
- `ParkCheaper.exe`: Standalone portable executable. Requires no installation.

### First-Time Setup and Usage

1. Launch Application:
   Start ParkCheaper from the Start Menu, Desktop shortcut, or by executing `ParkCheaper.exe`.
   The application initializes a local HTTP service (`http://127.0.0.1:8000`), opens your default web browser, and registers an icon in the Windows System Tray.

2. Configure Account Credentials:
   If running for the first time without an existing configuration file, the interface detects the unauthenticated state and automatically opens the configuration drawer.
   Enter your PayByPhone phone number in international format (e.g. `33612345678`) and account password or PIN. Click Save.
   Credentials are authenticated against PayByPhone APIs and persisted locally to `%APPDATA%\ParkCheaper\.env`.

3. Optimize and Schedule Parking:
   - Navigate to the Optimizer & Checkout tab.
   - Select the target vehicle from your registered vehicles list.
   - Enter the PayByPhone parking zone code (e.g. `94802`).
   - Define your desired parking window by time range (e.g. `14:00` to `18:30`) or total duration in minutes.
   - Click Calculate Optimization. The application displays the list of recommended sequential tickets, total cost, and calculated savings compared to standard block purchases.
   - Click Start Scheduler. ParkCheaper executes the first ticket purchase immediately and monitors expiration in the background.

4. Background Operation:
   You may close your browser tab at any time. The background scheduler continues running via the System Tray process.
   To restore the web dashboard or terminate the application, right-click the ParkCheaper tray icon in the Windows taskbar.

---

## 2. Command Line Interface (CLI)

For headless servers, automated scripts, and power users, the CLI executable (`ParkCheaper-cli.exe` or `python cli.py`) provides full functional control.

### Zero-Config Interactive Setup
If credentials are not yet configured, executing any command interactively in a terminal will prompt for the phone number and password directly in the console and persist them to `%APPDATA%\ParkCheaper\.env`.

### Available Commands

#### Account Status and Active Sessions
```powershell
ParkCheaper-cli.exe status --zone 94802
```
Displays account details, registered vehicles, active payment methods, and current parking ticket status.

#### Calculate Tariff Optimization
```powershell
# Optimize by duration (in minutes):
ParkCheaper-cli.exe optimize --zone 94802 --duration 210

# Optimize by time window (for the current day):
ParkCheaper-cli.exe optimize --zone 94802 --start 14:00 --end 17:30
```

#### Purchase an Immediate Ticket
```powershell
ParkCheaper-cli.exe buy --zone 94802 --duration 15
```

#### Execute Sequential Scheduler
```powershell
ParkCheaper-cli.exe schedule --zone 94802 --tickets 30,90,90
```
Purchases the first ticket (30 min), waits for expiration, and automatically buys subsequent tickets (90 min, then 90 min). Can be terminated safely at any time using `Ctrl+C`.

---

## 3. Building from Source

### Prerequisites
- Python 3.11 or higher
- Node.js 20 or higher (with npm)

### Setup
```powershell
git clone https://github.com/Timothee-Robin/PaybyPhoneBuyer.git
cd PaybyPhoneBuyer

pip install -r requirements.txt

cd frontend
npm install
cd ..
```

### Local Development
```powershell
.\start.ps1
```

### Build Standalone Executables and MSI
```powershell
.\build_installer.ps1
```

---

## 4. Security and Credential Storage

- No Intermediate Servers: All network communications occur directly between the client machine and official PayByPhone HTTPS API endpoints.
- Local Storage: Credentials and preferences are stored exclusively on the host system within `%APPDATA%\ParkCheaper\.env` (with backward compatibility for `%APPDATA%\PaybyPhoneBuyer\.env`).

---

## 5. License and Legal Disclaimer

### License
This project is licensed under the MIT License. See [installer/license.rtf](installer/license.rtf) for terms and conditions.

### Legal Disclaimer
ParkCheaper is an independent, open-source project developed for educational and personal workflow efficiency. It is neither affiliated with, supported by, nor endorsed by PayByPhone Technologies Inc. Users remain solely responsible for ensuring compliance with PayByPhone terms of service and municipal parking regulations.
