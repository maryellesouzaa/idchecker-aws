from dotenv import load_dotenv
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import psycopg2
import re
from psycopg2 import errors

load_dotenv()

token = os.getenv('BOT_TOKEN')
if not token:
    print("Erro: O token do bot não foi carregado corretamente.")

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
    
    ids = re.findall(ID_REGEX, text)

    if not ids:
        await update.message.reply_text("❌ Nenhum ID válido encontrado. Por favor, envie no formato AAA-BBB-CCC.")
        return

    resposta = []

    for codigo in ids:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT link FROM produtos WHERE codigo = %s", (codigo,))
            resultado = cursor.fetchone()

            if resultado:
                link = resultado[0] if resultado[0] else "Link não registrado ainda."
                resposta.append(f"⚠️ {nome_usuario}, o ID {codigo} já existe!\n🔗 Link associado: {link}")
            else:
                cursor.execute("INSERT INTO produtos (codigo) VALUES (%s)", (codigo,))
                conn.commit()
                resposta.append(f"✅ {nome_usuario}, novo ID registrado com sucesso: {codigo}")

        except errors.UniqueViolation:
            resposta.append(f"⚠️ {nome_usuario}, o ID {codigo} já existe! 🔗 Link: [desconhecido]")

        except Exception as e:
            resposta.append(f"❌ Erro ao tentar inserir o código {codigo}. Por favor, tente novamente.")
        
        finally:
            cursor.close()

    await update.message.reply_text("\n\n".join(resposta))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot iniciado! Envie os IDs dos produtos no formato AAA-BBB-CCC.")

async def quantos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM produtos;")
        total = cursor.fetchone()[0]
        await update.message.reply_text(f"📊 Atualmente existem {total} IDs registrados no banco de dados!")

    except Exception as e:
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

    except Exception as e:
        await update.message.reply_text("❌ Ocorreu um erro ao adicionar o link.")
    
    finally:
        cursor.close()

def main():
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quantos", quantos))
    app.add_handler(CommandHandler("addlink", addlink))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot rodando...")
    app.run_polling()

if __name__ == '__main__':
    main()
