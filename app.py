from flask import Flask, request, render_template, redirect, url_for, session
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
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
    if search:
        students = conn.execute("SELECT * FROM students WHERE reg_no LIKE ?", (f"%{search}%",)).fetchall()
    else:
        students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return render_template("dashboard.html", students=students, search=search)

@app.route("/edit/<reg_no>", methods=["GET", "POST"])
def edit_student(reg_no):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        conn.execute(
            "UPDATE students SET attendance=?, maths=?, physics=?, chemistry=?, phone=?, parent_name=? WHERE reg_no=?",
            (
                int(request.form.get("attendance")),
                int(request.form.get("maths")),
                int(request.form.get("physics")),
                int(request.form.get("chemistry")),
                request.form.get("phone"),
                request.form.get("parent_name"),
                reg_no
            )
        )
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))
    student = conn.execute("SELECT * FROM students WHERE reg_no=?", (reg_no,)).fetchone()
    conn.close()
    if not student:
        return "Student not found"
    return render_template("edit_student.html", student=student)

@app.route("/add", methods=["GET", "POST"])
def add_student():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    if request.method == "POST":
        conn = get_db()
        conn.execute(
            "INSERT INTO students (reg_no, name, dob, attendance, maths, physics, chemistry, phone, parent_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                request.form.get("reg_no"),
                request.form.get("name"),
                request.form.get("dob"),
                int(request.form.get("attendance")),
                int(request.form.get("maths")),
                int(request.form.get("physics")),
                int(request.form.get("chemistry")),
                request.form.get("phone"),
                request.form.get("parent_name")
            )
        )
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))
    return render_template("add_student.html")

@app.route("/delete/<reg_no>")
def delete_student(reg_no):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    conn = get_db()
    conn.execute("DELETE FROM students WHERE reg_no=?", (reg_no,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/send_warnings")
def send_warnings():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    conn = get_db()
    low_attendance = conn.execute("SELECT * FROM students WHERE attendance < 75 AND phone IS NOT NULL").fetchall()
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
            except:
                pass
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
    student = conn.execute("SELECT * FROM students WHERE reg_no=?", (reg_no,)).fetchone()
    conn.close()
    if student:
        stored_dob = str(student["dob"])[:10].strip()
        if stored_dob == dob.strip():
            msg = "Name: " + str(student["name"]) + "\n"
            msg += "Attendance: " + str(student["attendance"]) + "%\n\n"
            msg += "Marks:\n"
            msg += "Maths: " + str(student["maths"]) + "\n"
            msg += "Physics: " + str(student["physics"]) + "\n"
            msg += "Chemistry: " + str(student["chemistry"])
            reply.body(msg)
        else:
            reply.body("Invalid DOB")
    else:
        reply.body("Invalid Reg No")
    return str(response)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)