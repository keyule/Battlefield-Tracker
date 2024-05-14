import requests
import os
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

# Global region map
REGION_MAP = {0: "Pirate", 1: "Cat", 2: "Wolf", 3: "Food"}

# Initialize request-id in memory
current_request_id = int(os.getenv('REQUEST_ID'))

def get_battlefields():
    """Fetch and return battlefield data from the API, incrementing request-id."""
    global current_request_id
    url = 'https://gv.gameduo.net/battlefield/getAllRegions'
    
    headers = {
        'Authorization': f"Bearer {os.getenv('BEARER_TOKEN')}",
        'bodyhmac': os.getenv('BODY_HMAC'),
        'Content-Type': 'application/json',
        'Host': 'gv.gameduo.net',
        'request-id': str(current_request_id),
        'User-Agent': 'UnityPlayer/2021.3.33f1 (UnityWebRequest/1.0, libcurl/8.4.0-DEV)',
        'X-Unity-Version': '2021.3.33f1',
        'Content-Length': '2'
    }

    # Make the request
    response = requests.post(url, headers=headers, json={})

    if response.status_code == 403:
        print('Authorization Error: Bearer token has expired or is invalid. Please update your authentication credentials and try again.')
        sys.exit(1)

    # Increment the request-id after the request
    current_request_id += 1

    return json.loads(response.text)

def calculate_time_details(gen_time_str, disp_time_str):
    """Convert and calculate time details."""
    singapore_tz = pytz.timezone('Asia/Singapore')
    current_time = datetime.now(timezone.utc).astimezone(singapore_tz)
    gen_time = datetime.fromisoformat(gen_time_str[:-1]).replace(tzinfo=timezone.utc).astimezone(singapore_tz)
    disp_time = datetime.fromisoformat(disp_time_str[:-1]).replace(tzinfo=timezone.utc).astimezone(singapore_tz)

    time_left = disp_time - current_time
    hours_left = time_left.seconds // 3600
    minutes_left = (time_left.seconds % 3600) // 60
    time_left_str = f"{hours_left} hrs {minutes_left} min" if hours_left > 0 else f"{minutes_left} min"

    return gen_time.strftime('%m-%d %H:%M:%S'), disp_time.strftime('%m-%d %H:%M:%S'), time_left_str

def alert_for_new_mobs(new_mobs, data, min_time_left, reward_ids, telegram_alerts_enabled):
    """Alerts if new mobs meet the criteria of time left, reward IDs, and includes region and level information."""
    singapore_tz = pytz.timezone('Asia/Singapore')
    current_time = datetime.now(timezone.utc).astimezone(singapore_tz)
    alert_mobs = []

    for mob in new_mobs:
        for region in data["regions"]:
            region_name = REGION_MAP.get(region['region'], "Unknown")
            for battlefield in region["battlefields"]:
                if battlefield['id'] == mob:
                    gen_time_str, disp_time_str, time_left_str = calculate_time_details(battlefield["generatedTime"], battlefield["disappearedTime"])
                    disp_time = datetime.fromisoformat(battlefield["disappearedTime"][:-1]).replace(tzinfo=timezone.utc).astimezone(singapore_tz)
                    time_left = disp_time - current_time
                    minutes_left = (time_left.seconds // 60) + time_left.days * 1440  # Convert days to minutes if any

                    if minutes_left < min_time_left and (not reward_ids or battlefield['rewardGroupId'] in reward_ids):
                        alert_message = (
                            f"Alert: New mob with ID: {battlefield['id']}, "
                            f"Region: {region['region']} - {region_name}, "
                            f"Level: {battlefield['level']}, "
                            f"Reward Group ID: {battlefield['rewardGroupId']}, "
                            f"Time Left: {minutes_left} minutes has spawned!"
                        )
                        print(alert_message)
                        if telegram_alerts_enabled:
                            send_telegram_message(alert_message)


def print_battlefield_info(data, previous_ids, min_time_left, reward_ids, telegram_alerts_enabled):
    table = PrettyTable()
    table.field_names = ["ID", "Region", "Level", "Generated Time (SGT)", "Disappearing Time (SGT)", "Time Left", "Reward Group ID"]
    current_ids = []

    for region in data["regions"]:
        region_name = REGION_MAP.get(region['region'], "Unknown")
        for battlefield in region["battlefields"]:
            gen_time, disp_time, time_left_str = calculate_time_details(battlefield["generatedTime"], battlefield["disappearedTime"])
            table.add_row([battlefield['id'], f"{region['region']} - {region_name}", battlefield['level'], gen_time, disp_time, time_left_str, battlefield['rewardGroupId']])
            current_ids.append(battlefield['id'])
    
    print(table)
    
    new_mobs = [mob_id for mob_id in current_ids if mob_id not in previous_ids]
    if new_mobs:
        print("New mobs have spawned:", new_mobs)
        alert_for_new_mobs(new_mobs, data, min_time_left, reward_ids, telegram_alerts_enabled)

    return current_ids

def main():
    """Main execution function."""
    previous_ids = []
    min_time_left = 70  # Time left threshold in minutes for alert
    reward_ids = []  # Empty list indicates no specific filter on reward IDs
    telegram_alerts_enabled = os.getenv('TELEGRAM_ALERTS_ENABLED', 'False') == 'True'

    try:
        while True:
            data = get_battlefields()
            previous_ids = print_battlefield_info(data, previous_ids, min_time_left, reward_ids, telegram_alerts_enabled)

            current_time = datetime.now()
            print("Last Updated:", current_time.strftime("%H:%M:%S"))
            time.sleep(600)  # Sleep for 10 minutes
    except KeyboardInterrupt:
        print("Stopped by user.")


if __name__ == "__main__":
    main()