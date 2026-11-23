@echo off
title ArtGlow - Controle de Estoque
cd /d "%~dp0"

rem Escolhe o Python: o do venv (se existir), senao "py", senao "python"
set "PY="
if exist "venv\Scripts\python.exe" set "PY=venv\Scripts\python.exe"
if not defined PY ( where py >nul 2>nul && set "PY=py" )
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY (
    echo Python nao encontrado. Instale em python.org marcando "Add Python to PATH".
    pause
    exit /b 1
)

rem Primeira vez: instala as bibliotecas que faltarem (precisa de internet)
%PY% -c "import flask, pypdf" >nul 2>nul
if errorlevel 1 (
    echo Instalando bibliotecas, aguarde...
    %PY% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Nao foi possivel instalar as bibliotecas. Verifique a internet.
        pause
        exit /b 1
    )
)

rem Abre o navegador depois de 3 segundos (tempo do servidor subir)
start "" cmd /c "timeout /t 3 >nul & start http://127.0.0.1:5000"

echo.
echo ArtGlow rodando em http://127.0.0.1:5000
echo Para encerrar o sistema, feche esta janela.
echo.
%PY% app.py
pause
