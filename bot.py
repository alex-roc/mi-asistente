"""Tu asistente en Telegram.

En tu equipo (polling: el bot pregunta a Telegram cada poco si hay mensajes):
    uv run python bot.py
En Render (webhook: Telegram avisa a tu URL cuando llega un mensaje), el mismo archivo se da cuenta
solo porque Render define RENDER_EXTERNAL_URL.
"""

import hashlib
import os

from asistente import Respuesta, decidir, responder
from pydantic_ai.exceptions import ModelAPIError
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
if not TOKEN:
    raise SystemExit("Falta TELEGRAM_TOKEN: créalo con @BotFather y ponlo en .env (o en Environment, en Render).")


def permitidos() -> set[str]:
    """Los chats que pueden hablar con el bot (TELEGRAM_PERMITIDOS=123,456). Vacío = nadie."""
    return {c.strip() for c in os.getenv("TELEGRAM_PERMITIDOS", "").split(",") if c.strip()}


def texto_de(respuesta: Respuesta) -> str:
    texto = "\n".join([respuesta.texto, *respuesta.pendiente, "Responde /si o /no."]) if respuesta.pendiente else respuesta.texto
    return texto[:4000]  # Telegram no acepta mensajes de más de 4096 caracteres


async def inicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start: lo primero que manda Telegram. Dice el número de chat para añadirlo a la lista."""
    chat = str(update.effective_chat.id)
    if chat in permitidos():
        await update.message.reply_text("¡Hola! Ya puedes escribirme.")
    else:
        await update.message.reply_text(f"Tu número de chat es {chat}. Pídele al dueño del bot que lo añada.")


async def mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = str(update.effective_chat.id)
    if chat not in permitidos():  # se rechaza ANTES de llamar al modelo (y de gastar cuota)
        print(f"Chat no autorizado: {chat}", flush=True)
        await update.message.reply_text(f"No autorizado. Tu chat es {chat}: pídele al dueño que lo añada.")
        return
    try:
        respuesta = await responder(f"tg{chat}", update.message.text)  # un chat = una persona = una memoria
    except ModelAPIError as error:  # cuota agotada (429), modelo caído o lento
        print("El modelo no respondió:", str(error)[:200], flush=True)
        await update.message.reply_text("El modelo no respondió. Intenta de nuevo en un minuto.")
        return
    await update.message.reply_text(texto_de(respuesta))


async def si_o_no(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = str(update.effective_chat.id)
    if chat not in permitidos():
        return
    try:
        respuesta = await decidir(f"tg{chat}", aprobar=update.message.text.startswith("/si"))
    except ModelAPIError:
        await update.message.reply_text("El modelo no respondió. Intenta de nuevo en un minuto.")
        return
    await update.message.reply_text(texto_de(respuesta))


def main() -> None:
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", inicio))
    app.add_handler(CommandHandler(["si", "no"], si_o_no))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje))

    url = os.getenv("RENDER_EXTERNAL_URL")  # solo existe en Render
    if url:
        print(f"Webhook en {url}/telegram · permitidos: {sorted(permitidos()) or 'nadie'}", flush=True)
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv("PORT", "10000")),  # Render dice en qué puerto escuchar
            url_path="telegram",
            webhook_url=f"{url}/telegram",
            # Telegram manda este secreto en cada aviso: así nadie más puede hacerse pasar por Telegram.
            # Sale del token (que solo tú tienes); TELEGRAM_SECRETO lo reemplaza si quieres otro.
            secret_token=os.getenv("TELEGRAM_SECRETO") or hashlib.sha256(TOKEN.encode()).hexdigest()[:32],
        )
    else:
        print(f"Bot en marcha (polling). Permitidos: {sorted(permitidos()) or 'nadie'}. Ctrl+C para parar.", flush=True)
        app.run_polling()  # ojo: esto BORRA el webhook de Render (ver README, «Problemas frecuentes»)


if __name__ == "__main__":
    main()
