from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pyodbc
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_development_secret_key")

# --- DATABASE CONNECTION ---
# Uses environment variables from Azure App Service
def get_db_connection():
    # Recommended: Use Managed Identity or ODBC Connection String
    conn_str = os.getenv("SQL_CONNECTION_STRING")
    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"Database Connection Error: {e}")
        return None

# --- AUTHENTICATION DECORATORS ---
# Ensures only specific roles can access certain routes
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
            return "Access Denied: Educator role required.", 403
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

# LOGIN (Question 2b: Authentication)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Simple simulation: in a real app, verify against the Users table
        username = request.form['username']
        role = request.form['role'] # 'Educator' or 'Learner'
        session['user'] = username
        session['role'] = role
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# DASHBOARD (Question 2: Role-Based Access)
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Courses")
    courses = cursor.fetchall()
    return render_template('dashboard.html', courses=courses, role=session['role'])

# --- CRUD OPERATIONS (Question 2a: 10 Marks) ---

# CREATE: Add Course (Educator Only)
@app.route('/course/add', methods=['POST'])
@login_required
@educator_only
def add_course():
    title = request.form['title']
    description = request.form['description']
    educator = session['user']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Courses (Title, Description, Educator) VALUES (?, ?, ?)", 
                   (title, description, educator))
    conn.commit()
    return redirect(url_for('dashboard'))

# UPDATE: Edit Course (Educator Only)
@app.route('/course/update/<int:id>', methods=['POST'])
@login_required
@educator_only
def update_course(id):
    new_title = request.form['title']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Courses SET Title = ? WHERE id = ?", (new_title, id))
    conn.commit()
    return redirect(url_for('dashboard'))

# DELETE: Remove Course (Educator Only)
@app.route('/course/delete/<int:id>', methods=['POST'])
@login_required
@educator_only
def delete_course(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Courses WHERE id = ?", (id))
    conn.commit()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Use port 8000 for Azure App Service compatibility
    app.run(host='0.0.0.0', port=8000)