#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    echo "Criando ambiente Python, aguarde..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Instalando dependencias, aguarde..."
pip install -q -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "============================================================"
    echo " ATENCAO: abra o arquivo .env (nesta mesma pasta) com o"
    echo " TextEdit e cole sua chave da API da Anthropic na linha"
    echo " ANTHROPIC_API_KEY="
    echo " Depois de salvar, volte aqui e aperte Enter."
    echo "============================================================"
    read -p "Aperte Enter para continuar..."
fi

( sleep 2 && open http://localhost:8000 ) &
uvicorn app.main:app --host 0.0.0.0 --port 8000
