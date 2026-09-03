import sqlite3
from datetime import datetime

DB_NAME = "autoprocure.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Store internal inventory
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            sku TEXT PRIMARY KEY,
            item_name TEXT,
            current_stock INTEGER,
            reorder_threshold INTEGER,
            target_stock INTEGER
        )
    """)
    
    # Audit trail table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            sku TEXT,
            action TEXT,
            decision TEXT,
            status TEXT,
            order_id TEXT,
            amount_inr REAL,
            details TEXT
        )
    """)

    # NPCI UAP / UPI Reserve Pay Vault
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reserve_vault (
            id INTEGER PRIMARY KEY,
            balance_inr REAL,
            daily_spent_inr REAL,
            daily_limit_inr REAL
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM reserve_vault")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO reserve_vault VALUES (1, 300000.0, 0.0, 200000.0)")

    cursor.execute("SELECT COUNT(*) FROM inventory")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO inventory VALUES (?, ?, ?, ?, ?)
        """, [
            ("SKU-KB-01", "Mechanical Keyboard Pro", 2, 5, 10),
            ("SKU-MS-02", "Wireless Ergonomic Mouse", 1, 4, 8),
            ("SKU-HUB-03", "USB-C Multiport Hub", 6, 3, 10),
            ("SKU-MON-04", "27-inch 4K IPS Monitor", 1, 2, 4),
            ("SKU-CBL-05", "Braided 100W Type-C Cable", 3, 10, 20),
            ("SKU-HD-06", "ANC Studio Headphones", 1, 3, 5),
            ("SKU-SSD-07", "1TB NVMe M.2 SSD", 1, 3, 6),
            ("SKU-RAM-08", "16GB DDR5 5600MHz RAM", 2, 4, 6),
            ("SKU-CAM-09", "1080p 60fps Pro Webcam", 1, 3, 4),
            ("SKU-MIC-10", "USB Condenser Studio Mic", 2, 3, 5),
            ("SKU-MAT-11", "Extended Desk Mat (90x40cm)", 2, 5, 12),
            ("SKU-STN-12", "Aluminum Laptop Riser Stand", 5, 4, 8),
            ("SKU-CHG-13", "65W GaN Fast Wall Charger", 2, 5, 8),
            ("SKU-PWR-14", "20000mAh PD Power Bank", 1, 3, 5),
            ("SKU-LGT-15", "Monitor LED ScreenBar Light", 4, 3, 6),
            ("SKU-ROU-16", "Wi-Fi 6 Dual-Band Router", 1, 2, 4),
            ("SKU-SWT-17", "8-Port Gigabit Desktop Switch", 1, 3, 5),
            ("SKU-SPK-18", "Compact Stereo Desktop Speakers", 1, 2, 4),
            ("SKU-ENC-19", "M.2 NVMe Tool-Free Enclosure", 2, 4, 7),
            ("SKU-CLN-20", "Electronics Screen Cleaning Kit", 4, 10, 20)
        ])
    
    conn.commit()
    conn.close()

def log_audit(sku, action, decision, status, order_id=None, amount_inr=0.0, details=""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_logs (timestamp, sku, action, decision, status, order_id, amount_inr, details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sku, action, decision, status, order_id, amount_inr, details))
    conn.commit()
    conn.close()

def deduct_reserve_vault(amount_inr: float):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE reserve_vault 
        SET balance_inr = balance_inr - ?, daily_spent_inr = daily_spent_inr + ? 
        WHERE id = 1
    """, (amount_inr, amount_inr))
    conn.commit()
    conn.close()
