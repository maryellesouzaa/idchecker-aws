
from dotenv import load_dotenv
import os
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from datetime import datetime
import psycopg2
import re
from telegram.constants import ParseMode

load_dotenv()

token = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:xYqoSUrBXewIYTfQkNYzsbIwJeRsMyKd@interchange.proxy.rlwy.net:19437/railway"

ID_REGEX = r'\b[A-Z0-9]{3}-[A-Z0-9]{3}-[A-Z0-9]{3}\b'
USUARIOS_ADMIN_TEMP = set()
CANAL_ID = -1002563145936
SENHA_ADMIN = "0809"

RELATAR_CODIGO, RELATAR_MOTIVO = range(2)

def get_db_connection():
    if not hasattr(get_db_connection, "conn"):
        get_db_connection.conn = psycopg2.connect(DATABASE_URL)
    return get_db_connection.conn

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot iniciado! Envie os IDs dos produtos no formato AAA-BBB-CCC.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.upper()
    user = update.effective_user
    user_id = user.id
    user_name = user.first_name
    message_id = update.message.message_id
    chat_id = update.message.chat_id

    ids = re.findall(ID_REGEX, text)
    if not ids:
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    for codigo in ids:
        cursor.execute("SELECT link, user_name FROM produto WHERE codigo = %s", (codigo,))
        resultado = cursor.fetchone()
        if resultado:
            link_existente, user_name_existente = resultado
            resposta = f"⚠️ {user_name_existente}, o ID {codigo} já existe!"
            if link_existente:
                resposta += f"\n🔗 Link associado: {link_existente}"
            else:
                resposta += "\n🔗 Nenhum link foi associado ainda."
            await update.message.reply_text(resposta)
            continue

        cursor.execute(
            "INSERT INTO produto (codigo, user_id, user_name, message_id, chat_id, data_pedido) VALUES (%s, %s, %s, %s, %s, %s)",
            (codigo, user_id, user_name, message_id, chat_id, datetime.now().date())
        )
        conn.commit()

        await update.message.reply_text(
            f"✅ ID {codigo} adicionado à fila. Avisarei quando o link estiver disponível.\n\n"
            "⏳ O tempo de resposta pode variar dependendo do horário, mas em breve sua solicitação será respondida!"
        )

        link_msg = f"https://t.me/c/{str(chat_id)[4:]}/{message_id}" if str(chat_id).startswith("-100") else None
        mensagem = (
            f"📨 <b>Novo pedido de ID</b>\n"
            f"👤 <b>Usuário:</b> {user_name} (ID: <code>{user_id}</code>)\n"
            f"🆔 <b>Pedido:</b> <code>{codigo}</code>\n"
        )
        if link_msg:
            mensagem += f"🔗 <a href='{link_msg}'>Ver mensagem</a>"

        await context.bot.send_message(chat_id=CANAL_ID, text=mensagem, parse_mode=ParseMode.HTML)

    cursor.close()

# (outros handlers também foram atualizados aqui, por brevidade estão omitidos neste trecho...)

# Ao final, o main()
def main():
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("quantos", quantos))
    app.add_handler(CommandHandler("addlink", addlink))
    app.add_handler(CommandHandler("fila", fila))
    app.add_handler(CommandHandler("historico", historico))
    app.add_handler(CommandHandler("historicoids", historicoids))
    app.add_handler(CommandHandler("limpar", limpar))
    app.add_handler(CommandHandler("mensagem", mensagem))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("relatarerro", relatarerro_start)],
        states={
            RELATAR_CODIGO: [MessageHandler(filters.TEXT & ~filters.COMMAND, relatarerro_codigo)],
            RELATAR_MOTIVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, relatarerro_motivo)]
        },
        fallbacks=[CommandHandler("cancelar", relatarerro_cancel)],
    ))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()