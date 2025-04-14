# Advising Tool Demo

This is a demo for an edTech advising tool to help academic advisors assess the schedule difficulty for first-year college students. It uses student academic history and course DFW rates to provide a green/yellow/red "stop light view" of how challenging a schedule is, empowering advisors to make adjustments.

## How It Works
- **Data**:
  - `Student Data.xlsx`: Student details (GPA, ACT, Class Rank, First Gen, etc.).
  - `full_atu_course_pass_rates_combined.xlsx`: Course pass rates (DFW = 100% - pass rate).
- **Features**:
  - Select a student from a dropdown.
  - Choose 4+ courses (default 4, option to add more) from a dropdown of all courses.
  - View a green (low risk), yellow (moderate risk), or red (high risk) schedule rating.
  - Check a "tutoring/support" box to shift red to yellow, reflecting added support.
- **Purpose**: Helps advisors ensure schedules are manageable, especially for students with weaker academic backgrounds, while keeping them motivated.

## Setup
1. Ensure `Student Data.xlsx` and `full_atu_course_pass_rates_combined.xlsx` are in the repository.
2. Deploy on Streamlit Community Cloud:
   - Connect this repo to [streamlit.io/cloud](https://streamlit.io/cloud).
   - Set `app.py` as the main file.
   - Deploy to get a public URL.
3. View the app to test the advising tool.

## Files
- `app.py`: Streamlit app code.
- `requirements.txt`: Python dependencies.
- `Student Data.xlsx`: Sample student data.
- `full_atu_course_pass_rates_combined.xlsx`: Sample course data.

## Notes
- Built for non-coders, with simple copy-paste setup.
- Positive framing ensures students feel supported.
- Future versions may include course swap suggestions or more data fields.

Contact: [Your name, if you want] for feedback.
