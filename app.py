import streamlit as st
import pandas as pd

# Constants for scoring weights and thresholds
GPA_WEIGHT = 40
RANK_WEIGHT = 30
ACT_WEIGHT = 20
DUAL_BONUS = 5
FIRST_GEN_PENALTY = -5
MAX_STRENGTH = 100
MIN_STRENGTH = 0
RISK_LOW_THRESHOLD = 0.15
RISK_MODERATE_THRESHOLD = 0.35
MAX_COURSES = 8  # Realistic cap for number of courses

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

# Load data with caching for efficiency
@st.cache_data
def load_data():
    try:
        students = pd.read_excel("data/Student Data.xlsx")
        courses = pd.read_excel("data/full_atu_course_pass_rates_combined.xlsx")
        # Safely convert pass_rate to numeric
        courses["pass_rate"] = pd.to_numeric(courses["pass_rate"].astype(str).str.rstrip("%"), errors='coerce')
        courses["DFW Rate (%)"] = 100 - courses["pass_rate"].fillna(0)
        return students, courses
    except Exception as e:
        st.error(f"Error loading data: {e}. Ensure 'Student Data.xlsx' and 'full_atu_course_pass_rates_combined.xlsx' are in the 'data' folder.")
        st.stop()

students, courses = load_data()

# Function to calculate student strength
def calculate_student_strength(student_data):
    # GPA score
    gpa_score = (student_data["High School GPA"] / 4.0) * GPA_WEIGHT
    
    # Rank score with error handling
    rank_score = 0
    rank_str = student_data["High School Class Rank"]
    if isinstance(rank_str, str):
        try:
            position, total = map(int, rank_str.split("/"))
            if total > 0:
                rank_score = (1 - position / total) * RANK_WEIGHT
        except (ValueError, ZeroDivisionError):
            pass  # Defaults to 0 if parsing fails
    
    # ACT score
    act_score = (student_data["ACT Composite"] / 36) * ACT_WEIGHT
    
    # Dual credit bonus
    college_gpa = student_data.get("College GPA", None)
    dual_bonus = DUAL_BONUS if pd.notnull(college_gpa) else 0
    
    # First-gen penalty
    first_gen_penalty = FIRST_GEN_PENALTY if student_data["First Generation College Student"] == "yes" else 0
    
    # Total and clamp
    strength = gpa_score + rank_score + act_score + dual_bonus + first_gen_penalty
    return max(MIN_STRENGTH, min(MAX_STRENGTH, strength))

# Function to calculate challenge score
def calculate_challenge_score(student_strength, schedule_df):
    if schedule_df.empty:
        return 0  # No courses, no challenge
    avg_dfw = schedule_df["DFW Rate (%)"].mean()
    return (avg_dfw / 100) * (1 - student_strength / 100)

# Select student
st.markdown("<div class='card'><h2>Select a Student</h2></div>", unsafe_allow_html=True)
student_ids = students["Student ID"].astype(str).tolist()
selected_student = st.selectbox("Choose a student:", student_ids, help="Select a student by their ID.")
student_data = students[students["Student ID"] == int(selected_student)].iloc[0]

# Display minimal student info
st.write(f"**Student ID**: {selected_student}")

# Divider
st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

# Select courses using multiselect for simplicity and to prevent duplicates
st.markdown("<div class='card'><h2>Build Schedule 📋</h2></div>", unsafe_allow_html=True)
course_options = courses["course_name"].tolist()
selected_courses = st.multiselect(
    "Select courses (up to 8):",
    course_options,
    max_selections=MAX_COURSES,
    help="Choose courses for the schedule. Duplicates are not allowed."
)

# Preview selected courses
if selected_courses:
    st.markdown("<h3>Preview Selected Courses</h3>", unsafe_allow_html=True)
    preview_df = pd.DataFrame({"Course Name": selected_courses})
    st.table(preview_df)

# Initialize session state for analyze button and reset
if "analyze_clicked" not in st.session_state:
    st.session_state.analyze_clicked = False
if "tutoring" not in st.session_state:
    st.session_state.tutoring = False

# Analyze Schedule button
if selected_courses:
    if st.button("Analyze Schedule", help="View the schedule difficulty and recommendations."):
        st.session_state.analyze_clicked = True
        st.session_state.tutoring = False  # Reset tutoring on new analysis

    # Show results if analyze button was clicked
    if st.session_state.analyze_clicked:
        student_strength = calculate_student_strength(student_data)
        
        # Prepare schedule data
        schedule_df = courses[courses["course_name"].isin(selected_courses)][["course_name", "DFW Rate (%)"]]
        if schedule_df.empty:
            st.warning("No valid courses selected. Please choose from the available options.")
            st.stop()
        
        # Initial challenge score
        challenge_score = calculate_challenge_score(student_strength, schedule_df)
        
        # Tutoring option
        st.session_state.tutoring = st.checkbox("Reviewed tutoring/support options ✅", value=st.session_state.tutoring, help="Check if tutoring or support was discussed to ease the schedule.")
        if st.session_state.tutoring:
            challenge_score *= 0.5  # Reduce challenge by 50%
        
        # Identify most challenging course if above low risk
        most_challenging = None
        if challenge_score >= RISK_LOW_THRESHOLD and not schedule_df.empty:
            most_challenging = schedule_df.loc[schedule_df["DFW Rate (%)"].idxmax()]["course_name"]
        
        # Format schedule table with highlight
        display_df = schedule_df[["course_name"]].rename(columns={"course_name": "Course Name"})
        if most_challenging:
            display_df["Course Name"] = display_df["Course Name"].apply(
                lambda x: f"<span class='highlight-red'>{x}</span>" if x == most_challenging else x
            )
        
        st.markdown("<div class='card'><h3>Selected Schedule</h3></div>", unsafe_allow_html=True)
        st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)

        # Determine risk rating
        if challenge_score < RISK_LOW_THRESHOLD:
            risk = "Low Risk"
            color = "#28a745"  # Green
            message = "Great fit! This schedule aligns well with the student's preparation."
            if st.session_state.tutoring:
                message = "Great fit! With tutoring, this schedule aligns well."
        elif challenge_score < RISK_MODERATE_THRESHOLD:
            risk = "Moderate Risk"
            color = "#ffc107"  # Yellow
            message = f"Manageable with support. Consider reviewing courses{f' (e.g., {most_challenging})' if most_challenging else ''} or adding tutoring."
            if st.session_state.tutoring:
                message = f"Manageable with tutoring. Consider reviewing courses{f' (e.g., {most_challenging})' if most_challenging else ''}."
        else:
            risk = "High Risk"
            color = "#a6192e"  # Red
            message = f"Ambitious schedule! Consider tutoring or adjusting courses{f' (e.g., {most_challenging})' if most_challenging else ''} to ensure success."
            if st.session_state.tutoring:
                message = f"Still ambitious with tutoring. Consider adjusting courses{f' (e.g., {most_challenging})' if most_challenging else ''}."

        # Display result
        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
        st.markdown("<div class='card'><h2>Schedule Assessment</h2></div>", unsafe_allow_html=True)
        st.markdown(f"**Challenge Level**: <span style='color:{color}; font-weight:bold;'>{risk}</span>", unsafe_allow_html=True)
        st.write(message)
        if st.session_state.tutoring:
            st.write("Tutoring/support added—schedule now feels more manageable!")

        # Send Schedule button
        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
        if st.button("Send Schedule", help="Send the schedule to the student's registration cart."):
            st.success("Your schedule has been sent to your student registration cart.")
        
        # Reset button
        if st.button("Reset Analysis", help="Clear the analysis and start over."):
            st.session_state.analyze_clicked = False
            st.session_state.tutoring = False
            st.rerun()
else:
    st.write("Please select at least one course to assess the schedule.")
