import streamlit as st
import pandas as pd
import numpy as np  # For generating fake data
import plotly.express as px
import plotly.graph_objects as go

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
TUTORING_REDUCTION_FACTOR = 0.5  # Reduce DFW by 50% for tutored courses

# Set page title and layout
st.set_page_config(page_title="Advising Tool Demo", layout="wide")  # Changed to wide for dashboards

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
    .stCheckbox { margin-top: 0px; }  /* Tighten checkbox spacing */
    </style>
""", unsafe_allow_html=True)

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

# Function to calculate challenge score with per-course tutoring
def calculate_challenge_score(student_strength, schedule_df, tutored_courses):
    if schedule_df.empty:
        return 0  # No courses, no challenge
    # Adjust DFW for tutored courses
    adjusted_dfw = schedule_df["DFW Rate (%)"].copy()
    for course in tutored_courses:
        idx = schedule_df[schedule_df["course_name"] == course].index
        if not idx.empty:
            adjusted_dfw.loc[idx] *= TUTORING_REDUCTION_FACTOR
    avg_dfw = adjusted_dfw.mean()
    return (avg_dfw / 100) * (1 - student_strength / 100)

# Multi-page navigation
page = st.sidebar.selectbox("Select View", ["Advisor Tool", "Tutoring Allocation Dashboard", "DFW Spotlight"])

if page == "Advisor Tool":
    # Title
    st.markdown("<div class='card'><h1>First-Year Student Advising Tool 📚</h1></div>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 16px;'>Set your student up for success with a balanced schedule!</p>", unsafe_allow_html=True)

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

    # Consolidated UI: Combine preview and analysis in one flow
    if selected_courses:
        if st.button("Analyze Schedule", help="View the schedule difficulty and recommendations."):
            st.session_state.analyze_clicked = True
            st.session_state.tutored_courses = []  # Reset tutoring on new analysis
        else:
            st.markdown("<h3>Preview Selected Courses</h3>", unsafe_allow_html=True)
            preview_df = pd.DataFrame({"Course Name": selected_courses})
            st.table(preview_df)

        # Initialize session state
        if "analyze_clicked" not in st.session_state:
            st.session_state.analyze_clicked = False
        if "tutored_courses" not in st.session_state:
            st.session_state.tutored_courses = []

        # Show results if analyze button was clicked
        if st.session_state.analyze_clicked:
            student_strength = calculate_student_strength(student_data)
            
            # Prepare schedule data
            schedule_df = courses[courses["course_name"].isin(selected_courses)][["course_name", "DFW Rate (%)"]]
            if schedule_df.empty:
                st.warning("No valid courses selected. Please choose from the available options.")
                st.stop()
            
            # Remember old tutored for change detection
            old_tutored = st.session_state.tutored_courses.copy()
            
            # Table header
            st.markdown("<div class='card'><h3>Schedule with Tutoring Options</h3></div>", unsafe_allow_html=True)
            header_col1, header_col2 = st.columns([8, 1])
            with header_col1:
                st.markdown("<b>Course Name</b>", unsafe_allow_html=True)
            with header_col2:
                st.markdown("<b>Tutoring</b>", unsafe_allow_html=True)
            
            # Table rows with course and checkbox
            tutored_courses = []
            for course in schedule_df["course_name"]:
                row_col1, row_col2 = st.columns([8, 1])
                tutor_check = row_col2.checkbox("", key=f"tutor_{course}", help="Checking this box will enroll student in tutoring reminders for this course.", label_visibility="collapsed")
                if tutor_check:
                    tutored_courses.append(course)
                with row_col1:
                    # Highlight logic: red if most challenging and not tutored
                    initial_most_challenging = schedule_df.loc[schedule_df["DFW Rate (%)"].idxmax()]["course_name"] if not schedule_df.empty else None
                    is_challenging = (course == initial_most_challenging) and (not tutor_check)
                    course_display = f"<span class='highlight-red'>{course}</span>" if is_challenging else course
                    st.markdown(course_display, unsafe_allow_html=True)
            
            # Update session and rerun if changed for immediate update
            if sorted(old_tutored) != sorted(tutored_courses):
                st.session_state.tutored_courses = tutored_courses
                st.rerun()
            
            # Now calculate with updated tutored_courses
            challenge_score = calculate_challenge_score(student_strength, schedule_df, tutored_courses)
            
            # Identify current most challenging course based on adjusted DFW
            most_challenging = None
            if challenge_score >= RISK_LOW_THRESHOLD and not schedule_df.empty:
                adjusted_dfw = schedule_df["DFW Rate (%)"].copy()
                for course in tutored_courses:
                    idx = schedule_df[schedule_df["course_name"] == course].index
                    if not idx.empty:
                        adjusted_dfw.loc[idx] *= TUTORING_REDUCTION_FACTOR
                most_challenging = schedule_df.loc[adjusted_dfw.idxmax(), "course_name"]
            
            # Risk downgrade logic: If the initial flagged course is tutored, force downgrade by one level
            initial_challenge_score = calculate_challenge_score(student_strength, schedule_df, [])
            initial_most_challenging = None
            if initial_challenge_score >= RISK_LOW_THRESHOLD and not schedule_df.empty:
                initial_most_challenging = schedule_df.loc[schedule_df["DFW Rate (%)"].idxmax()]["course_name"]
            
            downgrade = initial_most_challenging in tutored_courses if initial_most_challenging else False
            
            # Determine initial risk level without tutoring
            if initial_challenge_score < RISK_LOW_THRESHOLD:
                initial_risk = "Low Risk"
                initial_color = "#28a745"
            elif initial_challenge_score < RISK_MODERATE_THRESHOLD:
                initial_risk = "Moderate Risk"
                initial_color = "#ffc107"
            else:
                initial_risk = "High Risk"
                initial_color = "#a6192e"
            
            # Apply downgrade if applicable
            if downgrade:
                if initial_risk == "High Risk":
                    risk = "Moderate Risk"
                    color = "#ffc107"
                elif initial_risk == "Moderate Risk":
                    risk = "Low Risk"
                    color = "#28a745"
                else:
                    risk = initial_risk
                    color = initial_color
                message = f"Manageable with tutoring on challenging course. Consider reviewing other courses if needed."
            else:
                # Use calculated based on current challenge_score
                if challenge_score < RISK_LOW_THRESHOLD:
                    risk = "Low Risk"
                    color = "#28a745"
                    message = "Great fit! This schedule aligns well with the student's preparation."
                    if tutored_courses:
                        message = "Great fit! With selected tutoring, this schedule aligns well."
                elif challenge_score < RISK_MODERATE_THRESHOLD:
                    risk = "Moderate Risk"
                    color = "#ffc107"
                    message = f"Manageable with support. Consider reviewing courses{f' (e.g., {most_challenging})' if most_challenging else ''} or adding more tutoring."
                    if tutored_courses:
                        message = f"Manageable with selected tutoring. Consider reviewing courses{f' (e.g., {most_challenging})' if most_challenging else ''}."
                else:
                    risk = "High Risk"
                    color = "#a6192e"
                    message = f"Ambitious schedule! Consider adding tutoring or adjusting courses{f' (e.g., {most_challenging})' if most_challenging else ''} to ensure success."
                    if tutored_courses:
                        message = f"Still ambitious with selected tutoring. Consider adjusting courses{f' (e.g., {most_challenging})' if most_challenging else ''}."

            # Display result (consolidated below the schedule)
            st.markdown(f"**Challenge Level**: <span style='color:{color}; font-weight:bold;'>{risk}</span>", unsafe_allow_html=True)
            st.write(message)
            if tutored_courses:
                st.write(f"Tutoring selected for: {', '.join(tutored_courses)}—schedule now feels more manageable!")

            # Actions
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Send Schedule", help="Send the schedule to the student's registration cart."):
                    st.success("Your schedule has been sent to your student registration cart.")
                    # In production, here you'd integrate with CRM to set reminders for tutored courses
            with col2:
                if st.button("Reset Analysis", help="Clear the analysis and start over."):
                    st.session_state.analyze_clicked = False
                    st.session_state.tutored_courses = []
                    st.rerun()
    else:
        st.write("Please select at least one course to assess the schedule.")

elif page == "Tutoring Allocation Dashboard":
    st.markdown("<div class='card'><h1>Tutoring Allocation Dashboard 📊</h1></div>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 16px;'>Plan and allocate tutoring resources based on flagged needs across students.</p>", unsafe_allow_html=True)
    
    # Realistic fake data for tutoring needs
    np.random.seed(42)
    realistic_courses = [
        "General Chemistry", "Introductory Biology", "College Algebra", "Calculus I", "Trigonometry",
        "Organic Chemistry", "Physics I", "Microeconomics", "Accounting I", "English Composition"
    ]
    subjects = ["CHEM", "BIO", "MATH", "MATH", "MATH", "CHEM", "PHYS", "ECON", "ACCT", "ENGL"]
    gen_ed = [True, True, True, True, False, False, True, True, False, True]  # Assume some are gen ed
    classifications = np.random.choice(["Freshman", "Sophomore", "Junior", "Senior"], len(realistic_courses))
    fake_data = pd.DataFrame({
        "Course Name": realistic_courses,
        "Subject": subjects,
        "General Education": gen_ed,
        "Classification": classifications,
        "Students Flagged": np.random.randint(20, 100, len(realistic_courses)),
        "Estimated Hours Needed": np.random.randint(50, 500, len(realistic_courses)),
    })
    
    # Student level filter at top
    all_classifications = sorted(set(fake_data["Classification"]))
    class_filter = st.multiselect("Select Student Level", all_classifications, default=all_classifications)
    
    top_data = fake_data[fake_data["Classification"].isin(class_filter)].sort_values("Estimated Hours Needed", ascending=False)
    
    # Top section: KPIs and chart of top courses
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Students Needing Tutoring", top_data["Students Flagged"].sum())
    with col2:
        st.metric("Total Estimated Hours", top_data["Estimated Hours Needed"].sum())
    
    st.markdown("<h3>Top Courses Needing Tutoring (by Estimated Hours)</h3>", unsafe_allow_html=True)
    st.bar_chart(top_data.set_index("Course Name")["Estimated Hours Needed"])
    
    # Below: Actionable options to review by department (subject)
    st.markdown("<h3>Review Top Tutoring Needs by Department</h3>", unsafe_allow_html=True)
    all_subjects = sorted(set(fake_data["Subject"]))
    subject_filter = st.multiselect("Select Department(s)", all_subjects)
    gen_ed_only = st.checkbox("Limit to General Education Courses Only", value=False)
    
    filtered_data = fake_data.copy()
    if subject_filter:
        filtered_data = filtered_data[filtered_data["Subject"].isin(subject_filter)]
    if gen_ed_only:
        filtered_data = filtered_data[filtered_data["General Education"]]
    filtered_data = filtered_data.sort_values("Estimated Hours Needed", ascending=False)
    
    # Filtered view (table only, no bottom bar)
    if not filtered_data.empty:
        st.dataframe(filtered_data[["Course Name", "Subject", "Estimated Hours Needed", "Students Flagged"]])

    st.write("This dashboard simulates aggregated data from advising sessions. In production, it would pull from CRM integrations for real-time planning.")

elif page == "DFW Spotlight":
    # Generate realistic fake data based on typical college DFW rates
    # Courses: High DFW in STEM (e.g., Calculus 30-40%, Org Chem 40-50%, Physics 20-40%)
    # Lower in others (e.g., English 10-20%). Includes fluctuations: e.g., Algebra jumps 25%->35%
    data = {
        'Subject': ['Math', 'Math', 'Math', 'Math', 'Math', 'Math', 'Math', 'Math', 'Math', 'Math',
                    'Chemistry', 'Chemistry', 'Chemistry', 'Chemistry', 'Chemistry', 'Chemistry', 'Chemistry', 'Chemistry', 'Chemistry', 'Chemistry',
                    'Physics', 'Physics', 'Physics', 'Physics', 'Physics', 'Physics', 'Physics', 'Physics', 'Physics', 'Physics',
                    'Biology', 'Biology', 'Biology', 'Biology', 'Biology', 'Biology', 'Biology', 'Biology', 'Biology', 'Biology',
                    'English', 'English', 'English', 'English', 'English', 'English', 'English', 'English', 'English', 'English',
                    'History', 'History', 'History', 'History', 'History', 'History', 'History', 'History', 'History', 'History'],
        'Course': ['College Algebra', 'College Algebra', 'College Algebra', 'College Algebra', 'College Algebra', 'Calculus I', 'Calculus I', 'Calculus I', 'Calculus I', 'Calculus I',
                   'General Chemistry', 'General Chemistry', 'General Chemistry', 'General Chemistry', 'General Chemistry', 'Organic Chemistry', 'Organic Chemistry', 'Organic Chemistry', 'Organic Chemistry', 'Organic Chemistry',
                   'Physics I', 'Physics I', 'Physics I', 'Physics I', 'Physics I', 'Physics II', 'Physics II', 'Physics II', 'Physics II', 'Physics II',
                   'Intro Biology', 'Intro Biology', 'Intro Biology', 'Intro Biology', 'Intro Biology', 'Cell Biology', 'Cell Biology', 'Cell Biology', 'Cell Biology', 'Cell Biology',
                   'English Comp I', 'English Comp I', 'English Comp I', 'English Comp I', 'English Comp I', 'English Comp II', 'English Comp II', 'English Comp II', 'English Comp II', 'English Comp II',
                   'US History I', 'US History I', 'US History I', 'US History I', 'US History I', 'World History', 'World History', 'World History', 'World History', 'World History'],
        'Year': [2020, 2021, 2022, 2023, 2024, 2020, 2021, 2022, 2023, 2024,
                 2020, 2021, 2022, 2023, 2024, 2020, 2021, 2022, 2023, 2024,
                 2020, 2021, 2022, 2023, 2024, 2020, 2021, 2022, 2023, 2024,
                 2020, 2021, 2022, 2023, 2024, 2020, 2021, 2022, 2023, 2024,
                 2020, 2021, 2022, 2023, 2024, 2020, 2021, 2022, 2023, 2024,
                 2020, 2021, 2022, 2023, 2024, 2020, 2021, 2022, 2023, 2024],
        'Semester': ['Fall', 'Spring', 'Fall', 'Spring', 'Fall', 'Fall', 'Spring', 'Fall', 'Spring', 'Fall',
                     'Fall', 'Spring', 'Fall', 'Spring', 'Fall', 'Fall', 'Spring', 'Fall', 'Spring', 'Fall',
                     'Fall', 'Spring', 'Fall', 'Spring', 'Fall', 'Fall', 'Spring', 'Fall', 'Spring', 'Fall',
                     'Fall', 'Spring', 'Fall', 'Spring', 'Fall', 'Fall', 'Spring', 'Fall', 'Spring', 'Fall',
                     'Fall', 'Spring', 'Fall', 'Spring', 'Fall', 'Fall', 'Spring', 'Fall', 'Spring', 'Fall',
                     'Fall', 'Spring', 'Fall', 'Spring', 'Fall', 'Fall', 'Spring', 'Fall', 'Spring', 'Fall'],
        'DFW_Rate': [0.25, 0.28, 0.35, 0.32, 0.30, 0.32, 0.35, 0.38, 0.34, 0.36,
                     0.28, 0.30, 0.32, 0.29, 0.31, 0.42, 0.45, 0.48, 0.44, 0.46,
                     0.22, 0.25, 0.28, 0.24, 0.26, 0.30, 0.32, 0.35, 0.31, 0.33,
                     0.20, 0.22, 0.25, 0.21, 0.23, 0.28, 0.30, 0.32, 0.29, 0.31,
                     0.12, 0.15, 0.18, 0.14, 0.16, 0.10, 0.13, 0.16, 0.12, 0.14,
                     0.15, 0.18, 0.20, 0.17, 0.19, 0.14, 0.16, 0.19, 0.15, 0.17],
        'Enrollment': [500, 480, 520, 510, 490, 400, 390, 410, 395, 405,
                       450, 440, 460, 445, 455, 300, 290, 310, 295, 305,
                       350, 340, 360, 345, 355, 280, 270, 290, 275, 285,
                       600, 580, 620, 590, 610, 550, 530, 570, 540, 560,
                       700, 680, 720, 690, 710, 650, 630, 670, 640, 660,
                       400, 390, 410, 395, 405, 380, 370, 390, 375, 385]
    }
    df = pd.DataFrame(data)
    df['DFW_Rate_%'] = df['DFW_Rate'] * 100  # For display
    df['Period'] = df['Year'].astype(str) + ' ' + df['Semester']

    # Sort periods chronologically for comparisons
    df = df.sort_values(['Year', 'Semester'])

    # Calculate changes for notifications
    df['Prev_DFW_Rate'] = df.groupby('Course')['DFW_Rate'].shift(1)
    df['Change'] = df['DFW_Rate'] - df['Prev_DFW_Rate']
    df['Change_Percent'] = (df['Change'] / df['Prev_DFW_Rate'] * 100).where(df['Prev_DFW_Rate'] != 0)

    # Streamlit Dashboard
    st.title('DFW Rates Dashboard for Administrators')
    st.markdown('''Insights into course difficulties: Compare trends, spot changes, and drill down by subject.  
                Ties into schedule rigor—high DFW courses may need tutoring interventions.''')

    # Sidebar for global filters
    st.sidebar.header('Filters')
    selected_subject = st.sidebar.selectbox('Drill Into Subject', ['All'] + sorted(df['Subject'].unique()))
    selected_course = st.sidebar.selectbox('Select Course for Trend', ['All'] + sorted(df['Course'].unique()))
    change_threshold = st.sidebar.slider('Notification Threshold (% Change)', 5, 20, 10)

    # Section 1: Highest DFW Rates Across Campus
    st.header('Highest DFW Rates Across Campus')
    latest_year = df['Year'].max()
    latest_df = df[df['Year'] == latest_year].groupby('Course').agg({'DFW_Rate_%': 'mean', 'Enrollment': 'sum'}).reset_index()
    latest_df = latest_df.sort_values('DFW_Rate_%', ascending=False).head(10)
    st.table(latest_df.style.format({'DFW_Rate_%': '{:.1f}%'}))

    # Bar Chart
    fig_bar = px.bar(latest_df, x='Course', y='DFW_Rate_%', text='DFW_Rate_%',
                     labels={'DFW_Rate_%': 'DFW Rate (%)'}, title=f'Top 10 Highest DFW Courses ({latest_year})')
    fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    st.plotly_chart(fig_bar)

    # Section 2: Year-Over-Year / Semester Comparisons
    st.header('Trend Comparisons')
    if selected_course != 'All':
        course_data = df[df['Course'] == selected_course]
        fig_line = px.line(course_data, x='Period', y='DFW_Rate_%', markers=True,
                           title=f'DFW Rate Trend for {selected_course}')
        fig_line.update_yaxes(title='DFW Rate (%)')
        st.plotly_chart(fig_line)
    else:
        st.info('Select a course in the sidebar to view trends.')

    # Section 3: Notifications for Changes
    st.header('Notifications: Significant Changes')
    changes_df = df[(abs(df['Change_Percent']) >= change_threshold) & df['Change'].notna()]
    if not changes_df.empty:
        for _, row in changes_df.iterrows():
            direction = 'jump' if row['Change'] > 0 else 'drop'
            st.warning(f"Alert: {row['Course']} DFW rate {direction}ed by {row['Change_Percent']:.1f}% to {row['DFW_Rate_%']:.1f}% in {row['Period']} (from prior period).")
    else:
        st.success('No significant changes detected based on threshold.')

    # Section 4: Drill Into Subject
    if selected_subject != 'All':
        st.header(f'Detailed View for {selected_subject}')
        subject_df = df[df['Subject'] == selected_subject]
        # Table
        st.subheader('Course Data Table')
        st.dataframe(subject_df[['Course', 'Period', 'DFW_Rate_%', 'Enrollment', 'Change_Percent']].style.format({'DFW_Rate_%': '{:.1f}%', 'Change_Percent': '{:.1f}%'}))
        
        # Chart
        fig_subject = px.line(subject_df, x='Period', y='DFW_Rate_%', color='Course', markers=True,
                              title=f'DFW Trends in {selected_subject}')
        fig_subject.update_yaxes(title='DFW Rate (%)')
        st.plotly_chart(fig_subject)
    else:
        st.info('Select a subject in the sidebar to drill down.')
