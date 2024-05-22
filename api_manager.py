import requests

class ApiManager:
    def __init__(self, request_id, bearer_token, body_hmac):
        self.request_id = request_id
        self.bearer_token = bearer_token
        self.body_hmac = body_hmac

    def update_bearer_token(self):
        new_token = input("Bearer token has expired or is invalid. Please enter a new bearer token: ")
        self.bearer_token = new_token

    def get_battlefields(self):
        url = 'https://gv.gameduo.net/battlefield/getAllRegions'
        headers = {
            'Authorization': f"Bearer {self.bearer_token}",
            'bodyhmac': self.body_hmac,
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