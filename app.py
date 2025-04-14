import streamlit as st
import pandas as pd

# Set page title and layout
st.set_page_config(page_title="Advising Tool Demo", layout="centered")

# Custom CSS for look and feel inspired by Mineral Area College
st.markdown("""
    <style>
    .main { background-color: #ffffff; padding: 20px; }
    .stSelectbox, .stCheckbox { margin-bottom: 15px; }
    .stButton>button { background-color: #003366; color: white; border-radius: 5px; padding: 8px 16px; font-weight: bold; }
    .section-divider { border-top: 1px solid #cccccc; margin: 20px 0; }
    .card { background-color: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    h1, h2, h3 { font-family: 'Arial', sans-serif; color: #003366; }
    p, div { font-family: 'Arial', sans-serif; color: #333333; }
    </style>
""", unsafe_allow_html=True)

# Title
st.markdown("<div class='card'><h1>First-Year Student Advising Tool 📚</h1></div>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 16px;'>Set your student up for success with a balanced schedule!</p>", unsafe_allow_html=True)

# Load data
try:
    students = pd.read_excel("data/Student Data.xlsx")
    courses = pd.read_excel("data/full_atu_course_pass_rates_combined.xlsx")
except:
    st.error("Error: Please ensure 'Student Data.xlsx' and 'full_atu_course_pass_rates_combined.xlsx' are in the 'data' folder.")
    st.stop()

# Calculate DFW rate (kept internal)
courses["DFW Rate (%)"] = 100 - courses["pass_rate"].str.rstrip("%").astype(float)

# Select student
st.markdown("<div class='card'><h2>Select a Student</h2></div>", unsafe_allow_html=True)
student_ids = students["Student ID"].astype(str).tolist()
selected_student = st.selectbox("Choose a student:", student_ids, help="Select a student by their ID.")
student_data = students[students["Student ID"] == int(selected_student)].iloc[0]

# Display minimal student info
st.write(f"**Student ID**: {selected_student}")

# Divider
st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

# Select courses
st.markdown("<div class='card'><h2>Build Schedule 📋</h2></div>", unsafe_allow_html=True)
course_options = courses["course_name"].tolist()
if "num_courses" not in st.session_state:
    st.session_state.num_courses = 4

if st.button("Add another course", help="Add a slot for an extra course."):
    st.session_state.num_courses += 1

selected_courses = []
for i in range(st.session_state.num_courses):
    course = st.selectbox(f"Course {i + 1}", ["Select a course"] + course_options, key=f"course_{i}", help="Choose a course for the schedule.")
    if course != "Select a course":
        selected_courses.append(course)

# Calculate schedule difficulty
if selected_courses:
    schedule_df = courses[courses["course_name"].isin(selected_courses)][["course_name"]]
    avg_dfw = courses[courses["course_name"].isin(selected_courses)]["DFW Rate (%)"].mean()
    st.markdown("<div class='card'><h3>Selected Schedule</h3></div>", unsafe_allow_html=True)
    st.table(schedule_df.rename(columns={"course_name": "Course Name"}))

    # Calculate challenge score
    gpa_score = (student_data["High School GPA"] / 4.0) * 40
    rank_str = student_data["High School Class Rank"]
    position, total = map(int, rank_str.split("/"))
    rank_score = (1 - position / total) * 30
    act_score = (student_data["ACT Composite"] / 36) * 20
    college_gpa = student_data.get("College GPA", None)
    dual_bonus = 5 if pd.notnull(college_gpa) else 0
    first_gen_penalty = -5 if student_data["First Generation College Student"] == "yes" else 0
    student_strength = gpa_score + rank_score + act_score + dual_bonus + first_gen_penalty
    challenge_score = (avg_dfw / 100) * (1 - student_strength / 100)

    # Tutoring option
    tutoring = st.checkbox("Reviewed tutoring/support options ✅", help="Check if tutoring or support was discussed to ease the schedule.")
    if tutoring:
        challenge_score *= 0.5  # Reduce challenge by 50%

    # Determine stop light rating
    if challenge_score < 0.15:
        risk = "Low Risk"
        color = "#28a745"  # Green
        message = "Great fit! This schedule aligns well with the student's preparation."
    elif challenge_score < 0.35:
        risk = "Moderate Risk"
        color = "#ffc107"  # Yellow
        message = "Manageable with support. Review courses or add tutoring."
    else:
        risk = "High Risk"
        color = "#a6192e"  # Red from Mineral Area
        message = "Ambitious schedule! Consider tutoring or adjusting courses to ensure success."

    # Display result
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.markdown("<div class='card'><h2>Schedule Assessment</h2></div>", unsafe_allow_html=True)
    st.markdown(f"**Challenge Level**: <span style='color:{color}; font-weight:bold;'>{risk}</span>", unsafe_allow_html=True)
    st.write(message)
    if tutoring:
        st.write("Tutoring/support added—schedule now feels more manageable!")
else:
    st.write("Please select at least one course to assess the schedule.")
