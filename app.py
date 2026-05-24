
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# 👇 Sample student database (you will extend to 60 later)
students = {
    "101": {
        "dob": "01-01-2005",
        "name": "Arun",
        "attendance": "92%",
        "marks": {"Maths": 85, "Physics": 78, "Chemistry": 88}
    },
    "102": {
        "dob": "02-01-2005",
        "name": "Kavi",
        "attendance": "85%",
        "marks": {"Maths": 65, "Physics": 70, "Chemistry": 60}
    }
}

def format_report(student):
    msg = f"Name: {student['name']}\n"
    msg += f"Attendance: {student['attendance']}\n\nMarks:\n"
    for sub, mark in student["marks"].items():
        msg += f"{sub}: {mark}\n"
    return msg

@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.form.get("Body").strip()
    parts = incoming_msg.split()

    response = MessagingResponse()
    reply = response.message()

    if len(parts) != 2:
        reply.body("Send like: 101 01-01-2005")
        return str(response)

    reg_no, dob = parts

    if reg_no in students and students[reg_no]["dob"] == dob:
        reply.body(format_report(students[reg_no]))
    else:
        reply.body("Invalid Reg No or DOB")

    return str(response)

if __name__ == "__main__":
    app.run(port=5000)