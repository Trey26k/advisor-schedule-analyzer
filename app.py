import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Student Schedule Difficulty", layout="centered")
st.title("🎓 Student Schedule Difficulty Estimator")

@st.cache_data
def load_data():
    student_data = pd.read_excel("data/Student Data.xlsx")
    course_pass_rates = pd.read_excel("data/full_atu_course_pass_rates_combined.xlsx")
    course_pass_rates["course_code"] = course_pass_rates["course_name"].str.extract(r"(^[A-Z]{2,4} \d{4})")
    return student_data, course_pass_rates

student_data, course_pass_rates = load_data()

def calculate_student_quality_score(profile):
    hs_gpa_score = (profile["High School GPA"] / 4.0) * 40
    rank_n, rank_d = map(int, profile["High School Class Rank"].split('/'))
    rank_percentile = (1 - (rank_n / rank_d)) * 100
    rank_score = rank_percentile * 0.3
    act_score = (profile["ACT Composite"] / 36) * 30

    bonus = 0
    college_gpa = profile["College GPA"]
    if not pd.isna(college_gpa):
        if college_gpa >= 3.5:
            bonus = 10
        elif college_gpa >= 3.0:
            bonus = 5

    return round(hs_gpa_score + rank_score + act_score + bonus)

def calculate_schedule_difficulty_score(course_codes):
    rates = []
    for code in course_codes:
        match = course_pass_rates[course_pass_rates["course_code"] == code]
        if not match.empty:
            rate = int(match.iloc[0]["pass_rate"].replace('%', ''))
            rates.append(100 - rate)
    return round(sum(rates) / len(rates)) if rates else 0

def determine_schedule_indicator(student_quality, schedule_difficulty):
    if student_quality >= 81:
        if schedule_difficulty <= 40:
            return "🟢 Green"
        elif schedule_difficulty <= 70:
            return "🟢 Green"
        else:
            return "🟡 Yellow"
    elif student_quality >= 61:
        if schedule_difficulty <= 40:
            return "🟢 Green"
        elif schedule_difficulty <= 70:
            return "🟡 Yellow"
        else:
            return "🔴 Red"
    else:
        if schedule_difficulty <= 40:
            return "🟡 Yellow"
        else:
            return "🔴 Red"

entered_id = st.text_input("Enter Student ID")

if entered_id and entered_id in student_data["Student ID"].astype(str).values:
    student_profile = student_data[student_data["Student ID"].astype(str) == entered_id].iloc[0]
    available_courses = sorted(course_pass_rates["course_code"].dropna().unique().tolist())
    st.subheader("📝 Build Proposed Schedule")

    if "course_count" not in st.session_state:
        st.session_state.course_count = 4
    if "reanalyze" not in st.session_state:
    st.session_state.reanalyze = False
else:
    st.session_state.reanalyze = st.session_state.reanalyze or any(
        st.session_state.get(f"replace_{i}") != st.session_state.get(f"course_{i}")
        for i in range(st.session_state.course_count)
    )

    course_selections = []
    for i in range(st.session_state.course_count):
        selected = st.selectbox(f"Course {i+1}", [""] + available_courses, index=0, key=f"course_{i}")
        if selected:
            course_selections.append(selected)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Add Course"):
            st.session_state.course_count += 1
            st.rerun()
    with col2:
        if st.session_state.course_count > 1 and st.button("➖ Remove Course"):
            st.session_state.course_count -= 1
            st.rerun()

    if st.button("🔍 Analyze Schedule") or st.session_state.reanalyze:
        student_quality = calculate_student_quality_score(student_profile)
        schedule_difficulty = calculate_schedule_difficulty_score(course_selections)
        risk_level = determine_schedule_indicator(student_quality, schedule_difficulty)

        st.markdown("---")
        st.markdown("<h3>📊 Schedule Evaluation</h3>", unsafe_allow_html=True)

        color_map = {
            "🟢": ("#e0ffe0", "#33cc33"),
            "🟡": ("#fff8db", "#ffcc00"),
            "🔴": ("#ffe0e0", "#ff4444")
        }
        icon = risk_level[0]
        label = risk_level[2:]
        bg_color, border_color = color_map.get(icon, ("#f0f0f0", "#ccc"))

        st.markdown(f"""
            <div style='background-color: {bg_color}; border-left: 10px solid {border_color}; padding: 1em; margin-top: 1em;'>
                <h4>{icon} Schedule is {label}</h4>
                <p>Based on the student profile and selected schedule, this plan is assessed as <strong>{label}</strong>.</p>
            </div>
        """, unsafe_allow_html=True)

        if icon in ["🔴", "🟡"]:
            st.markdown("---")
            st.subheader("⚠️ Build a Supportive Alternate Schedule")
            st.markdown("<p><strong>🔴 This schedule is currently too difficult based on the student's profile.</strong><br>Consider removing 1–2 of the flagged courses or replacing them with general education or support options.</p>", unsafe_allow_html=True)
            reconsidered = False
            for i, course_code in enumerate(course_selections):
                match = course_pass_rates[course_pass_rates["course_code"] == course_code]
                if not match.empty:
                    rate = int(match.iloc[0]["pass_rate"].replace('%', ''))
                    if rate < 50:
                        reconsidered = True
                        new_selection = st.selectbox(
                            f"Replace {course_code} (Low pass rate: {rate}%)",
                            [course_code] + [c for c in available_courses if c != course_code],
                            key=f"replace_{i}"
                        )
                        if new_selection != course_code:
                            st.session_state[f"course_{i}"] = new_selection
                            st.session_state.reanalyze = True
                            st.rerun()
            if icon == "🔴" and not reconsidered:
                st.warning("🔁 Please revise the schedule to improve the outcome before finalizing.")
            if icon == "🔴" and reconsidered:
                st.info("After making your changes, click the button below to re-check the schedule.")
                if st.button("♻️ Re-check Schedule"):
                    st.session_state.reanalyze = True
                    st.rerun()
 st.session_state.reanalyze and icon in ["🟡", "🟢"]:
            st.success("✅ Schedule improved! You've helped this student move toward a more manageable plan.")
            st.session_state.reanalyze = False
elif entered_id:
    st.error("Student ID not found. Please check and try again.")
