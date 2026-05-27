from flask import Flask, request, render_template, redirect, url_for, session
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "admin123"

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# 📌 Load Excel file
df = pd.read_excel("students.xlsx")

# 🟢 Clean data once (IMPORTANT)
df["reg_no"] = df["reg_no"].astype(str).str.strip()
df["dob"] = pd.to_datetime(df["dob"], dayfirst=True).dt.strftime("%d-%m-%Y")

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
    if search:
        filtered = df[df["reg_no"].str.contains(search, case=False)]
    else:
        filtered = df
    students = filtered.to_dict(orient="records")
    return render_template("dashboard.html", students=students, search=search)

# 🟢 Edit student route
@app.route("/edit/<reg_no>", methods=["GET", "POST"])
def edit_student(reg_no):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    global df
    student = df[df["reg_no"] == reg_no]
    if student.empty:
        return "Student not found"
    if request.method == "POST":
        df.loc[df["reg_no"] == reg_no, "attendance"] = request.form.get("attendance")
        df.loc[df["reg_no"] == reg_no, "maths"] = request.form.get("maths")
        df.loc[df["reg_no"] == reg_no, "physics"] = request.form.get("physics")
        df.loc[df["reg_no"] == reg_no, "chemistry"] = request.form.get("chemistry")
        df.to_excel("students.xlsx", index=False)
        return redirect(url_for("dashboard"))
    s = student.iloc[0]
    return render_template("edit_student.html", student=s)

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

    # 🔍 search student
    student = df[df["reg_no"] == reg_no]

    if not student.empty:
        stored_dob = str(student.iloc[0]["dob"])[:10].strip()

        if stored_dob == dob.strip():
            s = student.iloc[0]

            msg = f"Name: {s['name']}\n"
            msg += f"Attendance: {s['attendance']}%\n\n"
            msg += f"Marks:\n"
            msg += f"Maths: {s['maths']}\n"
            msg += f"Physics: {s['physics']}\n"
            msg += f"Chemistry: {s['chemistry']}"

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