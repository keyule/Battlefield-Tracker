from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
from utility import Utility
from prettytable import PrettyTable
from rewards import Rewards
from datetime import timedelta  

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
        self.application.add_handler(CommandHandler("setalarm", self.set_alarm_command))
        self.running = True
        self.id_to_mob_id = {} 

    async def mob_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user 
            print(f"Command executed by UserID: {user.id}, Username: {user.username}")  # Log the user's ID and username

            mobs, last_updated = self.mob_list.get_current_mobs()
            if not mobs:
                message = "No mobs available."
            else:
                mob_table = PrettyTable()
                prize_table = PrettyTable()

                mob_table.field_names = ["ID", "Reg", "Lv", "DeTime", "T Left"]
                prize_table.field_names = ["Reg", "Lv", "First Prize"]

                self.id_to_mob_id.clear()  # Clear the previous mapping
                for idx, mob in enumerate(self.mob_list.mobs, start=1):
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

                    self.id_to_mob_id[idx] = mob.mob_id  # Store the mapping
                    mob_table.add_row([idx, mob.region, mob.level, disp_time.strftime('%H:%M:%S'), time_left_str])

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
                await self.application.bot.send_message(chat_id=chat_id, text=message)
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


    async def set_alarm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_message.chat_id
        try:
            simple_id = int(context.args[0])
            if simple_id not in self.id_to_mob_id:
                await update.effective_message.reply_text("Invalid mob ID.")
                return

            mob_id = self.id_to_mob_id[simple_id]
            due = self.calculate_due_time(mob_id)
            if due is None or due < 0:
                await update.effective_message.reply_text("Invalid mob ID or mob already expired.")
                return

            job_removed = self.remove_job_if_exists(str(chat_id), context)
            context.job_queue.run_once(self.alarm, due, chat_id=chat_id, name=str(chat_id), data=simple_id)

            text = "Alarm successfully set!"
            if job_removed:
                text += " Old one was removed."
            await update.effective_message.reply_text(text)

        except (IndexError, ValueError):
            await update.effective_message.reply_text("Usage: /setalarm <simple_id>")

    def calculate_due_time(self, mob_id):
        for mob in self.mob_list.mobs:
            if mob.mob_id == mob_id:
                disp_time = Utility.convert_to_sgt(mob.disappeared_time)
                time_left = Utility.calculate_time_difference(disp_time)
                due_time = time_left - timedelta(minutes=12)
                return max(0, due_time.total_seconds())
        return None

    async def alarm(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send the alarm message."""
        job = context.job
        await context.bot.send_message(job.chat_id, text=f"Beep! 12 minutes left for mob ID {job.data}!")

    def remove_job_if_exists(self, name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Remove job with given name. Returns whether job was removed."""
        current_jobs = context.job_queue.get_jobs_by_name(name)
        if not current_jobs:
            return False
        for job in current_jobs:
            job.schedule_removal()
        return True