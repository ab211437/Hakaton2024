import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_file="hack/purchases.db"):
        self.db_file = db_file
        self._ensure_connection()
        
    def _ensure_connection(self):
        self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        
    def __del__(self):
        try:
            self.conn.close()
        except:
            pass

    def execute_query(self, query, params=None):
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.conn.commit()
            return self.cursor
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            raise

    def create_tables(self):
        self.execute_query('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT,
            purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

    def add_purchase(self, user_id: int, item_name: str, amount: float, category: str = None):
        query = '''
        INSERT INTO purchases (user_id, item_name, amount, category, purchase_date)
        VALUES (?, ?, ?, ?, ?)
        '''
        self.execute_query(query, (user_id, item_name, amount, category, datetime.now()))

    def get_user_purchases(self, user_id: int):
        query = '''
        SELECT * FROM purchases 
        WHERE user_id = ? 
        ORDER BY purchase_date DESC
        '''
        self.cursor.execute(query, (user_id,))
        purchases = self.cursor.fetchall()
        return purchases

    def get_user_statistics(self, user_id: int):
        query = '''
        SELECT category, SUM(amount) as total_amount 
        FROM purchases 
        WHERE user_id = ? 
        GROUP BY category
        '''
        self.cursor.execute(query, (user_id,))
        stats = self.cursor.fetchall()
        return stats

    def print_all_data(self):
        self.cursor.execute('SELECT * FROM purchases')
        rows = self.cursor.fetchall()
        
        print("\nВсе записи в базе данных:")
        print("ID | User ID | Item Name | Amount | Category | Purchase Date")
        print("-" * 70)
        for row in rows:
            print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")

    def get_spending_by_category(self, user_id: int, start_date: datetime, end_date: datetime):
        query = '''
        SELECT category, SUM(amount) as total_amount 
        FROM purchases 
        WHERE user_id = ? 
        AND purchase_date BETWEEN ? AND ?
        AND category IS NOT NULL
        GROUP BY category
        ORDER BY total_amount DESC
        '''
        self.cursor.execute(query, (user_id, start_date, end_date))
        spending_data = self.cursor.fetchall()
        return spending_data

    def get_all_users(self):
        query = '''
        SELECT DISTINCT user_id FROM purchases
        '''
        self.cursor.execute(query)
        users = [row[0] for row in self.cursor.fetchall()]
        return users
