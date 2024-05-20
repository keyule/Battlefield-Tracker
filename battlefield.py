import requests
import os
import argparse
from dotenv import load_dotenv
import pytz
import json
from datetime import datetime, timezone
import time
import sys
from prettytable import PrettyTable
from telegram_alert import send_telegram_message

# Load environment variables
load_dotenv()

# Constants
REGION_MAP = {0: "Pirate", 1: "Cat", 2: "Wolf", 3: "Food"}
SINGAPORE_TZ = pytz.timezone('Asia/Singapore')
REQUEST_ID = int(os.getenv('REQUEST_ID'))
BODY_HMAC = os.getenv('BODY_HMAC')
TELEGRAM_ALERTS_ENABLED = os.getenv('TELEGRAM_ALERTS_ENABLED', 'False') == 'True'
MIN_TIME_LEFT = 70  # Time left threshold in minutes for alert
SLEEP_TIME = 300  # Sleep time in seconds (5 minutes)

class Rewards:
    def __init__(self, rewards_file):
        self.rewards_data = self.load_rewards(rewards_file)

    def load_rewards(self, rewards_file):
        with open(rewards_file, 'r') as file:
            return json.load(file)

    def get_first_place_prize(self, reward_group_id):
        if str(reward_group_id) in self.rewards_data and self.rewards_data[str(reward_group_id)]:
            return ', '.join(self.rewards_data[str(reward_group_id)][0])
        return "No data available"

class ApiManager:
    def __init__(self, request_id, bearer_token):
        self.request_id = request_id
        self.bearer_token = bearer_token

    def update_bearer_token(self):
        new_token = input("Bearer token has expired or is invalid. Please enter a new bearer token: ")
        self.bearer_token = new_token

    def get_battlefields(self):
        url = 'https://gv.gameduo.net/battlefield/getAllRegions'
        headers = {
            'Authorization': f"Bearer {self.bearer_token}",
            'bodyhmac': BODY_HMAC,
            'Content-Type': 'application/json',
            'Host': 'gv.gameduo.net',
            'request-id': str(self.request_id),
            'User-Agent': 'UnityPlayer/2021.3.33f1 (UnityWebRequest/1.0, libcurl/8.4.0-DEV)',
            'X-Unity-Version': '2021.3.33f1',
            'Content-Length': '2'
        }

        response = requests.post(url, headers=headers, json={})
        if response.status_code == 403:
            self.update_bearer_token()
            return self.get_battlefields()  # Retry with the new token
        
        self.request_id += 1
        return response.json()

class Utility:
    @staticmethod
    def convert_to_sgt(disp_time_str):
        """Convert a given time string to Singapore Time."""
        return datetime.fromisoformat(disp_time_str[:-1]).replace(tzinfo=timezone.utc).astimezone(SINGAPORE_TZ)

    @staticmethod
    def calculate_time_difference(disp_time):
        """Calculate the time difference from the current time to the given time."""
        current_time = datetime.now(timezone.utc).astimezone(SINGAPORE_TZ)
        return disp_time - current_time

    @staticmethod
    def format_time_left(time_left):
        """Format the time left into a human-readable string."""
        hours_left = time_left.seconds // 3600
        minutes_left_only = (time_left.seconds % 3600) // 60
        return f"{hours_left} hrs {minutes_left_only} min" if hours_left > 0 else f"{minutes_left_only} min"

    @staticmethod
    def calculate_minutes_left(time_left):
        """Calculate the total minutes left from the time difference."""
        return (time_left.seconds // 60) + time_left.days * 1440  # Convert days to minutes if any

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

    def add_mob(self, mob):
        self.mobs.append(mob)

    def get_new_mobs(self):
        new_mobs = [mob for mob in self.mobs if mob.mob_id not in self.previous_ids]
        self.previous_ids = [mob.mob_id for mob in self.mobs]
        return new_mobs

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
    def print_last_updated():
        current_time = datetime.now()
        print("Last Updated:", current_time.strftime("%H:%M:%S"))

class Alert:
    @staticmethod
    def alert_for_new_mobs(new_mobs, rewards):
        for mob in new_mobs:
            disp_time = Utility.convert_to_sgt(mob.disappeared_time)
            time_left = Utility.calculate_time_difference(disp_time)
            time_left_str = Utility.format_time_left(time_left)
            minutes_left = Utility.calculate_minutes_left(time_left)

            first_place_prize = rewards.get_first_place_prize(mob.reward_group_id)

            if minutes_left < MIN_TIME_LEFT:
                alert_message = (
                    f"Alert: New mob Spawned!\n"
                    f"ID: {mob.mob_id}\n"
                    f"Region: {mob.region}\n"
                    f"Level: {mob.level}\n"
                    f"Time Left: {time_left_str}\n"
                    f"Reward Group ID: {mob.reward_group_id}\n"
                    f"1st Prize: {first_place_prize}"
                )
                UI.print_alert_message(alert_message)
                if TELEGRAM_ALERTS_ENABLED:
                    send_telegram_message(alert_message)

class Battlefield:
    def __init__(self, bearer_token):
        self.api_manager = ApiManager(REQUEST_ID, bearer_token)
        self.mob_list = MobList()
        self.rewards = Rewards('rewards.json')

    def run(self):
        try:
            while True:
                data = self.api_manager.get_battlefields()
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
                        self.mob_list.add_mob(mob)

                UI.print_battlefield_info(self.mob_list, self.rewards)
                new_mobs = self.mob_list.get_new_mobs()
                if new_mobs:
                    Alert.alert_for_new_mobs(new_mobs, self.rewards)

                UI.print_last_updated()
                time.sleep(SLEEP_TIME)
        except KeyboardInterrupt:
            UI.print_alert_message("Stopped by user.")

def main():
    parser = argparse.ArgumentParser(description='Run the battlefield monitoring script.')
    parser.add_argument('-token', '--bearer_token', required=True, help='Bearer token for authentication')
    args = parser.parse_args()

    battlefield = Battlefield(args.bearer_token)
    battlefield.run()

if __name__ == "__main__":
    main()