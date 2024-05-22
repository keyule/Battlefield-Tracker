from datetime import datetime, timezone
import pytz

class Utility:
    @staticmethod
    def convert_to_sgt(disp_time_str):
        """Convert a given time string to Singapore Time."""
        SINGAPORE_TZ = pytz.timezone('Asia/Singapore')
        return datetime.fromisoformat(disp_time_str[:-1]).replace(tzinfo=timezone.utc).astimezone(SINGAPORE_TZ)

    @staticmethod
    def calculate_time_difference(disp_time):
        """Calculate the time difference from the current time to the given time."""
        SINGAPORE_TZ = pytz.timezone('Asia/Singapore')
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

    @staticmethod
    def get_current_time():
        """Return the current time."""
        return datetime.now().strftime("%H:%M:%S")
