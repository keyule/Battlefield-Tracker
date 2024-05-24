from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import requests
import asyncio
import time
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

    def send_alert(self, message):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {
            "chat_id": os.getenv('TELEGRAM_CHAT_ID'),
            "text": message
        }
        requests.post(url, data=data)

    def start(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(self.application.run_polling(allowed_updates=Update.ALL_TYPES))
        try:
            loop.run_forever()
        finally:
            task.cancel()
            loop.run_until_complete(task) 
            loop.close()

    def stop(self):
        loop = asyncio.get_event_loop()
        loop.stop()

    def run(self):
        """Run the bot using an asyncio event loop."""
        try:
            asyncio.run(self.start())
        except Exception as e:
            print(f"An error occurred in the Telegram bot: {e}")
