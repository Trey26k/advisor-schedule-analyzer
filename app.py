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
    .highlight-red { color: #a6192e; font-weight: bold; }
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

# Initialize session state for analyze button
if "analyze_clicked" not in st.session_state:
    st.session_state.analyze_clicked = False

# Analyze Schedule button
if selected_courses:
    if st.button("Analyze Schedule", help="View the schedule difficulty and recommendations."):
        st.session_state.analyze_clicked = True

    # Show results if analyze button was clicked
    if st.session_state.analyze_clicked:
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
        
        # Prepare schedule table
        schedule_df = courses[courses["course_name"].isin(selected_courses)][["course_name", "DFW Rate (%)"]]
        avg_dfw = schedule_df["DFW Rate (%)"].mean()
        challenge_score = (avg_dfw / 100) * (1 - student_strength / 100)

        # Identify most challenging course (only for moderate/high risk)
        most_challenging = None
        if challenge_score >= 0.15 and not schedule_df.empty:  # Only for yellow/red
            most_challenging = schedule_df.loc[schedule_df["DFW Rate (%)"].idxmax()]["course_name"]
        
        # Format schedule table with highlight
        display_df = schedule_df[["course_name"]].rename(columns={"course_name": "Course Name"})
        if most_challenging:
            display_df["Course Name"] = display_df["Course Name"].apply(
                lambda x: f"<span class='highlight-red'>{x}</span>" if x == most_challenging else x
            )
        
        st.markdown("<div class='card'><h3>Selected Schedule</h3></div>", unsafe_allow_html=True)
        st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)

        # Determine stop light rating
        if challenge_score < 0.15:
            risk = "Low Risk"
            color = "#28a745"  # Green
            message = "Great fit! This schedule aligns well with the student's preparation."
        elif challenge_score < 0.35:
            risk = "Moderate Risk"
            color = "#ffc107"  # Yellow
            message = f"Manageable with support. Consider reviewing courses{f' (e.g., {most_challenging})' if most_challenging else ''} or adding tutoring."
        else:
            risk = "High Risk"
            color = "#a6192e"  # Red
            message = f"Ambitious schedule! Consider tutoring or adjusting courses{f' (e.g., {most_challenging})' if most_challenging else ''} to ensure success."

        # Display result
        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
        st.markdown("<div class='card'><h2>Schedule Assessment</h2></div>", unsafe_allow_html=True)
        st.markdown(f"**Challenge Level**: <span style='color:{color}; font-weight:bold;'>{risk}</span>", unsafe_allow_html=True)
        st.write(message)

        # Tutoring option
        tutoring = st.checkbox("Reviewed tutoring/support options ✅", help="Check if tutoring or support was discussed to ease the schedule.")
        if tutoring:
            challenge_score_tutoring = challenge_score * 0.5  # Reduce challenge by 50%
            # Recalculate most challenging course for tutoring (none if low risk)
            most_challenging_tutoring = None
            if challenge_score_tutoring >= 0.15 and not schedule_df.empty:
                most_challenging_tutoring = schedule_df.loc[schedule_df["DFW Rate (%)"].idxmax()]["course_name"]
            
            # Update schedule table for tutoring
            display_df_tutoring = schedule_df[["course_name"]].rename(columns={"course_name": "Course Name"})
            if most_challenging_tutoring:
                display_df_tutoring["Course Name"] = display_df_tutoring["Course Name"].apply(
                    lambda x: f"<span class='highlight-red'>{x}</span>" if x == most_challenging_tutoring else x
                )
            
            st.markdown("<div class='card'><h3>Updated Schedule with Tutoring</h3></div>", unsafe_allow_html=True)
            st.markdown(display_df_tutoring.to_html(escape=False, index=False), unsafe_allow_html=True)

            # Recalculate rating after tutoring
            if challenge_score_tutoring < 0.15:
                risk = "Low Risk"
                color = "#28a745"
                message = "Great fit! With tutoring, this schedule aligns well."
            elif challenge_score_tutoring < 0.35:
                risk = "Moderate Risk"
                color = "#ffc107"
                message = f"Manageable with tutoring. Consider reviewing courses{f' (e.g., {most_challenging_tutoring})' if most_challenging_tutoring else ''}."
            else:
                risk = "High Risk"
                color = "#a6192e"
                message = f"Still ambitious with tutoring. Consider adjusting courses{f' (e.g., {most_challenging_tutoring})' if most_challenging_tutoring else ''}."
            st.markdown(f"**Updated Challenge Level**: <span style='color:{color}; font-weight:bold;'>{risk}</span>", unsafe_allow_html=True)
            st.write(message)
            st.write("Tutoring/support added—schedule now feels more manageable!")

        # Send Schedule button
        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
        if st.button("Send Schedule", help="Send the schedule to the student's registration cart."):
            st.session_state.analyze_clicked = True  # Keep results visible
            st.success("Your schedule has been sent to your student registration cart.")
else:
    st.write("Please select at least one course to assess the schedule.")
