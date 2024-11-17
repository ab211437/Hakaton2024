import requests
import json
from config import API_TOKEN, WEBHOOK_URL

class APIClient:
    @staticmethod
    def check_receipt(fields):
        url = 'https://proverkacheka.com/api/v1/check/get'
        payload = {
            'token': API_TOKEN,
            'fn': fields['fn'],
            'fd': fields['i'],
            'fp': fields['fp'],
            't': fields['t'],
            's': fields['s'],
            'n': 1,
            'qr': 1
        }
        
        try:
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
            # Добавляем проверку и преобразование JSON
            if response.text:
                return json.loads(response.text)
            return None
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            return None

    @staticmethod
    def send_items_data(items_data):
        payload = {'items': [{'name': item['name']} for item in items_data]}
        try:
            response = requests.post(WEBHOOK_URL, json=payload)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error sending items data: {e}")
            return False 