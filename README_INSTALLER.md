# Installer and local deployment

This project includes two ways to make the app installable on a Windows machine:

- `scripts/install_local.ps1` — a PowerShell installer that prepares a Python virtual environment, installs dependencies and creates `run_server.bat` and `run_bot.bat` launchers. Use this when you want a quick installer that runs on the target machine (requires Python installed).
- `installers/water_delivery_installer.iss` — an Inno Setup script you can compile into a single `.exe` installer. The generated installer copies the project into `Program Files\WaterDeliveryCRM`, creates Start Menu shortcuts and runs `scripts/install_local.ps1` at the end.

Steps to run using PowerShell installer (no Inno required)
1. Copy the repository to the target PC.
2. Ensure Python 3.10+ is installed and on `PATH`.
3. Open PowerShell as a normal user and run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\install_local.ps1
   ```
4. Edit `.env` in the project root and fill `TELEGRAM_BOT_TOKEN`, `ALLOWED_HOSTS` (add your local network IPs), etc.
5. Start the web server:
   ```powershell
   .\run_server.bat
   ```
   Or start the bot:
   ```powershell
   .\run_bot.bat
   ```

How to build a native installer (.exe) using Inno Setup
1. Install Inno Setup: https://jrsoftware.org/
2. Open `installers\water_delivery_installer.iss` in Inno Setup Compiler.
3. Adjust `Source` or `Excludes` if necessary, then press `Compile` to produce `dist\WaterDeliveryCRM_Installer.exe`.
4. Run the produced `.exe` on the target PC. The installer will copy files and execute `scripts\install_local.ps1` to prepare the environment.

Alternatively you can automate compilation using the included PowerShell helper:

```powershell
# Try automatic build (will search for ISCC in common locations):
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1

# Or specify the exact path to ISCC.exe:
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1 -InnoPath "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe"
```

The script will print compiler output and write the compiled installer to the `dist` folder (as configured in the .iss file).

Including a portable Python to make the installer fully autonomous
---------------------------------------------------------------
If you want the produced installer to work on a target machine that does NOT have Python installed,
provide a portable/full Python distribution inside the project before building the installer.

How to prepare the portable Python bundle (recommended approach):
1. Download a portable copy of Python (a full distribution that includes `python.exe`, `pip` and `venv`).
    - The official Windows embeddable ZIP is minimal and may lack `venv`/`pip`. For best results use a full portable distribution
       or unpack the official installer files into a folder.
2. Place the portable Python folder into the project root and name it `embedded_python` (so `embedded_python\python.exe` exists).
3. When you run `scripts\build_installer.ps1` (or compile the .iss manually), the `embedded_python` folder will be included
    in the installer and copied to the target machine.

What the installer will do with the bundled Python
- The installer copies the `embedded_python` folder into the application directory on the target machine.
- During installation `scripts\install_local.ps1` will detect `embedded_python\python.exe` and use it to create the `.venv` and
   install dependencies. This avoids requiring a system-wide Python installation on the target.

Notes and caveats
- The portable Python you include must provide `python.exe` and support `-m venv` and `-m pip` (a minimal embeddable ZIP from python.org
   may not have these). If you are unsure, test the portable Python locally by running `embedded_python\python.exe -m venv .venv`.
- Bundling a full Python increases installer size considerably. Test the produced installer on a clean Windows VM to verify behavior.

Notes and limitations
- The PowerShell installer requires Python to be installed on the target machine. Bundling Python into the installer is possible but significantly increases complexity and installer size.
- If you prefer a fully self-contained Docker-based install (recommended for multi-user local networks), use the provided `docker-compose.yml` instead.
- For production use or multi-user deployments consider using a real web server (Gunicorn/uvicorn behind nginx) and a managed Postgres instance.
