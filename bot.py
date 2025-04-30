from dotenv import load_dotenv
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
import psycopg2
import re
from telegram.constants import ParseMode

# Carrega variáveis de ambiente
load_dotenv()
token = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:xYqoSUrBXewIYTfQkNYzsbIwJeRsMyKd@interchange.proxy.rlwy.net:19437/railway"

ID_REGEX = r'\b[A-Z0-9]{3}-[A-Z0-9]{3}-[A-Z0-9]{3}\b'
ADMINS = [2132935211, 6294708048]
CANAL_ID = -1002563145936

admins_autenticados = set()
SENHA_ADMIN = "0809"

def get_db_connection():
    if not hasattr(get_db_connection, "conn"):
        get_db_connection.conn = psycopg2.connect(DATABASE_URL)
    return get_db_connection.conn

# Comando /admin
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ADMINS:
        await update.message.reply_text("❌ Você não está autorizado a usar comandos administrativos.")
        return

    if context.args:
        senha = context.args[0]
        if senha == SENHA_ADMIN:
            admins_autenticados.add(user_id)
            await update.message.reply_text(
                "✅ Acesso concedido!\n\n"
                "📋 Comandos administrativos:\n"
                "/limpar - Remove todos os IDs pendentes\n"
                "/quantos - Mostra a quantidade total de IDs\n"
                "/historicoids - Mostra o histórico completo de todos os IDs"
            )
        else:
            await update.message.reply_text("❌ Senha incorreta.")
    else:
        await update.message.reply_text("🔐 Digite a senha: `/admin 0809`", parse_mode=ParseMode.MARKDOWN)

# Comando /limpar
async def limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admins_autenticados:
        await update.message.reply_text("❌ Você precisa se autenticar com /admin.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM produto WHERE link IS NULL")
    deletados = cursor.rowcount
    conn.commit()
    cursor.close()

    await update.message.reply_text(f"🧹 {deletados} IDs pendentes foram removidos com sucesso.")

# Comando /quantos
async def quantos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admins_autenticados:
        await update.message.reply_text("❌ Você precisa se autenticar com /admin.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM produto;")
    total = cursor.fetchone()[0]
    cursor.close()

    await update.message.reply_text(f"📊 Atualmente existem {total} IDs registrados no banco de dados!")

# Comando /historicoids
async def historicoids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admins_autenticados:
        await update.message.reply_text("❌ Você precisa se autenticar com /admin.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, user_name, user_id, data_pedido, link FROM produto WHERE link IS NOT NULL ORDER BY data_pedido ASC")
    historico = cursor.fetchall()
    cursor.close()

    if not historico:
        await update.message.reply_text("📚 Nenhum histórico disponível.")
        return

    resposta = "📚 Histórico completo:\n\n"
    for idx, (codigo, user_name, user_id, data_pedido, link) in enumerate(historico, start=1):
        resposta += (
            f"{idx}. 🆔 {codigo}\n"
            f"👤 {user_name} ({user_id})\n"
            f"🗓 {data_pedido.strftime('%Y-%m-%d')}\n"
            f"🔗 {link}\n\n"
        )

    for i in range(0, len(resposta), 4000):
        await update.message.reply_text(resposta[i:i+4000])

# Demais comandos mantidos como estavam
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot iniciado! Envie os IDs dos produtos no formato AAA-BBB-CCC.")

async def addlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMINS:
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
                text=(f"✅ Link atualizado para {codigo}!\n👤 Pedido de: {user_name} ({user_id})\n🔗 Link: {link}"),
                reply_to_message_id=message_id
            )
        except Exception:
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
    cursor.close()

    if not ids_pendentes:
        await update.message.reply_text("✅ Nenhum ID pendente!")
    else:
        resposta = "🕒 Fila de IDs pendentes:\n\n"
        for idx, (codigo,) in enumerate(ids_pendentes, start=1):
            resposta += f"{idx}. 🆔 {codigo}\n"
        resposta += "\n⏳ Aguarde a geração dos links!"
        await update.message.reply_text(resposta)

async def historico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, data_pedido, link FROM produto WHERE user_id = %s AND link IS NOT NULL ORDER BY data_pedido ASC", (user.id,))
    historico = cursor.fetchall()
    cursor.close()

    if not historico:
        await update.message.reply_text("📚 Você ainda não possui histórico de pedidos concluídos.")
    else:
        resposta = "📚 Seu histórico de pedidos:\n\n"
        for idx, (codigo, data_pedido, link) in enumerate(historico, start=1):
            resposta += f"{idx}. 🆔 {codigo}\n🕒 {data_pedido.strftime('%Y-%m-%d')}\n🔗 {link}\n\n"
        await update.message.reply_text(resposta)

# Mensagem automática
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
            resposta += f"\n🔗 Link associado: {link_existente or 'Nenhum link foi associado ainda.'}"
            await update.message.reply_text(resposta)
            continue

        cursor.execute("INSERT INTO produto (codigo, user_id, user_name, message_id, chat_id, data_pedido) VALUES (%s, %s, %s, %s, %s, %s)", 
                       (codigo, user_id, user_name, message_id, chat_id, datetime.now().date()))
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

# Main
def main():
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("limpar", limpar))
    app.add_handler(CommandHandler("quantos", quantos))
    app.add_handler(CommandHandler("addlink", addlink))
    app.add_handler(CommandHandler("fila", fila))
    app.add_handler(CommandHandler("historico", historico))
    app.add_handler(CommandHandler("historicoids", historicoids))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == '__main__':
    main()
