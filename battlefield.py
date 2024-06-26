import os
import argparse
from dotenv import load_dotenv
import json
import time
import sys
import asyncio
from prettytable import PrettyTable
from utility import Utility
from api_manager import ApiManager
from telegram_bot import TelegramBot
from rewards import Rewards

# Load environment variables
load_dotenv()

# Constants
REGION_MAP = {0: "Pir", 1: "Cat", 2: "Wlf", 3: "Fod"}
REQUEST_ID = int(os.getenv('REQUEST_ID'))
BODY_HMAC = os.getenv('BODY_HMAC')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_ALERTS_ENABLED = os.getenv('TELEGRAM_ALERTS_ENABLED', 'False') == 'True'
MIN_TIME_LEFT = 70  # Time left threshold in minutes for alert
SLEEP_TIME = 60  # Sleep time in seconds (5 minutes)

class Mob:
    def __init__(self, mob_id, region, level, disappeared_time, reward_group_id):
        self.mob_id = mob_id
        self.region = region
        self.level = level
        self.disappeared_time = disappeared_time
        self.reward_group_id = reward_group_id

class MobList:
    def __init__(self):
        self.mobs = []
        self.previous_ids = []
        self.last_updated = None

    def update_mobs(self, new_mobs):
        self.previous_ids = [mob.mob_id for mob in self.mobs]
        self.mobs = new_mobs
        self.last_updated = Utility.get_current_time()

    def get_new_mobs(self):
        if not self.previous_ids:
            # If last_updated is None, it's the first run, so don't count any mobs as new.
            return []
        new_mobs = [mob for mob in self.mobs if mob.mob_id not in self.previous_ids]
        return new_mobs

    def get_last_updated(self):
        return self.last_updated

    def get_current_mobs(self):
        return self.mobs, self.last_updated

class UI:
    @staticmethod
    def print_battlefield_info(mob_list, rewards):
        table = PrettyTable()
        table.field_names = ["ID", "Region", "Level", "Despawn Time", "Time Left", "RewardID", "1st Prize"]

        for mob in mob_list.mobs:
            disp_time = Utility.convert_to_sgt(mob.disappeared_time)
            time_left = Utility.calculate_time_difference(disp_time)
            time_left_str = Utility.format_time_left(time_left)
            first_place_prize = rewards.get_first_place_prize(mob.reward_group_id)
            table.add_row([mob.mob_id, mob.region, mob.level, disp_time.strftime('%m-%d %H:%M:%S'), time_left_str, mob.reward_group_id, first_place_prize])

        print(table)

    @staticmethod
    def print_alert_message(alert_message):
        print(alert_message)

    @staticmethod
    def print_last_updated(last_updated):
        print("Last Updated:", last_updated)

class Alert:
    @staticmethod
    async def alert_for_new_mobs(new_mobs, rewards, telegram_bot):
        for mob in new_mobs:
            disp_time = Utility.convert_to_sgt(mob.disappeared_time)
            time_left = Utility.calculate_time_difference(disp_time)
            time_left_str = Utility.format_time_left(time_left)
            minutes_left = Utility.calculate_minutes_left(time_left)

            first_place_prize = rewards.get_first_place_prize(mob.reward_group_id)
            
            alert_message = (
                    f"Alert: New mob Spawned!\n"
                    f"ID: {mob.mob_id}\n"
                    f"Region: {mob.region}\n"
                    f"Level: {mob.level}\n"
                    f"Time Left: {time_left_str}\n"
                    f"Reward Group ID: {mob.reward_group_id}\n"
                    f"1st Prize: {first_place_prize}"
                )

            alert_message2 = (
                f"New Mob Spawned! Level: {mob.level}, Time Left: {time_left_str}, 1st Prize: {first_place_prize}"
            )

            if minutes_left < MIN_TIME_LEFT:
                UI.print_alert_message(alert_message)
                if TELEGRAM_ALERTS_ENABLED:
                    await telegram_bot.send_alert(alert_message)
            else:
                UI.print_alert_message(alert_message2)
            

class Battlefield:
    def __init__(self, request_id, bearer_token, body_hmac, mob_list, telegram_bot):
        self.api_manager = ApiManager(request_id, bearer_token, body_hmac)
        self.mob_list = mob_list
        self.rewards = Rewards('rewards.json')
        self.telegram_bot = telegram_bot
        self.running = True

    async def run(self):
        try:
            while self.running:
                data = self.api_manager.get_battlefields()
                new_mobs = []
                for region in data["regions"]:
                    region_name = REGION_MAP.get(region['region'], "Unknown")
                    for battlefield in region["battlefields"]:
                        mob = Mob(
                            mob_id=battlefield['id'],
                            region=region_name,
                            level=battlefield['level'],
                            disappeared_time=battlefield["disappearedTime"],
                            reward_group_id=battlefield['rewardGroupId']
                        )
                        new_mobs.append(mob)

                self.mob_list.update_mobs(new_mobs)

                UI.print_battlefield_info(self.mob_list, self.rewards)
                new_mobs = self.mob_list.get_new_mobs()
                if new_mobs:
                    await Alert.alert_for_new_mobs(new_mobs, self.rewards, self.telegram_bot)

                last_updated = self.mob_list.get_last_updated()
                UI.print_last_updated(last_updated)
                await asyncio.sleep(SLEEP_TIME)
        except asyncio.CancelledError:
            self.stop()

    def stop(self):
        self.running = False

async def main():
    parser = argparse.ArgumentParser(description='Run the battlefield monitoring script.')
    parser.add_argument('-token', '--bearer_token', required=True, help='Bearer token for authentication')
    args = parser.parse_args()

    mob_list = MobList()

    if TELEGRAM_ALERTS_ENABLED:
        telegram_bot = TelegramBot(TELEGRAM_TOKEN, mob_list)
    else:
        telegram_bot = None

    battlefield = Battlefield(REQUEST_ID, args.bearer_token, BODY_HMAC, mob_list, telegram_bot)

    battlefield_task = asyncio.create_task(battlefield.run())

    if TELEGRAM_ALERTS_ENABLED:
        try:
            await telegram_bot.start()  # This runs the Telegram bot
        except KeyboardInterrupt:
            print("Shutdown requested...")
            battlefield.stop()
            await asyncio.gather(battlefield_task)
            await telegram_bot.stop()
    else:
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Shutdown requested...")
            battlefield.stop()
            await asyncio.gather(battlefield_task)

    print("Successfully shutdown the service.")

if __name__ == "__main__":
    asyncio.run(main())