from dotenv import load_dotenv
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
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
ADMINS = set()
CANAL_ID = -1002563145936
SENHA_ADMIN = "0809"
USUARIOS_ADMIN_TEMP = set()
CODIGO, MOTIVO = range(2)

def get_db_connection():
    if not hasattr(get_db_connection, "conn"):
        get_db_connection.conn = psycopg2.connect(DATABASE_URL)
    return get_db_connection.conn

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

        await update.message.reply_text(f"✅ ID {codigo} adicionado à fila. Avisarei quando o link estiver disponível.")

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot iniciado! Envie os IDs dos produtos no formato AAA-BBB-CCC.\n"
                                    "Comandos de ajuda:\n"
                                    "/quantos - Ver total de IDs registrados\n"
                                    "/addlink CÓDIGO LINK - Adicionar link ao código\n"
                                    "/fila - Ver IDs pendentes\n"
                                    "/historico - Ver seu histórico de pedidos\n"
                                    "Nos apoie seguindo o canal: https://t.me/cupomnavitrine")

async def quantos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in USUARIOS_ADMIN_TEMP:
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM produto;")
    total = cursor.fetchone()[0]
    await update.message.reply_text(f"📊 Atualmente existem {total} IDs registrados no banco de dados!")
    cursor.close()

async def addlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in USUARIOS_ADMIN_TEMP:
        await update.message.reply_text("❌ Você não tem permissão para usar este comando.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ Uso correto: /addlink CÓDIGO LINK")
        return

    codigo = args[0].upper()
    link = ' '.join(args[1:])

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_name, user_id, message_id, chat_id FROM produto WHERE codigo = %s", (codigo,))
    result = cursor.fetchone()

    if result:
        user_name, user_id, message_id, chat_id = result
        cursor.execute("UPDATE produto SET link = %s WHERE codigo = %s", (link, codigo))
        conn.commit()
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(f"✅ Link atualizado para {codigo}!\n"
                      f"👤 Pedido de: {user_name} ({user_id})\n"
                      f"🔗 Link: {link}"),
                reply_to_message_id=message_id
            )
        except:
            await update.message.reply_text("⚠️ Não consegui responder à mensagem original, mas o link foi atualizado.")
        await update.message.reply_text(f"✅ Link atualizado para o ID {codigo}!")
    else:
        await update.message.reply_text(f"❌ Código {codigo} não encontrado.")

    cursor.close()

async def fila(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT codigo FROM produto WHERE link IS NULL ORDER BY data_pedido ASC")
    ids_pendentes = cursor.fetchall()

    if not ids_pendentes:
        await update.message.reply_text("✅ Nenhum ID pendente!")
    else:
        resposta = "🕒 Fila de IDs pendentes:\n\n"
        for idx, (codigo,) in enumerate(ids_pendentes, start=1):
            resposta += f"{idx}. 🆔 {codigo}\n"
        resposta += "\n⏳ Aguarde a geração dos links!"
        await update.message.reply_text(resposta)

    cursor.close()

async def historico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_name, codigo, data_pedido, link FROM produto WHERE user_id = %s ORDER BY data_pedido ASC", (user_id,))
    historico = cursor.fetchall()

    if not historico:
        await update.message.reply_text("📚 Nenhum histórico encontrado.")
    else:
        resposta = "📚 Seu histórico de pedidos:\n\n"
        for idx, (user_name, codigo, data_pedido, link) in enumerate(historico, start=1):
            resposta += (
                f"{idx}. 👤 {user_name}\n"
                f"🆔 {codigo}\n"
                f"🕒 {data_pedido.strftime('%Y-%m-%d')}\n"
                f"🔗 {link}\n\n"
            )
        await update.message.reply_text(resposta)

    cursor.close()

async def historicoids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in USUARIOS_ADMIN_TEMP:
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_name, codigo, data_pedido, link FROM produto WHERE link IS NOT NULL ORDER BY data_pedido ASC")
    historico = cursor.fetchall()

    if not historico:
        await update.message.reply_text("📚 Nenhum histórico encontrado.")
    else:
        resposta = "📚 Histórico geral de pedidos:\n\n"
        for idx, (user_name, codigo, data_pedido, link) in enumerate(historico, start=1):
            resposta += (
                f"{idx}. 👤 {user_name}\n"
                f"🆔 {codigo}\n"
                f"🕒 {data_pedido.strftime('%Y-%m-%d')}\n"
                f"🔗 {link}\n\n"
            )
        await update.message.reply_text(resposta)

    cursor.close()

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1 or context.args[0] != SENHA_ADMIN:
        await update.message.reply_text("❌ Senha incorreta.")
        return

    user_id = update.effective_user.id
    USUARIOS_ADMIN_TEMP.add(user_id)
    await update.message.reply_text(
        "🔐 Acesso administrativo concedido!\n\n"
        "Comandos disponíveis:\n"
        "/quantos - Ver total de IDs registrados\n"
        "/addlink CÓDIGO LINK - Adicionar link ao código\n"
        "/fila - Ver IDs pendentes\n"
        "/historicoids - Ver histórico de todos os IDs"
    )

def main():
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quantos", quantos))
    app.add_handler(CommandHandler("addlink", addlink))
    app.add_handler(CommandHandler("fila", fila))
    app.add_handler(CommandHandler("historico", historico))
    app.add_handler(CommandHandler("historicoids", historicoids))
    app.add_handler(CommandHandler("admin", admin))

    app.run_polling()

if __name__ == '__main__':
    main()