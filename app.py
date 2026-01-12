from flask import Flask, render_template, request, redirect, url_for, session
import pyodbc
import os
from functools import wraps

app = Flask(__name__)
# Fetches the secret key from your Azure Environment Variables
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_development_secret_key")

# --- DATABASE CONNECTION ---
def get_db_connection():
    # Uses the SQL_CONNECTION_STRING defined in Azure Configuration
    conn_str = os.getenv("SQL_CONNECTION_STRING")
    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"Database Connection Error: {e}")
        return None

# --- AUTHENTICATION DECORATORS (Question 2b: 5 Marks) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def educator_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'Educator':
            # Role-Based Access Control implementation
            return "Access Denied: Educator role required.", 403
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = request.form['username']
        session['role'] = request.form['role']
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    if not conn:
        return "Database connection failed. Please check Azure Networking settings.", 500
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Courses")
    courses = cursor.fetchall()
    conn.close() # Prevents database connection leaks
    return render_template('dashboard.html', courses=courses, role=session['role'])

# --- CRUD OPERATIONS (Question 2a: 10 Marks) ---

@app.route('/course/add', methods=['POST'])
@login_required
@educator_only
def add_course():
    title = request.form['title']
    description = request.form.get('description', '')
    educator = session['user']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Courses (Title, Description, Educator) VALUES (?, ?, ?)", 
                   (title, description, educator))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/course/update/<int:id>', methods=['POST'])
@login_required
@educator_only
def update_course(id):
    new_title = request.form['title']
    conn = get_db_connection()
    cursor = conn.cursor()
    # Critical Fix: (new_title, id) tuple ensures correct SQL execution
    cursor.execute("UPDATE Courses SET Title = ? WHERE id = ?", (new_title, id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/course/delete/<int:id>', methods=['POST'])
@login_required
@educator_only
def delete_course(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Critical Fix: (id,) tuple with trailing comma is required for single parameters
    cursor.execute("DELETE FROM Courses WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Azure App Service default port compatibility
    app.run(host='0.0.0.0', port=8000)