@echo off
cd /d "%~dp0"

if not exist .venv (
    echo Criando ambiente Python, aguarde...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Instalando dependencias, aguarde...
pip install -q -r requirements.txt

if not exist .env (
    copy .env.example .env
    echo.
    echo ============================================================
    echo  ATENCAO: abra o arquivo .env (nesta mesma pasta) com o
    echo  Bloco de Notas e cole sua chave da API da Anthropic na
    echo  linha ANTHROPIC_API_KEY=
    echo  Depois de salvar, volte aqui e aperte uma tecla.
    echo ============================================================
    pause
)

start http://localhost:8000
uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
