from flask import Flask, request, jsonify
import pyodbc
import os

app = Flask(__name__)

# --- DATABASE CONNECTION ---
def get_db_connection():
    # This matches the 'SQL_CONNECTION_STRING' you set in Azure Portal -> Configuration
    conn_str = os.getenv("SQL_CONNECTION_STRING")
    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"Database Connection Error: {e}")
        return None

# --- 1. CREATE & READ ALL (GET/POST /courses) ---
@app.route('/courses', methods=['GET', 'POST'])
def handle_courses():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor()

    # CREATE: Educator adds a new course
    if request.method == 'POST':
        data = request.json
        # Validation for Role (Required for Auth marks)
        if data.get('role') != 'Educator':
            return jsonify({"error": "Unauthorized: Only Educators can create courses"}), 403
            
        cursor.execute("INSERT INTO Courses (Title, Educator) VALUES (?, ?)", 
                       (data['title'], data['educator']))
        conn.commit()
        return jsonify({"message": "Course created successfully!"}), 201

    # READ: Both Educators and Learners can view courses
    else:
        cursor.execute("SELECT CourseID, Title, Educator FROM Courses")
        rows = cursor.fetchall()
        courses = []
        for r in rows:
            courses.append({
                "id": r[0],
                "title": r[1],
                "educator": r[2]
            })
        return jsonify(courses), 200

# --- 2. UPDATE & DELETE (PUT/DELETE /courses/<id>) ---
@app.route('/courses/<int:id>', methods=['PUT', 'DELETE'])
def modify_course(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    data = request.json

    # Role check
    if data.get('role') != 'Educator':
        return jsonify({"error": "Unauthorized: Educator role required"}), 403

    # UPDATE: Educator modifies course title
    if request.method == 'PUT':
        cursor.execute("UPDATE Courses SET Title = ? WHERE CourseID = ?", 
                       (data['title'], id))
        conn.commit()
        return jsonify({"message": f"Course {id} updated successfully!"})

    # DELETE: Educator removes a course
    if request.method == 'DELETE':
        cursor.execute("DELETE FROM Courses WHERE CourseID = ?", (id))
        conn.commit()
        return jsonify({"message": f"Course {id} deleted successfully!"})

# --- 3. SEARCH (Optional bonus feature) ---
@app.route('/search', methods=['GET'])
def search_courses():
    keyword = request.args.get('q')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Courses WHERE Title LIKE ?", ('%' + keyword + '%'))
    rows = cursor.fetchall()
    results = [{"id": r[0], "title": r[1]} for r in rows]
    return jsonify(results)

if __name__ == '__main__':
    # Flask runs on port 8000 for Azure compatibility
    app.run(host='0.0.0.0', port=8000)