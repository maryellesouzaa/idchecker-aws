from dotenv import load_dotenv
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import psycopg2
import re

load_dotenv()

token = os.getenv('BOT_TOKEN')

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:xYqoSUrBXewIYTfQkNYzsbIwJeRsMyKd@interchange.proxy.rlwy.net:19437/railway"

ID_REGEX = r'\b[A-Z0-9]{3}-[A-Z0-9]{3}-[A-Z0-9]{3}\b'

def get_db_connection():
    if not hasattr(get_db_connection, "conn"):
        get_db_connection.conn = psycopg2.connect(DATABASE_URL)
    return get_db_connection.conn

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.upper()
    nome_usuario = update.effective_user.first_name
    user_id = update.effective_user.id
    ids = re.findall(ID_REGEX, text)
    if not ids:
        return
    resposta = []
    for codigo in ids:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT link FROM produtos WHERE codigo = %s", (codigo,))
            resultado = cursor.fetchone()
            if resultado:
                continue
            else:
                cursor.execute(
                    "INSERT INTO produtos (codigo, user_id, user_name) VALUES (%s, %s, %s)",
                    (codigo, user_id, nome_usuario)
                )
                conn.commit()
                resposta.append(f"✅ ID {codigo} adicionado à fila. Avisarei quando o link estiver disponível.")
        except Exception:
            resposta.append(f"❌ Erro ao tentar adicionar o ID {codigo}.")
        finally:
            cursor.close()
    if resposta:
        await update.message.reply_text("\n".join(resposta))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot iniciado! Envie os IDs dos produtos no formato AAA-BBB-CCC.")

async def quantos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM produtos;")
        total = cursor.fetchone()[0]
        await update.message.reply_text(f"📊 Atualmente existem {total} IDs registrados no banco de dados!")
    except Exception:
        await update.message.reply_text("❌ Ocorreu um erro ao contar os IDs.")
    finally:
        cursor.close()

async def addlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("❌ Uso correto: /addlink CÓDIGO LINK")
            return
        codigo = args[0].upper()
        link = ' '.join(args[1:])
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM produtos WHERE codigo = %s", (codigo,))
        if cursor.fetchone():
            cursor.execute("UPDATE produtos SET link = %s WHERE codigo = %s", (link, codigo))
            conn.commit()
            await update.message.reply_text(f"✅ Link atualizado com sucesso para o ID {codigo}!")
        else:
            await update.message.reply_text(f"❌ Código {codigo} não encontrado no banco de dados.")
    except Exception:
        await update.message.reply_text("❌ Ocorreu um erro ao adicionar o link.")
    finally:
        cursor.close()

async def fila(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT codigo FROM produtos WHERE link IS NULL ORDER BY data_pedido ASC;")
        ids_pendentes = cursor.fetchall()
        if not ids_pendentes:
            await update.message.reply_text("✅ Nenhum ID pendente na fila!")
            return
        resposta = "📋 Fila de IDs pendentes:\n\n"
        for idx, (codigo,) in enumerate(ids_pendentes, start=1):
            resposta += f"{idx}. {codigo}\n"
        await update.message.reply_text(resposta)
    except Exception:
        await update.message.reply_text("❌ Ocorreu um erro ao buscar a fila.")
    finally:
        cursor.close()

async def historico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_name, user_id, codigo, data_pedido, link FROM produtos WHERE link IS NOT NULL ORDER BY data_pedido ASC;"
        )
        historico = cursor.fetchall()
        if not historico:
            await update.message.reply_text("📚 Nenhum histórico encontrado ainda.")
            return
        resposta = "📚 Histórico de todos os pedidos:\n\n"
        for idx, (user_name, user_id, codigo, data_pedido, link) in enumerate(historico, start=1):
            resposta += (
                f"{idx}. 👤 {user_name} ({user_id})\n"
                f"🆔 {codigo} — 🕒 {data_pedido.strftime('%Y-%m-%d %H:%M:%S')} — 📄 {link}\n\n"
            )
        await update.message.reply_text(resposta)
    except Exception:
        await update.message.reply_text("❌ Ocorreu um erro ao buscar o histórico.")
    finally:
        cursor.close()

def main():
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quantos", quantos))
    app.add_handler(CommandHandler("addlink", addlink))
    app.add_handler(CommandHandler("fila", fila))
    app.add_handler(CommandHandler("historico", historico))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()
