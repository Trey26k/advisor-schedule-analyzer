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
student_courses = course_history[course_history["student_id"] == selected_id].iloc[0, 1::2].tolist()

# Sample degree plan
degree_plan = [
    "ENGL 1013", "PSY 2003", "MATH 1113", "BUAD 1111", "BUAD 2003",
    "ENGL 1023", "MATH 2223", "COMM 2003", "ACCT
