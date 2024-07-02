import mysql.connector

# 連接到資料庫
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password="12345678",
    database="attractions"
)
cursor = conn.cursor()

# 創建訂單表
cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        order_number VARCHAR(255) NOT NULL,
        order_date DATE NOT NULL,
        price INT NOT NULL,
        status ENUM('UNPAID', 'PAID') DEFAULT 'UNPAID',
        attraction_id INT NOT NULL,
        attraction_name VARCHAR(255) NOT NULL,
        attraction_address VARCHAR(255) NOT NULL,
        attraction_image VARCHAR(255) NOT NULL,
        trip_date DATE NOT NULL,
        trip_time VARCHAR(50) NOT NULL,
        contact_name VARCHAR(255) NOT NULL,
        contact_email VARCHAR(255) NOT NULL,
        contact_phone VARCHAR(255) NOT NULL,
        FOREIGN KEY (attraction_id) REFERENCES attractions(id)
    );
""")

conn.commit()

cursor.close()
conn.close()