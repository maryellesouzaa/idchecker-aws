from telegram import Update, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler
import datetime

# Dados temporários em memória
usuarios_autorizados_temporariamente = set()
historico_mensagens = {}
RELATAR_CODIGO, RELATAR_MOTIVO = range(2)
mensagem_temp = {}

ADMIN_PASSWORD = "0809"
CANAL_DESTINO_ID = "@nomedoseucanal"

# Mensagem de boas-vindas
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user
    mensagem = (
        f"👋 Olá, {usuario.first_name}!\n\n"
        "Sou um assistente de suporte. Você pode me enviar sua dúvida ou pedido diretamente aqui.\n\n"
        "📌 *Comandos disponíveis:*\n"
        "/relatarerro – Relate um erro com código e motivo\n"
        "/historico – Veja seus pedidos anteriores\n"
        "/admin 0809 – Acesso administrativo\n"
        "/mensagem – Enviar mensagem como admin ao canal\n"
        "/historicoids – Ver histórico de todos os usuários (admin)\n\n"
        "✅ Nos apoie seguindo o canal: https://t.me/cupomnavitrine"
    )
    await update.message.reply_text(mensagem, parse_mode="Markdown")

# ADMIN - libera acesso temporário a qualquer pessoa com a senha correta
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        senha = context.args[0]
        if senha == ADMIN_PASSWORD:
            usuarios_autorizados_temporariamente.add(update.effective_user.id)
            await update.message.reply_text("✅ Acesso administrativo concedido temporariamente.")
        else:
            await update.message.reply_text("❌ Senha incorreta.")
    except:
        await update.message.reply_text("⚠️ Use `/admin <senha>`.", parse_mode="Markdown")

# COMANDO /mensagem - apenas para autorizados temporariamente
async def mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in usuarios_autorizados_temporariamente:
        await update.message.reply_text("⛔ Você não tem permissão para usar este comando.")
        return
    if context.args:
        texto = " ".join(context.args)
        await context.bot.send_message(chat_id=CANAL_DESTINO_ID, text=f"📢 Mensagem Administrativa:\n\n{texto}")
        await update.message.reply_text("✅ Mensagem enviada ao canal.")
    else:
        await update.message.reply_text("⚠️ Use: /mensagem <sua mensagem>")

# COMANDO /relatarerro
async def relatarerro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛠️ Por favor, envie o *código do erro*.", parse_mode="Markdown")
    return RELATAR_CODIGO

async def receber_codigo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["codigo_erro"] = update.message.text
    await update.message.reply_text("✏️ Agora envie o *motivo* ou descrição do erro.", parse_mode="Markdown")
    return RELATAR_MOTIVO

async def receber_motivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    codigo = context.user_data.get("codigo_erro")
    motivo = update.message.text
    usuario = update.effective_user

    mensagem = (
        f"🚨 *Erro relatado por:* @{usuario.username or usuario.first_name}\n"
        f"🧾 *Código:* `{codigo}`\n"
        f"📄 *Motivo:* {motivo}"
    )

    await context.bot.send_message(chat_id=CANAL_DESTINO_ID, text=mensagem, parse_mode="Markdown")
    await update.message.reply_text("✅ Obrigado! Seu erro foi relatado com sucesso.")
    return ConversationHandler.END

async def cancelar_relato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Relato cancelado.")
    return ConversationHandler.END

# COMANDO /historico - exibe apenas para o próprio usuário
async def historico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mensagens = historico_mensagens.get(user_id, [])
    if not mensagens:
        await update.message.reply_text("📭 Você ainda não enviou nenhuma mensagem.")
        return
    resposta = "📜 *Seu histórico:*\n\n"
    for item in mensagens[-10:]:
        resposta += f"🕒 {item['hora']}:\n{item['texto']}\n\n"
    await update.message.reply_text(resposta, parse_mode="Markdown")

# COMANDO /historicoids - exibe histórico geral (admin temporário)
async def historicoids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in usuarios_autorizados_temporariamente:
        await update.message.reply_text("⛔ Acesso negado.")
        return
    if not historico_mensagens:
        await update.message.reply_text("📭 Nenhuma mensagem registrada.")
        return
    resposta = "📊 *Histórico geral de mensagens:*\n\n"
    for uid, mensagens in historico_mensagens.items():
        resposta += f"👤 ID {uid}:\n"
        for m in mensagens[-3:]:
            resposta += f"  🕒 {m['hora']}: {m['texto']}\n"
        resposta += "\n"
    await update.message.reply_text(resposta, parse_mode="Markdown")

# Salvando mensagens automaticamente
async def salvar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    texto = update.message.text
    agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    historico_mensagens.setdefault(user_id, []).append({"texto": texto, "hora": agora})
    await update.message.reply_text("✅ Pedido recebido. Entraremos em contato.")

# INICIALIZADOR
if __name__ == '__main__':
    app = ApplicationBuilder().token("SEU_TOKEN_AQUI").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("mensagem", mensagem))
    app.add_handler(CommandHandler("historico", historico))
    app.add_handler(CommandHandler("historicoids", historicoids))

    relatar_handler = ConversationHandler(
        entry_points=[CommandHandler("relatarerro", relatarerro)],
        states={
            RELATAR_CODIGO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_codigo)],
            RELATAR_MOTIVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_motivo)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_relato)],
        conversation_timeout=120,  # 2 minutos
    )
    app.add_handler(relatar_handler)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, salvar_mensagem))

    print("✅ Bot iniciado com sucesso.")
    app.run_polling()

if __name__ == '__main__':
    main()