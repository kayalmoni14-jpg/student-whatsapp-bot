from flask import Flask, request, render_template, redirect, url_for, session
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import psycopg2
import psycopg2.extras
import os
from datetime import date

app = Flask(__name__)
app.secret_key = "admin123"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

def get_db():
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"), sslmode="require")
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            reg_no TEXT PRIMARY KEY,
            name TEXT,
            dob TEXT,
            attendance INTEGER,
            phone TEXT,
            parent_name TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id SERIAL PRIMARY KEY,
            subject_name TEXT,
            max_marks INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exam_marks (
            id SERIAL PRIMARY KEY,
            reg_no TEXT,
            exam_name TEXT,
            subject_id INTEGER,
            mark INTEGER,
            date TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid username or password!"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    search = request.args.get("search", "").strip()
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if search:
        cur.execute("SELECT * FROM students WHERE reg_no LIKE %s", (f"%{search}%",))
    else:
        cur.execute("SELECT * FROM students")
    students = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("dashboard.html", students=students, search=search)

@app.route("/edit/<reg_no>", methods=["GET", "POST"])
def edit_student(reg_no):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method == "POST":
        cur.execute(
            "UPDATE students SET attendance=%s, phone=%s, parent_name=%s WHERE reg_no=%s",
            (
                int(request.form.get("attendance")),
                request.form.get("phone"),
                request.form.get("parent_name"),
                reg_no
            )
        )
        for key, value in request.form.items():
            if key.startswith("mark_"):
                exam_mark_id = key.replace("mark_", "")
                if value.strip() != "":
                    cur.execute(
                        "UPDATE exam_marks SET mark=%s WHERE id=%s",
                        (int(value), int(exam_mark_id))
                    )
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("dashboard"))
    cur.execute("SELECT * FROM students WHERE reg_no=%s", (reg_no,))
    student = cur.fetchone()
    cur.execute(
        "SELECT e.id, e.exam_name, e.mark, s.subject_name, s.max_marks FROM exam_marks e JOIN subjects s ON e.subject_id = s.id WHERE e.reg_no=%s ORDER BY e.exam_name",
        (reg_no,)
    )
    raw_exams = cur.fetchall()
    cur.close()
    conn.close()
    exams = {}
    for row in raw_exams:
        if row["exam_name"] not in exams:
            exams[row["exam_name"]] = []
        exams[row["exam_name"]].append(row)
    if not student:
        return "Student not found"
    return render_template("edit_student.html", student=student, exams=exams)

@app.route("/add", methods=["GET", "POST"])
def add_student():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO students (reg_no, name, dob, attendance, phone, parent_name) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                request.form.get("reg_no"),
                request.form.get("name"),
                request.form.get("dob"),
                int(request.form.get("attendance")),
                request.form.get("phone"),
                request.form.get("parent_name")
            )
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("dashboard"))
    return render_template("add_student.html")

@app.route("/delete/<reg_no>")
def delete_student(reg_no):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE reg_no=%s", (reg_no,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/subjects", methods=["GET", "POST"])
def subjects():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method == "POST":
        cur.execute(
            "INSERT INTO subjects (subject_name, max_marks) VALUES (%s, %s)",
            (
                request.form.get("subject_name"),
                int(request.form.get("max_marks"))
            )
        )
        conn.commit()
    cur.execute("SELECT * FROM subjects")
    subjects = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("subjects.html", subjects=subjects)

@app.route("/delete_subject/<int:subject_id>")
def delete_subject(subject_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM subjects WHERE id=%s", (subject_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("subjects"))

@app.route("/add_exam/<reg_no>", methods=["GET", "POST"])
def add_exam(reg_no):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method == "POST":
        exam_name = request.form.get("exam_name")
        cur.execute("SELECT * FROM subjects")
        subjects = cur.fetchall()
        today = str(date.today())
        for subject in subjects:
            mark = request.form.get("mark_" + str(subject["id"]))
            if mark:
                cur.execute(
                    "INSERT INTO exam_marks (reg_no, exam_name, subject_id, mark, date) VALUES (%s, %s, %s, %s, %s)",
                    (reg_no, exam_name, subject["id"], int(mark), today)
                )
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("dashboard"))
    cur.execute("SELECT * FROM students WHERE reg_no=%s", (reg_no,))
    student = cur.fetchone()
    cur.execute("SELECT * FROM subjects")
    subjects = cur.fetchall()
    cur.execute(
        "SELECT e.exam_name, e.mark, e.date, s.subject_name, s.max_marks FROM exam_marks e JOIN subjects s ON e.subject_id = s.id WHERE e.reg_no=%s ORDER BY e.exam_name",
        (reg_no,)
    )
    raw_exams = cur.fetchall()
    cur.close()
    conn.close()
    exams = {}
    for row in raw_exams:
        if row["exam_name"] not in exams:
            exams[row["exam_name"]] = []
        exams[row["exam_name"]].append(row)
    return render_template("add_exam.html", student=student, subjects=subjects, exams=exams)

@app.route("/send_warnings")
def send_warnings():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM students WHERE attendance < 75 AND phone IS NOT NULL")
    low_attendance = cur.fetchall()
    cur.close()
    conn.close()
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    client = Client(account_sid, auth_token)
    for student in low_attendance:
        if student["phone"]:
            try:
                msg = "Warning: Dear " + str(student["parent_name"] or "Parent") + ", your child " + str(student["name"]) + " has low attendance of " + str(student["attendance"]) + "%. Please take action!"
                client.messages.create(
                    from_="whatsapp:+14155238886",
                    to="whatsapp:" + str(student["phone"]),
                    body=msg
                )
             except Exception as e:
            print("Failed to send warning to", student["reg_no"], "-", str(e))
                
    return redirect(url_for("dashboard"))

@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.form.get("Body")
    response = MessagingResponse()
    reply = response.message()
    if not incoming_msg:
        reply.body("No input received")
        return str(response)
    parts = incoming_msg.strip().replace("\t", " ").split()
    if len(parts) != 2:
        reply.body("Send like: 101 01-01-2005")
        return str(response)
    reg_no, dob = parts
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM students WHERE reg_no=%s", (reg_no,))
    student = cur.fetchone()
    if student:
        stored_dob = str(student["dob"])[:10].strip()
        if stored_dob == dob.strip():
            cur.execute(
                "SELECT e.exam_name, e.mark, s.subject_name, s.max_marks FROM exam_marks e JOIN subjects s ON e.subject_id = s.id WHERE e.reg_no=%s ORDER BY e.exam_name",
                (reg_no,)
            )
            exams = cur.fetchall()
            msg = "Name: " + str(student["name"]) + "\n"
            msg += "Attendance: " + str(student["attendance"]) + "%\n\n"
            if exams:
                current_exam = ""
                for exam in exams:
                    if exam["exam_name"] != current_exam:
                        current_exam = exam["exam_name"]
                        msg += "\n" + current_exam + ":\n"
                    msg += exam["subject_name"] + ": " + str(exam["mark"]) + "/" + str(exam["max_marks"]) + "\n"
            else:
                msg += "No exam marks added yet."
            reply.body(msg)
        else:
            reply.body("Invalid DOB")
    else:
        reply.body("Invalid Reg No")
    cur.close()
    conn.close()
    return str(response)

with app.app_context():
    init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)