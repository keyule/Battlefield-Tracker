from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import requests
import asyncio
from utility import Utility

class TelegramBot:
    def __init__(self, token, mob_list):
        self.token = token
        self.mob_list = mob_list
        self.application = Application.builder().token(token).build()

        # Add command handler for /mob
        mob_handler = CommandHandler("mobs", self.mob_command)
        self.application.add_handler(mob_handler)
        self.running = True

    async def mob_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user  # This retrieves the user information
        print(f"Command executed by UserID: {user.id}, Username: {user.username}")  # Log the user's ID and username

        mobs, last_updated = self.mob_list.get_current_mobs()
        if not mobs:
            message = "No mobs available."
        else:
            message = "Current mobs:\n"
            for mob in mobs:
                # Convert despawn time to SGT using the Utility class
                disp_time_sgt = Utility.convert_to_sgt(mob.disappeared_time)
                # Calculate the time left until despawn
                time_left = Utility.calculate_time_difference(disp_time_sgt)
                # Format the time left for display
                time_left_str = Utility.format_time_left(time_left)

                message += (f"ID: {mob.mob_id}, Region: {mob.region}, "
                            f"Level: {mob.level}, Despawn Time: {disp_time_sgt.strftime('%Y-%m-%d %H:%M:%S')}, "
                            f"Time Left: {time_left_str}\n")
            message += f"\nLast Updated: {last_updated}"

        await update.message.reply_text(message)

    async def send_alert(self, message):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {
            "chat_id": os.getenv('TELEGRAM_CHAT_ID'),
            "text": message
        }
        await asyncio.to_thread(requests.post, url, data=data)

    async def start(self):
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        await self.idle()

    async def idle(self):
        """Block until a signal is received, then clean up."""
        while self.running:
            await asyncio.sleep(1)

    async def stop(self):
        self.running = False
        await self.application.stop()