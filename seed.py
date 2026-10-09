import sqlite3
import random
from datetime import datetime, timedelta

def seed_db():
    conn = sqlite3.connect('report.db')
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer TEXT,
        product TEXT,
        amount REAL,
        created_at DATE
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT,
        created_at DATE
    )''')
    
    # Clear existing to maintain idempotency in seeding
    c.execute('DELETE FROM orders')
    
    products = ['Laptop', 'Mouse', 'Keyboard', 'Monitor', 'Headphones', 'Desk']
    
    for i in range(200):
        product = random.choice(products)
        amount = round(random.uniform(5, 200), 2)
        days_ago = random.randint(0, 30)
        date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        
        c.execute('INSERT INTO orders (customer, product, amount, created_at) VALUES (?, ?, ?, ?)',
                  (f'Customer_{i}', product, amount, date))
        
    conn.commit()
    
    c.execute('SELECT COUNT(*) FROM orders')
    count = c.fetchone()[0]
    print(f"Seeded {count} orders.")
    conn.close()

if __name__ == '__main__':
    seed_db()
