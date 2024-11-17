import telebot
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton
import requests
from config import BOT_TOKEN, API_TOKEN
from database import Database
import matplotlib
import io
from datetime import datetime, timedelta
import seaborn as sns
import numpy as np
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

class ReceiptBot:
    def __init__(self):
        self.bot = telebot.TeleBot(BOT_TOKEN)
        self.db = Database()
        self.setup_handlers()
        self.setup_keyboard()
        self.setup_scheduler()

    def setup_keyboard(self):
        self.keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        self.keyboard.add(
            KeyboardButton('📊 Статистика'),
            KeyboardButton('❓ Помощь')
        )
        self.keyboard.add(KeyboardButton('📷 Отправить чек'))

    def setup_handlers(self):
        self.bot.message_handler(commands=['start'])(self.send_welcome)
        self.bot.message_handler(commands=['help'])(self.send_help)
        self.bot.message_handler(content_types=['photo'])(self.handle_photo)
        self.bot.message_handler(content_types=['text'])(self.handle_text)

    def setup_scheduler(self):
        self.scheduler = BackgroundScheduler()
        # Schedule message for 12:30 PM every day
        self.scheduler.add_job(
            self.send_daily_reminder,
            trigger=CronTrigger(hour=12, minute=30),
            id='daily_reminder'
        )
        # Add new job for daily statistics at 18:00
        self.scheduler.add_job(
            self.send_daily_statistics,
            trigger=CronTrigger(hour=18, minute=0),
            id='daily_statistics'
        )
        self.scheduler.start()

    def send_daily_reminder(self):
        # Get all unique user IDs from the database
        users = self.db.get_all_users()
        reminder_text = "🔔 Не забудьте сканировать чеки!"
        
        for user_id in users:
            try:
                self.bot.send_message(user_id, reminder_text)
            except Exception as e:
                print(f"Failed to send reminder to user {user_id}: {e}")

    def send_daily_statistics(self):
        users = self.db.get_all_users()
        
        for user_id in users:
            try:
                # Generate charts for the user
                pie_buffer, bar_buffer = self.generate_spending_chart(user_id)
                
                if pie_buffer and bar_buffer:
                    # Get spending data for summary
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=30)
                    spending_data = self.db.get_spending_by_category(user_id, start_date, end_date)
                    
                    if spending_data:
                        highest_category = max(spending_data, key=lambda x: x[1])
                        summary_text = (
                            f"📊 Ваша ежедневная статистика расходов\n\n"
                            f"💰 Больше всего за 30 дней вы потратили на категорию \"{highest_category[0]}\": "
                            f"{highest_category[1]:.2f} руб."
                        )
                    else:
                        summary_text = "📊 Ваша ежедневная статистика расходов"
                    
                    # Send pie chart
                    self.bot.send_photo(
                        user_id,
                        pie_buffer,
                        caption="Распределение расходов по категориям (в процентах)"
                    )
                    
                    # Send bar chart
                    self.bot.send_photo(
                        user_id,
                        bar_buffer,
                        caption=summary_text
                    )
            except Exception as e:
                print(f"Failed to send statistics to user {user_id}: {e}")

    def __del__(self):
        try:
            self.scheduler.shutdown()
        except:
            pass

    def send_welcome(self, message):
        welcome_text = """🤖 Привет! Я бот для учета расходов!

📱 Как пользоваться:
• Отправьте фото QR-кода с чека
• Я автоматически распознаю товары и категории
• Смотрите статистику расходов по категориям

📊 Доступные команды:
• 📷 Отправить чек - сканирование нового чека
• 📊 Статистика - анализ ваших расходов
• ❓ Помощь - справка по работе бота"""
        self.bot.send_message(message.chat.id, welcome_text, reply_markup=self.keyboard)

    def send_help(self, message):
        help_text = """🤖 Справка по работе бота

📱 Основные функции:
• Сканирование QR-кодов с чеков
• Автоматическое распределение по категориям
• Анализ расходов в виде графиков
• Ежедневная статистика в 18:00

💡 Чтобы начать учет расходов:
1. Нажмите "📷 Отправить чек"
2. Сфотографируйте QR-код с чека
3. Дождитесь обработки и подтверждения

📊 Для просмотра статистики:
• Нажмите "📊 Статистика"
• Получите графики и анализ трат по категориям"""
        self.bot.send_message(message.chat.id, help_text)

    def standardize_category(self, category):
        if not category:
            return "Прочее"
        
        # Convert to lowercase and remove punctuation
        category = category.lower().strip().rstrip('.').rstrip('!')
        
        # Dictionary of category mappings
        category_mappings = {
            # Products/Food
            'продукты': 'Продукты',
            'products': 'Продукты',
            'еда': 'Продукты',
            'food': 'Продукты',
            'бакалея': 'Продукты',
            'grocery': 'Продукты',
            
            # Electronics
            'электроника': 'Электроника',
            'electronics': 'Электроника',
            'техника': 'Электроника',
            'gadgets': 'Электроника',
            
            # Household
            'бытовая химия': 'Бытовая химия',
            'household chemicals': 'Бытовая химия',
            'cleaning': 'Бытовая химия',
            
            # Construction
            'строительные материалы': 'Стройматериалы',
            'стройматериалы': 'Стройматериалы',
            'construction': 'Стройматериалы',
            'tools': 'Стройматериалы',
            
            # Cosmetics
            'косметика': 'Косметика',
            'cosmetics': 'Косметика',
            'beauty': 'Косметика',
            
            # Office supplies
            'канцтовары': 'Канцтовары',
            'office supplies': 'Канцтовары',
            'stationery': 'Канцтовары',
        }
        
        # Try to find a matching category
        for key, value in category_mappings.items():
            if key in category:
                return value
        
        return "Прочее"

    def process_receipt_items(self, message, items):
        total_sum = 0
        items_with_categories = self._get_categories_for_items(items)
        
        # If more than 5 items, just show the count
        if len(items) >= 5:
            for item in items_with_categories:
                try:
                    self._process_single_item(message.from_user.id, item)
                    total_sum += item['amount']
                except Exception as e:
                    print(f"Error processing item: {e}")
                    continue
            
            summary = [f"✅ Добавлено {len(items)} продуктов\n\nОбщая сумма чека: {total_sum:.2f} руб."]
            return summary
        
        # If 5 or fewer items, show the detailed list
        purchase_summary = []
        current_message = "🧾 История покупок:\n\n"
        
        for item in items_with_categories:
            try:
                item_summary = self._process_single_item(message.from_user.id, item)
                total_sum += item['amount']
                
                if len(current_message + item_summary) > 3500:
                    purchase_summary.append(current_message)
                    current_message = "🧾 История покупок (продолжение):\n\n"
                
                current_message += item_summary
                
            except Exception as e:
                print(f"Error processing item: {e}")
                continue
        
        current_message += f"Общая сумма чека: {total_sum:.2f} руб."
        purchase_summary.append(current_message)
        return purchase_summary

    def _get_categories_for_items(self, items):
        items_data = [{'name': item['name'], 'sum': item['sum']} for item in items]
        
        for item in items_data:
            try:
                category = self._get_category_from_api(item['name'])
                item['category'] = self.standardize_category(category)
                item['amount'] = float(item['sum']) / 100
            except Exception as e:
                print(f"Error getting category for {item['name']}: {e}")
                item['category'] = "Прочее"
                
        return items_data

    def _get_category_from_api(self, item_name):
        url = 'https://hackaton.ipostik.ru/webhook/f45b2eb9-614e-4fc9-a643-58c18dbaac0f'
        try:
            response = requests.post(url, json={'name': item_name})
            if response.status_code == 200:
                return response.json().get('myField')
        except Exception as e:
            print(f"API error for {item_name}: {e}")
        return None

    def _process_single_item(self, user_id, item):
        self.db.add_purchase(
            user_id=user_id,
            item_name=item['name'],
            amount=item['amount'],
            category=item['category']
        )
        
        return (f"Товар: {item['name']}\n"
                f"Категория: {item['category']}\n"
                f"Сумма: {item['amount']:.2f} руб.\n\n")

    def handle_photo(self, message: Message):
        try:
            # Add processing notification
            self.bot.send_message(message.chat.id, "⏳ Обрабатываю фотографию чека...")
            
            # Get photo URL
            file_info = self.bot.get_file(message.photo[-1].file_id)
            photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

            # Send request to check service
            url = 'https://proverkacheka.com/api/v1/check/get'
            payload = {
                'token': API_TOKEN,
                'qrurl': photo_url
            }

            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
            response_data = response.json() if response.text else None
            
            print(f"API Response: {response_data}")

            if not response_data or 'error' in response_data:
                error_message = "Ошибка при проверке чека.\n"
                if response_data:
                    if 'error' in response_data:
                        error_message += f"Ошибка: {response_data['error']}\n"
                    if 'data' in response_data and isinstance(response_data['data'], str):
                        error_message += f"{response_data['data']}"
                    elif 'data' in response_data and isinstance(response_data['data'], dict):
                        error_message += f"{response_data['data'].get('message', '')}"
                self.bot.send_message(message.chat.id, error_message)
                return

            # Process items
            items = response_data.get('data', {}).get('json', {}).get('items', [])
            if not items:
                self.bot.send_message(message.chat.id, "В чеке не найдены товары.")
                return

            # Process receipt items and send summary
            purchase_summaries = self.process_receipt_items(message, items)
            for summary in purchase_summaries:
                self.bot.send_message(message.chat.id, summary)

        except Exception as e:
            error_message = f"❌ Ошибка при обработке запроса: {str(e)}\n"
            if 'response_data' in locals() and response_data:
                if isinstance(response_data.get('data'), str):
                    error_message += f"{response_data['data']}"
                elif isinstance(response_data.get('data'), dict):
                    error_message += f"{response_data['data'].get('message', '')}"
            self.bot.send_message(message.chat.id, error_message)

    def generate_spending_chart(self, user_id):
        # Import and set matplotlib to use 'Agg' backend at the start of the method
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        db = Database()
        # Get spending data for the last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Get spending by category from database
        spending_data = db.get_spending_by_category(user_id, start_date, end_date)
        
        if not spending_data:
            return None, None
        
        # Ensure we have valid data
        if not spending_data or not all(isinstance(item, tuple) and len(item) == 2 for item in spending_data):
            print("Invalid or empty spending data")
            return None, None
        
        try:
            # Safely unpack the data
            categories, amounts = map(list, zip(*spending_data))
        except ValueError as e:
            print(f"Error unpacking spending data: {e}")
            return None, None
        
        # Set custom style - using a built-in style instead of seaborn
        plt.style.use('ggplot')
        colors = ['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', '#FF99CC', '#99CCFF', '#FFB366', '#99FF99']
        
        # PIE CHART
        plt.figure(figsize=(12, 8))
        plt.rcParams['font.size'] = 12
        
        patches, texts, autotexts = plt.pie(
            amounts,
            labels=[''] * len(categories),
            colors=colors[:len(categories)],
            shadow=True,
            startangle=90,
            wedgeprops={'edgecolor': 'white', 'linewidth': 2},
            autopct=''
        )
        
        # Calculate and format legend labels
        total = sum(amounts)
        percentages = [amt/total*100 for amt in amounts]
        legend_labels = [f'{cat}\n{pct:.1f}% ({amt:,.0f}₽)' 
                        for cat, pct, amt in zip(categories, percentages, amounts)]
        
        # Add legend with custom style
        plt.legend(
            patches, 
            legend_labels,
            title="Категории расходов",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            frameon=True,
            facecolor='white',
            edgecolor='lightgray',
            shadow=True
        )
        
        plt.title(
            'Распределение расходов по категориям',
            pad=20,
            fontsize=16,
            fontweight='bold'
        )
        
        # Save pie chart
        pie_buf = io.BytesIO()
        plt.savefig(pie_buf, format='png', dpi=300, bbox_inches='tight', facecolor='white')
        pie_buf.seek(0)
        plt.close()
        
        # BAR CHART
        plt.figure(figsize=(12, 8))
        bars = plt.bar(
            categories,
            amounts,
            color=colors[:len(categories)],
            edgecolor='white',
            linewidth=2
        )
        
        plt.title(
            'Сумма расходов по категориям',
            pad=20,
            fontsize=16,
            fontweight='bold'
        )
        
        # Customize grid
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Rotate and align x-axis labels
        plt.xticks(rotation=45, ha='right')
        
        # Add value labels on bars with improved formatting
        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width()/2.,
                height,
                f'{height:,.0f}₽',
                ha='center',
                va='bottom',
                fontsize=10,
                fontweight='bold'
            )
        
        # Customize axes
        plt.xlabel('Категории', fontsize=12, labelpad=10)
        plt.ylabel('Сумма (руб.)', fontsize=12, labelpad=10)
        
        # Save bar chart
        bar_buf = io.BytesIO()
        plt.savefig(bar_buf, format='png', dpi=300, bbox_inches='tight', facecolor='white')
        bar_buf.seek(0)
        plt.close()
        
        return pie_buf, bar_buf

    def handle_text(self, message: Message):
        if message.text == '📊 Статистика':
            # Generate charts
            pie_buffer, bar_buffer = self.generate_spending_chart(message.from_user.id)
            if pie_buffer and bar_buffer:
                # Get spending data for summary
                db = Database()
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                spending_data = db.get_spending_by_category(message.from_user.id, start_date, end_date)
                
                if spending_data:
                    highest_category = max(spending_data, key=lambda x: x[1])
                    summary_text = (
                        f"Ваша статистика расходов за последние 30 дней\n\n"
                        f"💰 Больше всего вы потратили на категорию \"{highest_category[0]}\": "
                        f"{highest_category[1]:.2f} руб."
                    )
                else:
                    summary_text = "Ваша статистика расходов за последние 30 дней"
                
                # Send pie chart
                self.bot.send_photo(
                    message.chat.id,
                    pie_buffer,
                    caption="Распределение расходов по категориям (в процентах)"
                )
                
                # Send bar chart
                self.bot.send_photo(
                    message.chat.id,
                    bar_buffer,
                    caption=summary_text
                )
            else:
                self.bot.send_message(
                    message.chat.id,
                    "У вас пока нет данных о расходах за последние 30 дней"
                )
        elif message.text == '❓ Помощь':
            self.send_help(message)
        elif message.text == '📷 Отправить чек':
            self.bot.send_message(message.chat.id, "Пожалуйста, отправьте фотографию QR-кода с чека")

    def run(self):
        self.bot.polling(none_stop=True)

if __name__ == "__main__":
    bot = ReceiptBot()
    bot.run()
