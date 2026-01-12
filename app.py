from flask import Flask, render_template, request, redirect, url_for, session
import pyodbc
import os
from functools import wraps

app = Flask(__name__)
# Secret key for session security
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_development_secret_key")

# --- DATABASE CONNECTION ---
def get_db_connection():
    # Ensure this matches your Azure App Service Environment Variable
    conn_str = os.getenv("SQL_CONNECTION_STRING")
    try:
        # Using ODBC Driver 17 for standard Azure compatibility
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"Database Connection Error: {e}")
        return None

# --- AUTHENTICATION DECORATORS (Question 2b) ---
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
        # Checks the UserRole retrieved from your Users table
        if session.get('role') != 'Educator':
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
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        if not conn:
            return "Database Error.", 500
            
        cursor = conn.cursor()
        # Verifying against your real Users table
        cursor.execute("SELECT Username, UserRole FROM Users WHERE Username = ? AND Password = ?", 
                       (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = user[0]
            session['role'] = user[1]
            return redirect(url_for('dashboard'))
        else:
            return "Invalid login credentials.", 401
            
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Courses")
    courses = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', courses=courses, role=session['role'])

# --- CRUD OPERATIONS (Question 2a) ---

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
    try:
        new_title = request.form['title']
        conn = get_db_connection()
        cursor = conn.cursor()
        # Updated to use 'CourseID' to match your database
        cursor.execute("UPDATE Courses SET Title = ? WHERE CourseID = ?", (new_title, id))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    except Exception as e:
        return f"Update Error: {str(e)}", 500

@app.route('/course/delete/<int:id>', methods=['POST'])
@login_required
@educator_only
def delete_course(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Updated to use 'CourseID' and correct tuple
        cursor.execute("DELETE FROM Courses WHERE CourseID = ?", (id,))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    except Exception as e:
        return f"Delete Error: {str(e)}", 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)