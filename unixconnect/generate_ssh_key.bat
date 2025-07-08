@echo off
setlocal

:: === Configuration ===
set KEY_NAME=bob_id_rsa
set KEY_COMMENT="bob@your.server.com"
set KEY_DIR=%USERPROFILE%\.ssh
set KEY_PATH=%KEY_DIR%\%KEY_NAME%

:: === Create .ssh directory if not exists ===
if not exist "%KEY_DIR%" (
    mkdir "%KEY_DIR%"
)

:: === Generate SSH key ===
echo Generating SSH key: %KEY_NAME%
ssh-keygen -t rsa -b 4096 -C %KEY_COMMENT% -f "%KEY_PATH%" -N ""

:: === Set permissions ===
echo Securing private key file...
icacls "%KEY_PATH%" /inheritance:r /grant:r "%USERNAME%:R"

:: === Done ===
echo.
echo ✅ SSH key created!
echo 📌 Private key: %KEY_PATH%
echo 📎 Public key:  %KEY_PATH%.pub
echo.
echo You can now copy the public key to your server using:
echo.
echo   type "%KEY_PATH%.pub"
echo.
pause