import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Student Schedule Difficulty", layout="centered")
st.title("🎓 Student Schedule Difficulty Estimator")

# Load data
@st.cache_data
def load_data():
    student_data = pd.read_excel("data/Student Data.xlsx")
    course_history = pd.read_excel("data/student_course_history.xlsx")
    course_pass_rates = pd.read_excel("data/full_atu_course_pass_rates.xlsx")
    course_pass_rates["course_code"] = course_pass_rates["course_name"].str.extract(r"(^[A-Z]{2,4} \d{4})")
    return student_data, course_history, course_pass_rates

student_data, course_history, course_pass_rates = load_data()

# Student selection
student_ids = student_data["Student ID"].tolist()
selected_id = st.selectbox("Select Student ID", student_ids)

student_profile = student_data[student_data["Student ID"] == selected_id].iloc[0]

# Course selection
available_courses = course_pass_rates["course_code"].dropna().unique().tolist()
selected_courses = st.multiselect("Select the student's planned schedule (4-6 courses)", options=sorted(available_courses))

# Calculate if there are at least 1 course selected
if selected_courses:
    def get_pass_rate(course_code):
        match = course_pass_rates[course_pass_rates["course_code"] == course_code]
        return int(match.iloc[0]["pass_rate"].replace('%', '')) if not match.empty else 70

    pass_rates = [(c, get_pass_rate(c)) for c in selected_courses]

    # Student metrics
    hs_gpa = float(student_profile["High School GPA"])
    rank_str = student_profile["High School Class Rank"]
    rank_num, rank_den = map(int, rank_str.split('/'))
    rank_pct = 100 * (rank_den - rank_num) / rank_den
    college_gpa = student_profile["College GPA"] if not pd.isna(student_profile["College GPA"]) else 0
    act = student_profile["ACT Composite"]
    act_math = student_profile["ACT MATH"]

    # Scoring logic
    avg_difficulty = sum([100 - r for _, r in pass_rates]) / len(pass_rates)
    total_score = (
        (hs_gpa / 4.0) * 20 +
        (rank_pct / 100) * 10 +
        (college_gpa / 4.0) * 20 +
        (act / 36) * 10 +
        (act_math / 36) * 10 +
        max(0, 30 - avg_difficulty)
    )

    # Risk level
    if total_score >= 80:
        risk = "🟢 Low Risk"
    elif total_score >= 60:
        risk = "🟡 Moderate Risk"
    else:
        risk = "🔴 High Risk"

    st.subheader(f"Overall Difficulty Score: {total_score:.1f} / 100")
    st.markdown(f"### {risk}")

    # Course warnings
    st.divider()
    st.subheader("⚠️ Courses to Reconsider")
    math_keywords = ['MATH', 'STAT', 'QUANT']
    flagged = []
    for course, rate in pass_rates:
        reasons = []
        if rate < 50:
            reasons.append("Low pass rate")
        if any(k in course for k in math_keywords) and act_math < 22:
            reasons.append("Math-heavy course with low ACT Math")
        if course in ["MATH 2223", "ACCT 2013", "MGMT 3003"]:
            reasons.append("Multiple prerequisites")
        if reasons:
            flagged.append((course, reasons))

    if not flagged:
        st.success("No flagged courses in this schedule.")
    else:
        for course, reasons in flagged:
            st.error(f"**{course}**: " + ", ".join(reasons))
else:
    st.info("Please select at least one course to evaluate.")

