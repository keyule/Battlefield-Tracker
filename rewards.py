import json

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