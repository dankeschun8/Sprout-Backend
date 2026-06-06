# Connecting Supabase Database to Flask Backend

A comprehensive guide for integrating Supabase PostgreSQL database with Flask for executing SELECT queries.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Setup and Installation](#setup-and-installation)
- [Connection Methods](#connection-methods)
- [Basic Query Examples](#basic-query-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Python 3.7+
- Flask installed
- Supabase project created
- Database connection credentials from Supabase

## Setup and Installation

### 1. Install Required Packages

```bash
pip install flask psycopg2-binary python-dotenv
```

Or for async support:

```bash
pip install flask psycopg2-binary python-dotenv asyncpg
```

### 2. Get Supabase Connection String

Navigate to your Supabase project:
1. Go to **Project Settings** → **Database**
2. Find **Connection String** section
3. Copy the **URI** (Connection Pooling or Direct Connection)

The format looks like:
```
postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

### 3. Environment Variables

Create a `.env` file in your project root:

```env
SUPABASE_DB_URL=postgresql://postgres:your-password@db.xxxxx.supabase.co:5432/postgres
```

## Connection Methods

### Method 1: Using psycopg2 (Recommended for Simple Queries)

#### Basic Setup

```python
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Database connection function
def get_db_connection():
    conn = psycopg2.connect(
        os.getenv('SUPABASE_DB_URL'),
        cursor_factory=RealDictCursor  # Returns results as dictionaries
    )
    return conn

# Example route
@app.route('/api/users', methods=['GET'])
def get_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('SELECT * FROM users')
        users = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify(users), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
```

#### With Connection Pooling

```python
from psycopg2 import pool
from contextlib import contextmanager

# Initialize connection pool
db_pool = pool.SimpleConnectionPool(
    1,  # minconn
    10,  # maxconn
    os.getenv('SUPABASE_DB_URL')
)

@contextmanager
def get_db_cursor(commit=False):
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        yield cursor
        if commit:
            conn.commit()
    finally:
        cursor.close()
        db_pool.putconn(conn)

# Usage example
@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        with get_db_cursor() as cur:
            cur.execute('SELECT * FROM products WHERE available = true')
            products = cur.fetchall()
        return jsonify(products), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### Method 2: Using SQLAlchemy (Recommended for Complex Applications)

```python
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SUPABASE_DB_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define a model
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime)

# Query example
@app.route('/api/users', methods=['GET'])
def get_users():
    try:
        users = User.query.all()
        users_list = [{
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'created_at': user.created_at.isoformat() if user.created_at else None
        } for user in users]
        return jsonify(users_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Raw SQL with SQLAlchemy
@app.route('/api/custom-query', methods=['GET'])
def custom_query():
    try:
        result = db.session.execute(
            db.text('SELECT * FROM users WHERE created_at > :date'),
            {'date': '2024-01-01'}
        )
        data = [dict(row) for row in result]
        return jsonify(data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
```

## Basic Query Examples

### Simple SELECT Query

```python
@app.route('/api/items', methods=['GET'])
def get_items():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('SELECT id, name, price FROM items')
        items = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify(items), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### Parameterized Query (Prevent SQL Injection)

```python
from flask import request

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Use parameterized query
        cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if user:
            return jsonify(user), 200
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### Query with Multiple Conditions

```python
@app.route('/api/products/search', methods=['GET'])
def search_products():
    category = request.args.get('category')
    min_price = request.args.get('min_price', 0)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = '''
            SELECT * FROM products 
            WHERE category = %s AND price >= %s
            ORDER BY price ASC
        '''
        
        cur.execute(query, (category, min_price))
        products = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify(products), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### JOIN Query

```python
@app.route('/api/orders/<int:user_id>', methods=['GET'])
def get_user_orders(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = '''
            SELECT 
                o.id as order_id,
                o.total,
                o.created_at,
                u.name as customer_name,
                u.email
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE u.id = %s
            ORDER BY o.created_at DESC
        '''
        
        cur.execute(query, (user_id,))
        orders = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify(orders), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### Aggregation Query

```python
@app.route('/api/stats/products', methods=['GET'])
def get_product_stats():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = '''
            SELECT 
                category,
                COUNT(*) as total_products,
                AVG(price) as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price
            FROM products
            GROUP BY category
        '''
        
        cur.execute(query)
        stats = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### Pagination

```python
@app.route('/api/posts', methods=['GET'])
def get_posts():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    offset = (page - 1) * per_page
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get total count
        cur.execute('SELECT COUNT(*) FROM posts')
        total = cur.fetchone()['count']
        
        # Get paginated results
        query = '''
            SELECT * FROM posts 
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
        '''
        cur.execute(query, (per_page, offset))
        posts = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'posts': posts,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## Best Practices

### 1. Use Environment Variables

Never hardcode database credentials. Always use environment variables:

```python
from dotenv import load_dotenv
import os

load_dotenv()
DB_URL = os.getenv('SUPABASE_DB_URL')
```

### 2. Always Close Connections

Use context managers or ensure connections are closed:

```python
try:
    conn = get_db_connection()
    cur = conn.cursor()
    # ... do work
finally:
    if cur:
        cur.close()
    if conn:
        conn.close()
```

### 3. Use Parameterized Queries

Prevent SQL injection by using parameterized queries:

```python
# ✅ GOOD
cur.execute('SELECT * FROM users WHERE email = %s', (email,))

# ❌ BAD
cur.execute(f'SELECT * FROM users WHERE email = {email}')
```

### 4. Handle Errors Gracefully

```python
@app.route('/api/data', methods=['GET'])
def get_data():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM table_name')
        data = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(data), 200
    except psycopg2.Error as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500
```

### 5. Use Connection Pooling for Production

Connection pooling improves performance by reusing connections:

```python
from psycopg2 import pool

db_pool = pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=20,
    dsn=os.getenv('SUPABASE_DB_URL')
)
```

### 6. Enable Row Level Security (RLS)

In Supabase, enable RLS for your tables and create appropriate policies:

```sql
-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Users can view their own data"
ON users FOR SELECT
USING (auth.uid() = id);
```

## Troubleshooting

### Connection Timeout

If you experience connection timeouts, try using connection pooling mode in Supabase:

```
postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:6543/postgres
```

Note the port change from `5432` to `6543` for pooling mode.

### SSL Certificate Issues

If you encounter SSL errors, modify your connection string:

```python
conn = psycopg2.connect(
    os.getenv('SUPABASE_DB_URL'),
    sslmode='require'
)
```

### Import Errors

If `psycopg2` fails to install, try the binary version:

```bash
pip uninstall psycopg2
pip install psycopg2-binary
```

### Column Name Issues

If you're getting key errors when accessing results, ensure you're using `RealDictCursor`:

```python
from psycopg2.extras import RealDictCursor

cur = conn.cursor(cursor_factory=RealDictCursor)
```

## Complete Example Application

```python
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

app = Flask(__name__)

# Database connection helper
@contextmanager
def get_db_cursor():
    conn = psycopg2.connect(
        os.getenv('SUPABASE_DB_URL'),
        cursor_factory=RealDictCursor
    )
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

# Routes
@app.route('/api/users', methods=['GET'])
def get_users():
    try:
        with get_db_cursor() as cur:
            cur.execute('SELECT id, email, name, created_at FROM users')
            users = cur.fetchall()
        return jsonify(users), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        with get_db_cursor() as cur:
            cur.execute(
                'SELECT id, email, name, created_at FROM users WHERE id = %s',
                (user_id,)
            )
            user = cur.fetchone()
        
        if user:
            return jsonify(user), 200
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
```

## Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [psycopg2 Documentation](https://www.psycopg.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

---

**Last Updated:** April 2026
