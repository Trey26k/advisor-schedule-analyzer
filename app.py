import streamlit as st
import pandas as pd

# Set page title and layout
st.set_page_config(page_title="Advising Tool Demo", layout="centered")

# Title
st.title("First-Year Student Advising Tool 📚")
st.write("Assess a student's schedule difficulty based on their academic history and course DFW rates.")

# Load data
try:
    students = pd.read_excel("data/Student Data.xlsx")
    courses = pd.read_excel("data/full_atu_course_pass_rates_combined.xlsx")
except:
    st.error("Error: Please ensure 'Student Data.xlsx' and 'full_atu_course_pass_rates_combined.xlsx' are in the 'data' folder.")
    st.stop()

# Calculate DFW rate
courses["DFW Rate (%)"] = 100 - courses["pass_rate"].str.rstrip("%").astype(float)

# Select student
st.header("Select a Student")
student_ids = students["Student ID"].astype(str).tolist()
selected_student = st.selectbox("Choose a student:", student_ids)
student_data = students[students["Student ID"] == int(selected_student)].iloc[0]

# Display student info
st.write(f"**Student ID**: {selected_student}")
st.write(f"**High School GPA**: {student_data['High School GPA']}")
st.write(f"**ACT Composite**: {student_data['ACT Composite']}")
st.write(f"**Class Rank**: {student_data['High School Class Rank']}")
st.write(f"**First Generation**: {student_data['First Generation College Student']}")
college_gpa = student_data.get("College GPA", None)
st.write(f"**Dual Enrollment**: {'Yes' if pd.notnull(college_gpa) else 'No'}")

# Calculate student strength
gpa_score = (student_data["High School GPA"] / 4.0) * 40
rank_str = student_data["High School Class Rank"]
position, total = map(int, rank_str.split("/"))
rank_score = (1 - position / total) * 30
act_score = (student_data["ACT Composite"] / 36) * 20
dual_bonus = 5 if pd.notnull(college_gpa) else 0
first_gen_penalty = -5 if student_data["First Generation College Student"] == "yes" else 0
student_strength = gpa_score + rank_score + act_score + dual_bonus + first_gen_penalty

# Select courses
st.header("Build Schedule")
course_options = courses["course_code"].tolist()
if "num_courses" not in st.session_state:
    st.session_state.num_courses = 4

if st.button("Add another course"):
    st.session_state.num_courses += 1

selected_courses = []
for i in range(st.session_state.num_courses):
    course = st.selectbox(f"Course {i + 1}", ["Select a course"] + course_options, key=f"course_{i}")
    if course != "Select a course":
        selected_courses.append(course)

# Calculate schedule difficulty
if selected_courses:
    schedule_df = courses[courses["course_code"].isin(selected_courses)][["course_name", "DFW Rate (%)"]]
    avg_dfw = schedule_df["DFW Rate (%)"].mean()
    st.subheader("Selected Schedule")
    st.table(schedule_df.rename(columns={"course_name": "Course Name"}))

    # Calculate challenge score
    challenge_score = (avg_dfw / 100) * (1 - student_strength / 100)

    # Tutoring option
    tutoring = st.checkbox("Reviewed tutoring/support options")
    if tutoring:
        challenge_score *= 0.5  # Reduce challenge by 50%

    # Determine stop light rating
    if challenge_score < 0.15:
        risk = "Low Risk"
        color = "green"
        message = "Great fit! This schedule aligns well with the student's preparation."
    elif challenge_score < 0.35:
        risk = "Moderate Risk"
        color = "orange"
        message = "Manageable with support. Review high-DFW courses or add tutoring."
    else:
        risk = "High Risk"
        color = "red"
        message = "Ambitious schedule! Consider tutoring or adjusting courses to ensure success."

    # Display result
    st.header("Schedule Assessment")
    st.markdown(f"**Challenge Level**: <span style='color:{color}'>{risk}</span>", unsafe_allow_html=True)
    st.write(message)
    if tutoring:
        st.write("Tutoring/support added—schedule now feels more manageable!")
else:
    st.write("Please select at least one course to assess the schedule.")
