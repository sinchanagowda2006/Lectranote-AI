import streamlit as st
import yt_dlp
import whisper
import json
import os
from groq import Groq
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# -----------------------------
# Page Configuration
# -----------------------------
st.set_page_config(page_title="LectraNote AI", page_icon="🧠")

st.markdown("""
<style>

.main{
    background-color:#F8FAFC;
}

.stButton>button{
    background:linear-gradient(90deg,#2563EB,#4F46E5);
    color:white;
    border-radius:10px;
    height:3em;
    width:100%;
    font-weight:bold;
    border:none;
}

.stButton>button:hover{
    background:linear-gradient(90deg,#1D4ED8,#4338CA);
}

h1{
    color:#1E3A8A;
}

h2,h3{
    color:#2563EB;
}

div[data-testid="stExpander"]{
    border-radius:12px;
    border:1px solid #D1D5DB;
}

</style>
""", unsafe_allow_html=True)

st.title("🧠 LectraNote AI")

st.caption("Your AI-Powered Smart Lecture Assistant")

st.divider()

st.markdown("""
### Welcome!

LectraNote AI helps you study YouTube lectures using AI.

### Features

✅ Lecture Transcription

✅ AI Study Notes

✅ Interactive Quiz

✅ AI Flashcards

✅ AI Tutor
""")

# -----------------------------
# Configure Groq
# -----------------------------
client = Groq(api_key=os.environ["GROQ_API_KEY"])
# -----------------------------
# Load Whisper
# -----------------------------
@st.cache_resource
def load_model():
    return whisper.load_model("base")

model = load_model()

# -----------------------------
# PDF Generator
# -----------------------------
def create_pdf(text):

    pdf = SimpleDocTemplate("AI_Notes.pdf")

    styles = getSampleStyleSheet()

    story = []

    for line in text.split("\n"):
        story.append(Paragraph(line, styles["BodyText"]))

    pdf.build(story)

# -----------------------------
# YouTube Link
# -----------------------------
youtube_link = st.text_input("📺 Paste YouTube Lecture Link")

# -----------------------------
# Get Transcript
# -----------------------------
if st.button("📄 Get Lecture Transcript"):

    if youtube_link.strip() == "":
        st.warning("Please paste a YouTube link.")

    else:

        with st.spinner("Downloading lecture audio..."):

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "lecture_audio.%(ext)s",
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_link, download=True)
            audio_file = ydl.prepare_filename(info)

    except Exception as e:
        st.error("YouTube download failed:")
        st.code(str(e))
        st.stop()
        with st.spinner("Transcribing lecture..."):

            result = model.transcribe(audio_file)
            st.session_state["lecture_text"] = result["text"]

# -----------------------------
# Show Transcript
# -----------------------------
if "lecture_text" in st.session_state:

    transcript = st.session_state["lecture_text"]

    st.subheader("📄 Lecture Transcript")
    st.write(transcript)

    # -----------------------------
    # AI Notes
    # -----------------------------
    if st.button("📝 Generate AI Notes"):

        with st.spinner("Generating AI Notes..."):

            prompt = f"""
You are an expert study assistant.

Create high-quality study notes from this lecture.

Include:

# Title

# Summary

# Key Concepts

# Important Definitions

# Exam Tips

Lecture:

{transcript}
"""

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = response.choices[0].message.content

        st.subheader("📚 AI Study Notes")
        st.markdown(response_text)

        # Save notes as PDF
        create_pdf(response_text)

        with open("AI_Notes.pdf", "rb") as pdf_file:

            st.download_button(
                label="📥 Download Notes as PDF",
                data=pdf_file,
                file_name="LectraNote_AI_Notes.pdf",
                mime="application/pdf"
            )
           # -----------------------------
    # Interactive AI Quiz
    # -----------------------------
    if st.button("🎯 Generate AI Quiz"):

        with st.spinner("Generating Interactive Quiz..."):

            quiz_prompt = f"""
You are an expert teacher.

Generate EXACTLY 10 multiple-choice questions from the lecture.

Return ONLY valid JSON.

Format:

[
  {{
    "question":"Question here",
    "options":[
      "Option A",
      "Option B",
      "Option C",
      "Option D"
    ],
    "correct_answer":"Option A",
    "explanation":"Explain in one or two short sentences why this answer is correct."
  }}
]

Rules:

- Do NOT use markdown.
- Do NOT use ```json.
- Return ONLY JSON.
- Exactly 10 questions.
- Exactly 4 options each.
- correct_answer must exactly match one option.

Lecture:

{transcript}
"""

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "user",
                        "content": quiz_prompt
                    }
                ]
            )

            text = response.choices[0].message.content.strip()

            if text.startswith("```"):
                text = text.replace("```json", "")
                text = text.replace("```", "")
                text = text.strip()

            try:
                st.session_state["quiz"] = json.loads(text)
                st.success("✅ Quiz Generated!")
            except Exception:
                st.error("Couldn't generate quiz.")
                st.code(text)

    # -----------------------------
    # Display Quiz
    # -----------------------------
    if "quiz" in st.session_state:

        st.subheader("📝 Interactive Quiz")

        quiz = st.session_state["quiz"]

        for i, q in enumerate(quiz):

            st.markdown(f"### Question {i+1}")
            st.write(q["question"])

            options = ["Select an answer..."] + q["options"]

            st.selectbox(
                "Choose your answer:",
                options,
                key=f"q_{i}"
            )

    # -----------------------------
    # Submit Quiz
    # -----------------------------
    if "quiz" in st.session_state:

        if st.button("✅ Submit Quiz"):

            quiz = st.session_state["quiz"]

            unanswered = []

            for i in range(len(quiz)):
                if st.session_state[f"q_{i}"] == "Select an answer...":
                    unanswered.append(i + 1)

            if unanswered:

                st.error(
                    "Please answer all questions before submitting.\n\n"
                    f"Unanswered Questions: {', '.join(map(str, unanswered))}"
                )

                st.stop()

            score = 0

            st.subheader("📊 Quiz Results")

            for i, q in enumerate(quiz):

                user_answer = st.session_state[f"q_{i}"]
                correct_answer = q["correct_answer"]

                st.markdown(f"### Question {i+1}")

                if user_answer == correct_answer:

                    score += 1
                    st.success("✅ Correct")

                else:

                    st.error("❌ Incorrect")
                    st.write(f"**Your Answer:** {user_answer}")
                    st.write(f"**Correct Answer:** {correct_answer}")
                    st.info(f"💡 {q['explanation']}")

            st.divider()

            st.subheader(f"🎯 Final Score: {score}/{len(quiz)}")

            percentage = (score / len(quiz)) * 100

            st.progress(percentage / 100)

            st.write(f"### 📈 Percentage: {percentage:.0f}%")

            if percentage == 100:
                st.balloons()
                st.success("🏆 Perfect Score!")

            elif percentage >= 80:
                st.balloons()
                st.success("🎉 Excellent!")

            elif percentage >= 60:
                st.success("👍 Good Job!")

            else:
                st.warning("📚 Keep Practicing!")
                # -----------------------------
    # Chat with Lecture (AI Tutor)
    # -----------------------------
    st.divider()

    st.subheader("💬 Ask Anything About This Lecture")

    question = st.text_input("Ask a question about this lecture")

    if st.button("🤖 Ask AI"):

        if question.strip() == "":
            st.warning("Please enter a question.")

        else:

            with st.spinner("Thinking..."):

                prompt = f"""
You are an expert tutor.

Answer ONLY using the lecture below.

If the answer is not present in the lecture,
say:
'This topic is not covered in the lecture.'

Lecture:

{transcript}

Student Question:

{question}
"""

                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                answer = response.choices[0].message.content

            st.success("Answer")
            st.write(answer)

    # -----------------------------
    # AI Flashcards
    # -----------------------------
    st.divider()

    if st.button("🃏 Generate Flashcards"):

        with st.spinner("Generating Flashcards..."):

            prompt = f"""
Return ONLY valid JSON.

Generate exactly 10 flashcards.

Format:

[
  {{
    "front":"Question here",
    "back":"Answer here"
  }}
]

Rules:

- Return ONLY JSON.
- Do NOT use markdown.
- Do NOT use ```json.

Lecture:

{transcript}
"""

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            text = response.choices[0].message.content.strip()

            if text.startswith("```"):
                text = text.replace("```json", "")
                text = text.replace("```", "").strip()

            cards = json.loads(text)

            st.session_state["flashcards"] = cards

    if "flashcards" in st.session_state:

        st.subheader("🃏 AI Flashcards")

        for i, card in enumerate(st.session_state["flashcards"]):

            with st.expander(f"🃏 Flashcard {i+1}: {card['front']}"):

                st.success(card["back"])
