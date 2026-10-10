@echo off
chcp 65001 >nul
echo === Instalando o JARVIS ===
where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale o Python 3.11 ou 3.12 em python.org e marque "Add to PATH".
  pause
  exit /b 1
)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env >nul
echo.
echo Vou abrir o arquivo .env: cole sua chave ANTHROPIC_API_KEY e salve.
notepad .env
echo.
echo Pronto! Agora de dois cliques em iniciar.bat
pause
