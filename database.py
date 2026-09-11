import sqlite3
import os
from datetime import datetime

# Database file path
DB_PATH = "floraatlas.db"

def get_connection():
    """Create and return a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)

def initialize_database():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create admin table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Create plant table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plant (
            plant_id TEXT PRIMARY KEY,
            plant_name TEXT NOT NULL,
            scientific_name TEXT,
            kingdom TEXT,
            family TEXT,
            species TEXT,
            category TEXT,
            description TEXT,
            medicinal_uses TEXT,
            environmental_benefits TEXT,
            image_path TEXT,
            qr_code_id TEXT UNIQUE,
            latitude REAL,
            longitude REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default admin account if it doesn't exist
    cursor.execute('SELECT * FROM admin WHERE username = ?', ('admin',))
    if cursor.fetchone() is None:
        # In a real project, you would hash this password
        # For learning purposes, we're using plain text
        cursor.execute(
            'INSERT INTO admin (username, password) VALUES (?, ?)',
            ('admin', 'admin123')
        )
        print("Default admin account created: username='admin', password='admin123'")
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def add_plant(plant_data):
    """Add a new plant to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO plant (
                plant_id, plant_name, scientific_name, kingdom, family,
                species, category, description, medicinal_uses,
                environmental_benefits, image_path, qr_code_id,
                latitude, longitude
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            plant_data['plant_id'],
            plant_data['plant_name'],
            plant_data['scientific_name'],
            plant_data['kingdom'],
            plant_data['family'],
            plant_data['species'],
            plant_data['category'],
            plant_data['description'],
            plant_data['medicinal_uses'],
            plant_data['environmental_benefits'],
            plant_data['image_path'],
            plant_data['qr_code_id'],
            plant_data['latitude'],
            plant_data['longitude']
        ))
        conn.commit()
        return True, "Plant added successfully!"
    except sqlite3.IntegrityError as e:
        if 'UNIQUE constraint failed: plant.plant_id' in str(e):
            return False, "Plant ID already exists. Please use a different ID."
        elif 'UNIQUE constraint failed: plant.qr_code_id' in str(e):
            return False, "QR Code ID already exists. Please use a different QR ID."
        else:
            return False, f"Database error: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def get_all_plants():
    """Get all plants from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM plant ORDER BY plant_name')
    plants = cursor.fetchall()
    conn.close()
    return plants

def get_plant_by_id(plant_id):
    """Get a plant by its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM plant WHERE plant_id = ?', (plant_id,))
    plant = cursor.fetchone()
    conn.close()
    return plant

def get_plant_by_qr(qr_code_id):
    """Get a plant by its QR Code ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM plant WHERE qr_code_id = ?', (qr_code_id,))
    plant = cursor.fetchone()
    conn.close()
    return plant

def update_plant(plant_id, plant_data):
    """Update an existing plant."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE plant SET
                plant_name = ?,
                scientific_name = ?,
                kingdom = ?,
                family = ?,
                species = ?,
                category = ?,
                description = ?,
                medicinal_uses = ?,
                environmental_benefits = ?,
                image_path = ?,
                qr_code_id = ?,
                latitude = ?,
                longitude = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE plant_id = ?
        ''', (
            plant_data['plant_name'],
            plant_data['scientific_name'],
            plant_data['kingdom'],
            plant_data['family'],
            plant_data['species'],
            plant_data['category'],
            plant_data['description'],
            plant_data['medicinal_uses'],
            plant_data['environmental_benefits'],
            plant_data['image_path'],
            plant_data['qr_code_id'],
            plant_data['latitude'],
            plant_data['longitude'],
            plant_id
        ))
        conn.commit()
        return True, "Plant updated successfully!"
    except sqlite3.IntegrityError as e:
        if 'UNIQUE constraint failed: plant.qr_code_id' in str(e):
            return False, "QR Code ID already exists. Please use a different QR ID."
        else:
            return False, f"Database error: {str(e)}"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def delete_plant(plant_id):
    """Delete a plant from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM plant WHERE plant_id = ?', (plant_id,))
        conn.commit()
        return True, "Plant deleted successfully!"
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

def search_plants(search_term, category=None):
    """Search for plants by name, scientific name, or category."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT * FROM plant 
        WHERE plant_name LIKE ? 
        OR scientific_name LIKE ?
        OR description LIKE ?
    """
    params = [f'%{search_term}%', f'%{search_term}%', f'%{search_term}%']
    
    if category and category != "All":
        query += " AND category = ?"
        params.append(category)
    
    query += " ORDER BY plant_name"
    
    cursor.execute(query, params)
    plants = cursor.fetchall()
    conn.close()
    return plants

def get_all_categories():
    """Get all unique categories from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT category FROM plant WHERE category IS NOT NULL AND category != "" ORDER BY category')
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories

def admin_login(username, password):
    """Check if admin credentials are correct."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admin WHERE username = ? AND password = ?', (username, password))
    admin = cursor.fetchone()
    conn.close()
    return admin is not None

def get_total_plants():
    """Get the total number of plants in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM plant')
    count = cursor.fetchone()[0]
    conn.close()
    return count

# If you run this file directly, initialize the database
if __name__ == "__main__":
    initialize_database()