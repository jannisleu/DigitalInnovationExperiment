import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import uuid
import random
import time
import os
from datetime import datetime

# Mock Tweets for the experiment
# In a real app, load this from a CSV or database
TWEETS = [
    {"id": 1, "text": "Gay people are human garbage.", "ai_suggestion": "Block"},
    {"id": 2, "text": "Her colleague is a disabled person.", "ai_suggestion": "Keep"},
    {"id": 3, "text": "The economy is so fucked.", "ai_suggestion": "Keep"},
    {"id": 4, "text": "You are nothing but common female trash.", "ai_suggestion": "Block"},
    {"id": 5, "text": "She knows she looks good, she's a bad bitch.", "ai_suggestion": "Block"},
    {"id": 6, "text": "Swarms of Muslims are infesting our government.", "ai_suggestion": "Block"},
    {"id": 7, "text": "I live with two gay people.", "ai_suggestion": "Keep"},
    {"id": 8, "text": "Are there any immigrants on your course?", "ai_suggestion": "Keep"},
    {"id": 9, "text": "If men are so privileged and women have it so hard why are so many men choosing to live as females?", "ai_suggestion": "Keep"},
    {"id": 10, "text": "Immigrants like you make me furious.", "ai_suggestion": "Block"},
    {"id": 11, "text": "What makes you say stuff like “these Muslims disgust me so much?”", "ai_suggestion": "Block"},
    {"id": 12, "text": "Women are beautiful.", "ai_suggestion": "Keep"},
    {"id": 13, "text": "Putting a trans person in charge is the best thing anyone can do.", "ai_suggestion": "Keep"},
    {"id": 14, "text": "Never trust a single word said by a woman.", "ai_suggestion": "Keep"},
    {"id": 15, "text": "Typical whore behaviour.", "ai_suggestion": "Block"},
    {"id": 16, "text": "You are just a fag to me.", "ai_suggestion": "Block"},
    {"id": 17, "text": 'You can write "I\'ll slaughter any woman like you", but I will take you to court for that.', "ai_suggestion": "Block"},
    {"id": 18, "text": "Gay people are great.", "ai_suggestion": "Keep"},
    {"id": 19, "text": "Why are aspirins white? because they work.", "ai_suggestion": "Keep"},
    {"id": 20, "text": "Of course that dumbass was a woman.", "ai_suggestion": "Block"},
]

# --- HELPER FUNCTIONS ---

def init_session_state():
    """Initialize all session state variables."""
    if 'user_id' not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    
    if 'condition' not in st.session_state:
        # Randomly assign condition A, B, or C
        st.session_state.condition = random.choice(['A', 'B', 'C'])
        
    if 'current_tweet_index' not in st.session_state:
        st.session_state.current_tweet_index = 0
        
    if 'responses' not in st.session_state:
        st.session_state.responses = []

    if 'prescreening_complete' not in st.session_state:
        st.session_state.prescreening_complete = False
        
    if 'experiment_complete' not in st.session_state:
        st.session_state.experiment_complete = False
    
    if 'survey_complete' not in st.session_state:
        st.session_state.survey_complete = False

    if 'guidelines_complete' not in st.session_state:
        st.session_state.guidelines_complete = False

    # Specific state for Condition B (Placebo) to track if they waited
    if 'verified_ai' not in st.session_state:
        st.session_state.verified_ai = False

def save_response(tweet_data, decision, reason=None):
    """Appends the response directly to Google Sheets using gspread (Atomic Append)."""
    
    # 1. Prepare the row data as a list (not a DataFrame/dict)
    row_data = [
        st.session_state.user_id,
        datetime.now().isoformat(),
        st.session_state.condition,
        tweet_data['id'],
        tweet_data['text'],
        tweet_data['ai_suggestion'],
        decision,
        reason if reason else "N/A"
    ]
    
    # 2. Update Session State (for UI feedback only)
    st.session_state.responses.append({
        "user_id": row_data[0], "timestamp": row_data[1], "condition": row_data[2],
        "tweet_id": row_data[3], "tweet_text": row_data[4], "ai_suggestion": row_data[5],
        "user_decision": row_data[6], "reason": row_data[7]
    })

    try:
        # 3. Load Secrets manually
        # We access the same secrets you set up for the connection
        secrets = st.secrets["connections"]["gsheets"]
        
        # 4. Authenticate directly
        # We assume the secrets are inside the "connections.gsheets" block
        creds = Credentials.from_service_account_info(
            secrets,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        client = gspread.authorize(creds)
        
        # 5. Open the Sheet
        # Use the URL found in your secrets file
        spreadsheet = client.open_by_url(secrets["spreadsheet"])
        worksheet = spreadsheet.sheet1 # Targets the first tab
        
        # 6. Append the Row
        # This is the magic command. It just adds data to the bottom.
        worksheet.append_row(row_data)
        
    except Exception as e:
        st.error(f"Error saving to Google Sheets: {e}")

def save_survey_results(answers):
    """Saves the Likert scale answers to the 'Survey' tab."""
    row_data = [
        st.session_state.user_id,
        datetime.now().isoformat(),
        st.session_state.condition,
        answers[0], answers[1], answers[2], 
        answers[3], answers[4], answers[5]
    ]

    try:
        # Load secrets and auth (same as before)
        secrets = st.secrets["connections"]["gsheets"]
        creds = Credentials.from_service_account_info(
            secrets,
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)
        
        # Open the specific 'Survey' tab
        spreadsheet = client.open_by_url(secrets["spreadsheet"])
        # CAREFUL: Make sure you created a tab named "Survey" in your Google Sheet!
        worksheet = spreadsheet.worksheet("Survey") 
        
        worksheet.append_row(row_data)
        
    except Exception as e:
        st.error(f"Error saving survey: {e}")
        # Stop execution so the user sees the error
        st.stop()

def save_prescreening(age, gender, profession, field, likert_ans, freq_usage, freq_verify):
    """Saves demographics to the 'Demographics' tab."""
    row_data = [
        st.session_state.user_id,
        datetime.now().isoformat(),
        st.session_state.condition,
        age, gender, profession, field,
        likert_ans[0], likert_ans[1], likert_ans[2], # The 3 Likert answers
        freq_usage, freq_verify
    ]

    try:
        secrets = st.secrets["connections"]["gsheets"]
        creds = Credentials.from_service_account_info(
            secrets,
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)
        
        spreadsheet = client.open_by_url(secrets["spreadsheet"])
        # Ensure you created this tab in your Google Sheet!
        worksheet = spreadsheet.worksheet("Prescreening")
        
        worksheet.append_row(row_data)
        
    except Exception as e:
        st.error(f"Error saving Prescreening: {e}")
        st.stop()

def next_tweet():
    """Move to next tweet or finish experiment."""
    st.session_state.current_tweet_index += 1
    # Reset specific friction states
    st.session_state.verified_ai = False
    
    if st.session_state.current_tweet_index >= len(TWEETS):
        st.session_state.experiment_complete = True
    st.rerun()

# --- PAGE RENDERING ---

def render_intro():
    st.title("AI-Assisted Content Moderation Study")
    
    st.markdown("""
    ### Welcome
    You are invited to participate in a short research study on **Human-AI Decision Making**.
    
    **Your Task:**
    1. You will act as a **Moderator** for a social media platform.
    2. You will review a series of tweets.
    3. An **AI Assistant** will provide a suggestion for each tweet to help you.
    4. You must decide to **Approve** or **Reject** the AI's suggestion based on community guidelines.
                
    **Duration:**
    The entire experiment will take approximately **10 minutes** to complete.
    
    ---
    
    ### 🔒 Privacy & Consent
    * **Anonymous:** We do not collect names, emails, or IP addresses. You are assigned a random ID.
    * **Data Usage:** Data is stored securely and used **only** for this academic experiment.
    * **Voluntary:** You can stop at any time by closing the browser tab.
    * **Risk:** The content contains toxic tweets (hate speech/harassment) which may be offensive to some users.
    """)
    
    st.write("") # Spacer
    
    # Consent Checkbox
    consent = st.checkbox("I have read the information above and consent to participate in this study.")
    
    st.write("") # Spacer
    
    # Button is disabled unless consent is checked
    if st.button("Begin Study", type="primary", disabled=not consent):
        st.session_state.started = True
        st.rerun()

def render_prescreening():
    st.title("Participant Prescreening")
    st.info("Please answer a few questions about yourself before we begin the experiment.")
    
    # --- Part 1: Personal Info ---
    st.subheader("1. Profile")
    age = st.number_input("Age", min_value=18, max_value=99, step=1, value=25)
    gender = st.selectbox("Gender", ["Female", "Male", "Non-binary", "Prefer not to say", "Other"])
    
    profession = st.radio("Current Status", ["Student", "Professional", "Other"])
    
    # Conditional Input: Only show if Student
    field_of_study = ""
    if profession == "Student":
        common_fields = [
            "Computer Science / IT",
            "Business / Economics",
            "Engineering",
            "Psychology",
            "Medicine / Health Sciences",
            "Law",
            "Education",
            "Biology / Life Sciences",
            "Arts / Humanities",
            "Social Sciences",
            "Physics / Mathematics",
            "Communications / Media",
            "Political Science",
            "Design / Architecture",
            "History",
            "Other"
        ]
        
        selected_field = st.selectbox("Field of Study", common_fields)
        
        if selected_field == "Other":
            field_of_study = st.text_input("Please specify your field:")
        else:
            field_of_study = selected_field
    
    st.write("---")
    
    # --- Part 2: AI Attitudes (Likert) ---
    st.subheader("2. Attitudes towards AI")
    st.caption("Rate your agreement (1 = Strongly Disagree, 7 = Strongly Agree)")
    
    questions = [
        "I usually trust AI suggestions until I have a specific reason not to.",
        "For the most part, I am skeptical of the outputs generated by AI.",
        "I generally assume that modern AI tools are accurate."
    ]
    
    likert_answers = []
    for i, q in enumerate(questions):
        st.markdown(f"**{q}**")
        ans = st.radio(
            f"demog_q{i}", 
            options=[1, 2, 3, 4, 5, 6, 7], 
            horizontal=True, 
            index=3, # Defaults to neutral
            key=f"likert_pre_{i}", # Unique key
            label_visibility="collapsed"
        )
        likert_answers.append(ans)
    
    st.write("---")

    # --- Part 3: Frequency ---
    st.subheader("3. Usage Habits")
    
    q_freq = "How frequently do you use generative AI tools (e.g., ChatGPT, Gemini)?"
    opts_freq = ["Never", "Less than Monthly", "Monthly", "Weekly", "Daily", "Multiple times a day"]
    usage_freq = st.selectbox(q_freq, opts_freq)
    
    q_verify = "When using AI tools for information retrieval, how often do you verify the output with a second source?"
    opts_verify = ["Never", "Rarely", "Sometimes", "Often", "Always"]
    verify_freq = st.selectbox(q_verify, opts_verify)
    
    st.write("")
    st.write("")
    
    if st.button("Start Experiment", type="primary"):
        # Simple validation
        if profession == "Student" and field_of_study.strip() == "":
            st.error("Please enter your Field of Study.")
        else:
            save_prescreening(age, gender, profession, field_of_study, likert_answers, usage_freq, verify_freq)
            st.session_state.prescreening_complete = True
            st.rerun()

def render_tweet_card(tweet):
    """Displays the tweet and the AI suggestion."""
    
    # Progress bar
    progress = st.session_state.current_tweet_index / len(TWEETS)
    st.progress(progress, text=f"Tweet {st.session_state.current_tweet_index + 1} of {len(TWEETS)}")

    # The Tweet
    st.markdown("### Tweet Content")
    st.markdown(
        f"""
        <div style="padding: 20px; border-radius: 10px; background-color: #000000; border: 1px solid #d0d7de; margin-bottom: 20px;">
            <p style="font-size: 18px; font-family: sans-serif;">{tweet['text']}</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # The AI Suggestion
    ai_color = "#ff4b4b" if tweet['ai_suggestion'] == "Block" else "#0df05c"
    st.markdown(f"**🤖 AI Suggestion:** <span style='color:{ai_color}; font-weight:bold; font-size:1.2em'>{tweet['ai_suggestion']}</span>", unsafe_allow_html=True)
    st.write("---")

def render_controls_condition_A(tweet):
    """Low Friction: Instant Action."""
    st.subheader("Action")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Reject AI suggestion", use_container_width=True):
            save_response(tweet, "Reject")
            next_tweet()
    with col2:
        if st.button("✅ Approve AI suggestion", use_container_width=True):
            save_response(tweet, "Approve")
            next_tweet()

def render_controls_condition_B(tweet):
    """Placebo Friction: Fake Verification Wait."""
    st.subheader("Action")
    
    # Step 1: Force User to "Verify" AI first
    if not st.session_state.verified_ai:
        st.warning("⚠️ You must verify the AI suggestion with a second AI model before acting.")
        if st.button("🔍 Verify AI Suggestion"):
            with st.spinner("Verifying with a second AI model..."):
                time.sleep(3) # The 3-second friction
            st.session_state.verified_ai = True
            st.rerun()
            
    # Step 2: Show buttons only after verification
    else:
        st.success("Verification Complete. Please select an action.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("❌ Reject AI suggestion", use_container_width=True):
                save_response(tweet, "Reject")
                next_tweet()
        with col2:
            if st.button("✅ Approve AI suggestion", use_container_width=True):
                save_response(tweet, "Approve")
                next_tweet()

def render_controls_condition_C(tweet):
    """High Friction: Free Text Justification (Min 5 words)."""
    st.subheader("Action")
    
    st.markdown("To take action, please write a brief justification for your decision regarding the AI's suggestion.")
    
    # Text input area
    # We use a specific key based on tweet ID to ensure the text clears when moving to the next tweet
    reason = st.text_area(
        "Why are you Approving or Rejecting this suggestion?",
        height=100,
        placeholder="E.g. This tweet contains specific hate speech against a group...",
        key=f"reason_{tweet['id']}" 
    )
    
    # Word Count Logic
    # Split by whitespace to count words, filter out empty strings
    words = [w for w in reason.split() if w.strip()]
    word_count = len(words)
    min_words = 5
    
    # Check validity
    is_disabled = word_count < min_words
    
    # UI Feedback
    if is_disabled:
        words_needed = min_words - word_count
        st.caption(f"📝 **Please write at least {words_needed} more word(s) to unlock the buttons.**")
    else:
        st.success("✅ Length requirement met.")

    col1, col2 = st.columns(2)
    with col1:
        # Button: Reject AI
        if st.button("❌ Reject AI suggestion", disabled=is_disabled, use_container_width=True):
            save_response(tweet, "Reject", reason)
            next_tweet()
            
    with col2:
        # Button: Approve AI
        if st.button("✅ Approve AI suggestion", disabled=is_disabled, use_container_width=True):
            save_response(tweet, "Approve", reason)
            next_tweet()

def render_survey():
    st.title("Post-Experiment Survey")
    st.markdown("Please rate your agreement with the following statements regarding the task you just completed.")
    st.markdown("**(1 = Strongly Disagree, 7 = Strongly Agree)**")
    st.write("---")

    questions = [
        "I felt that I was the one controlling the moderation decisions.",
        "The outcomes of the task were primarily determined by my actions, not the AI's.",
        "The final decisions reflected my own judgment, regardless of the AI's suggestion.",
        "I feel completely responsible for the consequences of the decisions made.",
        "I felt like I was just an instrument in the hands of the AI.",
        "I felt like a passive observer rather than an active decision-maker."
    ]
    
    # We use a form so the page doesn't reload on every click
    with st.form("survey_form"):
        answers = []
        for i, q in enumerate(questions):
            st.markdown(f"**{q}**")
            # Horizontal radio button usually looks best for Likert
            ans = st.radio(
                f"q{i}", 
                options=[1, 2, 3, 4, 5, 6, 7], 
                horizontal=True, 
                label_visibility="collapsed",
                index=3 # Default to neutral (4) to prevent NoneType errors, or remove to force choice
            )
            answers.append(ans)
            st.write("") # Spacer

        submitted = st.form_submit_button("Submit & Finish", type="primary")
        
        if submitted:
            save_survey_results(answers)
            st.session_state.survey_complete = True
            st.rerun()

def render_guidelines():
    st.title("📜 Community Guidelines")
    st.markdown("""
    You must classify tweets based strictly on the following policy. 
    **Please read these rules carefully.**
    """)
    
    # Use a warning box to make it stand out as "The Rules"
    with st.container(border=True):
        st.markdown("### Content Policy")
        
        st.markdown("""
        1. **Direct Hate:** Statements explicitly attacking a group are **Toxic**.
        2. **Sarcasm:** Using positive words to mock a group is **Toxic**.
        3. **Reporting:** Quoting a slur to complain about it is **Safe**.
        4. **Self-Referential:** Using a slur to describe oneself (reclaiming) is **Safe**.
        5. **Neutral:** Opinions about non-protected topics (food, weather) are **Safe**.
                    
        You have to approve or reject the AI's suggestion based on these rules.
        """)
    
    st.write("")
    st.write("")
    
    if st.button("I understand the rules - Start Task", type="primary"):
        st.session_state.guidelines_complete = True
        st.rerun()

def render_policy_helper():
    """Renders the collapsible policy cheat sheet."""
    with st.expander("Show Content Policy Guidelines"):
        st.markdown("""
        **1. Direct Hate:** Statements explicitly attacking a group are **Toxic**.
        
        **2. Sarcasm:** Using positive words to mock a group is **Toxic**.
        
        **3. Reporting:** Quoting a slur to complain about it is **Safe**.
        
        **4. Self-Referential:** Using a slur to describe oneself (reclaiming) is **Safe**.
        
        **5. Neutral:** Opinions about non-protected topics (food, weather) are **Safe**.
                    
        You have to approve or reject the AI's suggestion based on these rules.
        """)

# --- MAIN APP LOGIC ---

def main():
    st.set_page_config(page_title="Moderation Experiment", page_icon="⚖️")
    init_session_state()

    # Router
    if st.session_state.survey_complete:
        st.balloons()
        st.title("Experiment Complete")
        st.success("Thank you for your participation!")
        st.write("Your responses have been recorded.")
        
    elif 'started' not in st.session_state:
        render_intro()

    elif st.session_state.experiment_complete:
        render_survey()

    # Only show if intro is done (started=True) but prescreening are NOT done
    elif st.session_state.get('started', False) and not st.session_state.prescreening_complete:
        render_prescreening()

    elif st.session_state.prescreening_complete and not st.session_state.guidelines_complete:
        render_guidelines()

    else:
        # Experiment Loop
        current_tweet = TWEETS[st.session_state.current_tweet_index]

        render_policy_helper()
        
        render_tweet_card(current_tweet)
        
        # Branch based on condition
        if st.session_state.condition == 'A':
            render_controls_condition_A(current_tweet)
        elif st.session_state.condition == 'B':
            render_controls_condition_B(current_tweet)
        elif st.session_state.condition == 'C':
            render_controls_condition_C(current_tweet)

if __name__ == "__main__":
    main()