# Configuration settings

WEBHOOK_URL = 'https://hackaton.ipostik.ru/webhook/f45b2eb9-614e-4fc9-a643-58c18dbaac0f'

from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
API_TOKEN = os.getenv('API_TOKEN')

if not BOT_TOKEN or not API_TOKEN:
    raise ValueError("Missing required environment variables. Please check your .env file.")