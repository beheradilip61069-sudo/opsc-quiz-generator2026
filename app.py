import streamlit as str
import pypdf
import google.generativeai as genai
import json
import time

# Page configuration
str.set_page_config(page_title="OPSC Mock Test Generator", page_icon="📝", layout="wide")

str.title("📝 OPSC AI Mock Test Generator")
str.subheader("Upload your syllabus or study material PDF to generate a 150-question mock test.")

# Sidebar for API Key configuration
with str.sidebar:
    str.header("Configuration")
    api_key = str.text_input("Enter your Gemini API Key:", type="password")
    str.markdown("[Get a free Gemini API Key here](https://aistudio.google.com/)")

# Initialize session states to store quiz data across rerenders
if "mock_test" not in str.session_state:
    str.session_state.mock_test = []
if "user_answers" not in str.session_state:
    str.session_state.user_answers = {}
if "submitted" not in str.session_state:
    str.session_state.submitted = False

# PDF Text Extraction Function
def extract_text_from_pdf(uploaded_file):
    pdf_reader = pypdf.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text

# AI Question Generation Function (Batched to reach 150)
def generate_opsc_questions(text, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    total_questions_needed = 150
    questions_per_batch = 15
    batches = total_questions_needed // questions_per_batch
    
    all_questions = []
    progress_bar = str.progress(0)
    status_text = str.empty()

    prompt_template = """
    You are an expert examiner for the OPSC (Odisha Public Service Commission) Civil Services Examination.
    Based on the following reference material, generate exactly {count} multiple-choice questions (MCQs) conforming strictly to OPSC GS Paper 1 standards.
    Include a mix of Indian Polity, History, Geography, Economy, General Science, and Odisha-specific GK if relevant to the text.
    
    Format your response STRICTLY as a JSON array of objects. Do not include markdown formatting like ```json or ```. 
    Each object must have these exact keys:
    - "question": The question text
    - "options": An array of 4 strings
    - "correct_answer": The exact string match of the correct option
    - "explanation": A detailed explanation of why it is correct.

    Reference Material (Excerpt):
    {text_excerpt}
    """

    # Split text roughly to distribute across batches
    text_chunks = [text[i:i+5000] for i in range(0, len(text), max(1, len(text)//batches))]

    for b in range(batches):
        status_text.text(f"Generating questions {b*questions_per_batch + 1} to {(b+1)*questions_per_batch} of 150...")
        
        excerpt = text_chunks[b % len(text_chunks)]
        prompt = prompt_template.format(count=questions_per_batch, text_excerpt=excerpt)
        
        try:
            response = model.generate_content(prompt)
            cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
            batch_questions = json.loads(cleaned_response)
            all_questions.extend(batch_questions)
        except Exception as e:
            # Retry logic or fallback placeholder if a batch fails
            time.sleep(2)
            continue
            
        progress_bar.progress((b + 1) / batches)
    
    status_text.text("Successfully generated 150 OPSC standard questions!")
    return all_questions[:150]

# File Upload UI
uploaded_file = str.file_uploader("Upload your Study Material (PDF)", type=["pdf"])

if uploaded_file and api_key:
    if str.button("Generate 150-Question OPSC Mock Test"):
        with str.spinner("Processing PDF and generating exam... This may take a minute due to the 150-question volume."):
            pdf_text = extract_text_from_pdf(uploaded_file)
            if len(pdf_text) < 100:
                str.error("Could not extract enough text from the PDF. Please ensure it's not a scanned image file.")
            else:
                str.session_state.mock_test = generate_opsc_questions(pdf_text, api_key)
                str.session_state.user_answers = {}
                str.session_state.submitted = False
                str.rerun()

elif uploaded_file and not api_key:
    str.warning("Please enter your Gemini API Key in the sidebar to start.")

# Display the Quiz
if str.session_state.mock_test:
    str.divider()
    str.header("📝 OPSC Mock Examination")
    str.caption(f"Total Questions: {len(str.session_state.mock_test)} | Marking Scheme: +2 for Correct, -0.66 for Incorrect")

    # Render questions
    for idx, q in enumerate(str.session_state.mock_test):
        str.markdown(f"**Q{idx+1}. {q['question']}**")
        
        # Unique key for each question widget
        options = q['options']
        user_choice = str.radio(
            f"Select option for Q{idx+1}:", 
            options, 
            index=None, 
            key=f"q_{idx}",
            label_visibility="collapsed"
        )
        
        if user_choice:
            str.session_state.user_answers[idx] = user_choice
            
        # If user submitted the test, reveal answers and explanations
        if str.session_state.submitted:
            correct = q['correct_answer']
            if user_choice == correct:
                str.success(f"Correct! Key: {correct}")
            else:
                str.error(f"Incorrect. Your Answer: {user_choice} | Correct Key: {correct}")
            str.info(f"**Explanation:** {q['explanation']}")
        str.divider()

    # Submit Button Logic
    if not str.session_state.submitted:
        if str.button("Submit Mock Test", type="primary"):
            str.session_state.submitted = True
            str.rerun()
            
    # Calculate Score
    if str.session_state.submitted:
        correct_count = 0
        incorrect_count = 0
        
        for idx, q in enumerate(str.session_state.mock_test):
            ans = str.session_state.user_answers.get(idx)
            if ans == q['correct_answer']:
                correct_count += 1
            elif ans is not None:
                incorrect_count += 1
                
        total_score = (correct_count * 2) - (incorrect_count * 0.66)
        
        str.sidebar.markdown("### 📊 Your Results")
        str.sidebar.metric("Total Score", f"{total_score:.2f} / 300")
        str.sidebar.write(f"✅ Correct: {correct_count}")
        str.sidebar.write(f"❌ Incorrect: {incorrect_count}")
        str.sidebar.write(f"⚪ Unattempted: {150 - (correct_count + incorrect_count)}")
