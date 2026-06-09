@app.route("/edit/<reg_no>", methods=["GET", "POST"])
def edit_student(reg_no):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    conn = get_db()
    if request.method == "POST":
        conn.execute(
            "UPDATE students SET attendance=?, phone=?, parent_name=? WHERE reg_no=?",
            (
                int(request.form.get("attendance")),
                request.form.get("phone"),
                request.form.get("parent_name"),
                reg_no
            )
        )
        # Update exam marks
        for key, value in request.form.items():
            if key.startswith("mark_"):
                exam_mark_id = key.replace("mark_", "")
                if value.strip() != "":
                    conn.execute(
                        "UPDATE exam_marks SET mark=? WHERE id=?",
                        (int(value), int(exam_mark_id))
                    )
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))

    student = conn.execute("SELECT * FROM students WHERE reg_no=?", (reg_no,)).fetchone()
    raw_exams = conn.execute(
        "SELECT e.id, e.exam_name, e.mark, s.subject_name, s.max_marks FROM exam_marks e JOIN subjects s ON e.subject_id = s.id WHERE e.reg_no=? ORDER BY e.exam_name",
        (reg_no,)
    ).fetchall()
    conn.close()

    exams = {}
    for row in raw_exams:
        if row["exam_name"] not in exams:
            exams[row["exam_name"]] = []
        exams[row["exam_name"]].append(row)

    if not student:
        return "Student not found"
    return render_template("edit_student.html", student=student, exams=exams)