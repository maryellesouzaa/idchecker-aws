#!/bin/bash

echo "🔧 Iniciando setup do bot..."

if [ ! -d "venv" ]; then
    echo "📦 Criando ambiente virtual..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "📥 Instalando dependências..."
pip install -r requirements.txt

echo "🚀 Iniciando o bot com nohup..."
nohup python bot.py > bot.log 2>&1 &

echo "✅ Bot rodando em background! Verifique com: tail -f bot.log"
