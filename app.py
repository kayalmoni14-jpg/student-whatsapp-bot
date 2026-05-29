from flask import Flask, request, render_template, redirect, url_for, session
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "admin123"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

def get_db():
    conn = sqlite3.connect("students.db")
    conn.row_factory = sqlite3.Row
    return conn

# 🟢 Home route
@app.route("/")
def home():
    return redirect(url_for("login"))

# 🟢 Login route
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

# 🟢 Logout route
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# 🟢 Dashboard route
@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    search = request.args.get("search", "").strip()
    conn = get_db()
    if search:
        students = conn.execute(
            "SELECT * FROM students WHERE reg_no LIKE ?",
            (f"%{search}%",)
        ).fetchall()
    else:
        students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return render_template("dashboard.html", students=students, search=search)

# 🟢 Edit student route
@app.route("/edit/<reg_no>", methods=["GET", "POST"])
def edit_student(reg_no):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        conn.execute(
            "UPDATE students SET attendance=?, maths=?, physics=?, chemistry=? WHERE reg_no=?",
            (
                int(request.form.get("attendance")),
                int(request.form.get("maths")),
                int(request.form.get("physics")),
                int(request.form.get("chemistry")),
                reg_no
            )
        )
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))
    student = conn.execute(
        "SELECT * FROM students WHERE reg_no=?", (reg_no,)
    ).fetchone()
    conn.close()
    if not student:
        return "Student not found"
    return render_template("edit_student.html", student=student)

# 🟢 WhatsApp route
@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.form.get("Body")

    response = MessagingResponse()
    reply = response.message()

    if not incoming_msg:
        reply.body("❌ No input received")
        return str(response)

    parts = incoming_msg.strip().replace("\t", " ").split()

    if len(parts) != 2:
        reply.body("❌ Send like: 101 01-01-2005")
        return str(response)

    reg_no, dob = parts

    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE reg_no=?", (reg_no,)
    ).fetchone()
    conn.close()

    if student:
        stored_dob = str(student["dob"])[:10].strip()
        if stored_dob == dob.strip():
            msg = f"Name: {student['name']}\n"
            msg += f"Attendance: {student['attendance']}%\n\n"
            msg += f"Marks:\n"
            msg += f"Maths: {student['maths']}\n"
            msg += f"Physics: {student['physics']}\n"
            msg += f"Chemistry: {student['chemistry']}"
            reply.body(msg)
        else:
            reply.body("❌ Invalid DOB")
    else:
        reply.body("❌ Invalid Reg No")

    return str(response)

# 🟢 Run server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)