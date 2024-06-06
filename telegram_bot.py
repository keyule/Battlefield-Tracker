from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import requests
import asyncio
from utility import Utility
from prettytable import PrettyTable

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
            table = PrettyTable()
            table.field_names = ["Reg", "Lvl", "DeTime", "TLeft"]

            for mob in self.mob_list.mobs:
                disp_time = Utility.convert_to_sgt(mob.disappeared_time)
                time_left = Utility.calculate_time_difference(disp_time)
                time_left_str = Utility.format_time_left_TG(time_left)
                table.add_row([mob.region, mob.level, disp_time.strftime('%H:%M:%S'), time_left_str])

        await update.message.reply_text(f'```{table}```', parse_mode=ParseMode.MARKDOWN_V2)

    async def send_alert(self, message):
        chat_ids = os.getenv('TELEGRAM_CHAT_ID').split(',')
        for chat_id in chat_ids:
            chat_id = chat_id.strip()  # Ensuring no leading/trailing whitespace
            try:
                # Use self.application.bot to access the bot instance
                await self.application.bot.send_message(chat_id=chat_id, text=message)
            except Exception as e:
                print(f"Failed to send message to {chat_id}: {e}")

    # async def send_alert(self, message):
    #     chat_ids = os.getenv('TELEGRAM_CHAT_ID').split(',')
    #     url = f"https://api.telegram.org/bot{self.token}/sendMessage"
    #     for chat_id in chat_ids:
    #         chat_id = chat_id.strip()
    #         data = {
    #             "chat_id": chat_id,
    #             "text": message
    #         }
    #     await asyncio.to_thread(requests.post, url, data=data)
    
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