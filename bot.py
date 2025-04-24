from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import psycopg2
import re
import os

# Usa variável de ambiente DATABASE_URL (recomendado)
DATABASE_URL = os.getenv("DATABASE_URL")

# Se não tiver variável, usa a URL fixa
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:xYqoSUrBXewIYTfQkNYzsbIwJeRsMyKd@interchange.proxy.rlwy.net:19437/railway"

# Conexão com o banco
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Regex para capturar códigos tipo AAA-BBB-CCC, permitindo números
ID_REGEX = r'\b[A-Z0-9]{3}-[A-Z0-9]{3}-[A-Z0-9]{3}\b'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.upper()
    print(f"Recebido: {text}")  # ADICIONE ISSO para depuração

    # Extraímos os códigos que correspondem ao padrão
    ids = re.findall(ID_REGEX, text)
    print(f"IDs extraídos: {ids}")  # ADICIONE ISSO para depuração

    if not ids:
        await update.message.reply_text("Nenhum ID válido encontrado.")
        return

    resposta = []

    for codigo in ids:
        try:
            # Verificar se o código já existe
            cursor.execute("SELECT 1 FROM produtos WHERE codigo = %s", (codigo,))
            if cursor.fetchone():
                resposta.append(f"⚠️ ID já existente: {codigo}")
            else:
                cursor.execute("INSERT INTO produtos (codigo) VALUES (%s)", (codigo,))
                conn.commit()
                resposta.append(f"✅ Novo ID registrado: {codigo}")
        except psycopg2.errors.UniqueViolation:
            # Erro de duplicação de chave única
            conn.rollback()  # Reverte a transação
            resposta.append(f"⚠️ ID já existe: {codigo}")
        except Exception as e:
            # Captura qualquer outro erro
            conn.rollback()  # Reverte a transação
            resposta.append(f"Erro ao tentar inserir o código {codigo}: {str(e)}")

    # Envia resposta ao usuário
    await update.message.reply_text("\n".join(resposta))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot iniciado! Envie os IDs dos produtos.")

def main():
    app = ApplicationBuilder().token("7680606076:AAFVfNAKU-jP_pWb9ZGuvL1DoRu8vYMPS48").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot rodando...")
    app.run_polling()

if __name__ == '__main__':
    main()
