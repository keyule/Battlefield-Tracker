from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
import json
from utility import Utility
from prettytable import PrettyTable
from rewards import Rewards

class TelegramBot:
    def __init__(self, token, mob_list):
        self.token = token
        self.mob_list = mob_list
        self.application = Application.builder().token(token).build()
        self.rewards = Rewards('rewards.json')

        # Add command handlers
        self.application.add_handler(CommandHandler("mobs", self.mob_command))
        self.application.add_handler(CommandHandler("subscribe", self.subscribe_command))
        self.application.add_handler(CommandHandler("unsubscribe", self.unsubscribe_command))
        self.running = True

    async def mob_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user 
        print(f"Command executed by UserID: {user.id}, Username: {user.username}")  # Log the user's ID and username

        mobs, last_updated = self.mob_list.get_current_mobs()
        if not mobs:
            message = "No mobs available."
        else:
            mob_table = PrettyTable()
            prize_table = PrettyTable()

            mob_table.field_names = ["Reg", "Lvl", "DeTime", "TLeft"]
            prize_table.field_names = ["Reg", "Lvl", "First Prize"]

            for mob in self.mob_list.mobs:
                disp_time = Utility.convert_to_sgt(mob.disappeared_time)
                time_left = Utility.calculate_time_difference(disp_time)
                time_left_str = Utility.format_time_left_TG(time_left)

                first_place_prize = self.rewards.get_first_place_prize(mob.reward_group_id)
                prize_items = first_place_prize.split(',')

                # Add the first item with the mob details
                if prize_items:
                    prize_table.add_row([mob.region, mob.level, prize_items[0].strip()])
                    # Add remaining items, aligning with the same mob but without repeating region and level
                    for item in prize_items[1:]:
                        prize_table.add_row(["", "", item.strip()])
                else:
                    prize_table.add_row([mob.region, mob.level, "No prize data"])

                mob_table.add_row([mob.region, mob.level, disp_time.strftime('%H:%M:%S'), time_left_str])

        combined_message = f"**Mob Information:**\n```{mob_table}```\n**Prizes:**\n```{prize_table}```"
        await update.message.reply_text(combined_message, parse_mode=ParseMode.MARKDOWN_V2)

    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        username = update.effective_user.username or "NoUsername"  # Fallback if the user doesn't have a username
        subscriber_info = f"{user_id},{username}\n"  
        print(f"UserID: {user_id}, Username: {username} has subscribed!")  

        with open("subscribers.txt", "a+") as file:
            file.seek(0)
            subscribers = file.readlines()
            if subscriber_info not in subscribers:
                file.write(subscriber_info)
                await update.message.reply_text("You've been subscribed successfully!")
            else:
                await update.message.reply_text("You're already subscribed.")

    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        with open("subscribers.txt", "r+") as file:
            lines = file.readlines()
            file.seek(0)
            found = False
            for line in lines:
                if line.split(',')[0].strip() != str(user_id):  # Check only the user_id part
                    file.write(line)
                else:
                    found = True
            file.truncate()
            if found:
                await update.message.reply_text("You've been unsubscribed.")
            else:
                await update.message.reply_text("You were not subscribed.")

    async def send_alert(self, message):
        try:
            with open("subscribers.txt", "r") as file:
                subscribers = file.readlines()
            for subscriber in subscribers:
                chat_id = subscriber.split(',')[0].strip()
                await self.application.bot.send_excerpt(chat_id=chat_id, text=message)
        except Exception as e:
            print(f"Failed to send message: {e}")
    
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