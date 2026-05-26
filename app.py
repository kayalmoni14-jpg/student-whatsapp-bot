from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd

app = Flask(__name__)

# 📌 Load Excel file
df = pd.read_excel("students.xlsx")

# 🟢 Clean data once (IMPORTANT)
df["reg_no"] = df["reg_no"].astype(str).str.strip()
df["dob"] = df["dob"].astype(str).str.strip()

# 🟢 Home route
@app.route("/")
def home():
    return "WhatsApp Student Bot is Running"

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
    app.run(host="0.0.0.0", port=10000)