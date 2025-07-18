@echo off
echo Installing Python Libraries...

REM Install pyvisa
pip install pyvisa
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to install pyvisa
    exit /b %ERRORLEVEL%
)

REM Install gspread and oauth2client
pip install gspread oauth2client
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to install gspread and oauth2client
    exit /b %ERRORLEVEL%
)

REM Install pyserial
pip install pyserial
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to install pyserial
    exit /b %ERRORLEVEL%
)

REM Install pillow
pip install pillow
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to install pillow
    exit /b %ERRORLEVEL%
)

REM Install pygame
pip install pygame
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to install pygame
    exit /b %ERRORLEVEL%
)

REM Install mysql-connector-python
pip install mysql-connector-python
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to install pip install mysql
    exit /b %ERRORLEVEL%
)

REM Install openpyxl (for gspread compatibility with .xlsx files)
pip install openpyxl
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to install openpyxl
    exit /b %ERRORLEVEL%
)

REM Find the Python installation path
FOR /F "tokens=2 delims=:" %%I IN ('pip show pyserial ^| findstr "Location"') DO SET PyLocation=%%I
SET PyLocation=%PyLocation:~1%

echo Python Libraries installed successfully.
echo Updating system environment variables...

REM Enable the display of hidden items in File Explorer
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" /v Hidden /t REG_DWORD /d 1 /f
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" /v ShowSuperHidden /t REG_DWORD /d 1 /f

REM Add Python Scripts path to system environment variables
setx PATH "%PATH%;%PyLocation%\Scripts"

echo System environment variables updated successfully.

REM Inform user to open a new Command Prompt
echo Installations and setup finish, close this window and continue with procedure

pause
