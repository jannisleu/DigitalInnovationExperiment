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
    {"id": 1, "text": "I really hate it when people don't use turn signals.", "ai_suggestion": "Keep"},
    {"id": 2, "text": "We should totally get rid of all [Group X], they are parasites.", "ai_suggestion": "Block"},
    {"id": 3, "text": "This product is the bomb! Highly recommend.", "ai_suggestion": "Keep"},
    {"id": 4, "text": "You represent everything wrong with this country. Go die.", "ai_suggestion": "Block"},
    {"id": 5, "text": "I disagree with your opinion on tax reform.", "ai_suggestion": "Keep"},
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
        
    if 'experiment_complete' not in st.session_state:
        st.session_state.experiment_complete = False

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
    st.title("🛡️ Content Moderation Task")
    st.markdown("""
    **Role:** You are a Moderator for a social media platform.
    
    **Goal:** Classify tweets as **"Safe/Keep"** or **"Toxic/Block"**.
    
    **Community Guidelines:**
    1. **Block:** Hate speech, harassment, threats of violence.
    2. **Keep:** Opinions, mild frustration, positive content.
    
    You will be assisted by an AI tool that analyzes the text and suggests an action.
    """)
    
    st.info(f"Debug Info (Hidden in prod): You are assigned Condition **{st.session_state.condition}**")
    
    if st.button("Start Experiment", type="primary"):
        st.session_state.started = True
        st.rerun()

def render_tweet_card(tweet):
    """Displays the tweet and the AI suggestion."""
    
    # Progress bar
    progress = st.session_state.current_tweet_index / len(TWEETS)
    st.progress(progress, text=f"Tweet {st.session_state.current_tweet_index + 1} of {len(TWEETS)}")

    # The Tweet
    st.markdown("### 🐦 Tweet Content")
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
        if st.button("❌ Block", use_container_width=True):
            save_response(tweet, "Block")
            next_tweet()
    with col2:
        if st.button("✅ Keep", use_container_width=True):
            save_response(tweet, "Keep")
            next_tweet()

def render_controls_condition_B(tweet):
    """Placebo Friction: Fake Verification Wait."""
    st.subheader("Action")
    
    # Step 1: Force User to "Verify" AI first
    if not st.session_state.verified_ai:
        st.warning("⚠️ You must verify the AI analysis before acting.")
        if st.button("🔍 Verify AI Analysis"):
            with st.spinner("Verifying against Community Guidelines..."):
                time.sleep(3) # The 3-second friction
            st.session_state.verified_ai = True
            st.rerun()
            
    # Step 2: Show buttons only after verification
    else:
        st.success("Verification Complete. Please select an action.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("❌ Block", use_container_width=True):
                save_response(tweet, "Block")
                next_tweet()
        with col2:
            if st.button("✅ Keep", use_container_width=True):
                save_response(tweet, "Keep")
                next_tweet()

def render_controls_condition_C(tweet):
    """High Friction: Justification Required."""
    st.subheader("Action")
    
    reason = st.selectbox(
        "Select a justification for your decision:",
        ["", "Hate Speech", "Harassment", "Spam", "Safe / Compliant", "Satire / Humor", "Other"],
        index=0
    )
    
    # Disable buttons if no reason is selected
    # Note: Streamlit buttons allow a 'disabled' param
    is_disabled = (reason == "")
    
    if is_disabled:
        st.caption("Please select a reason to enable the action buttons.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Block", disabled=is_disabled, use_container_width=True):
            save_response(tweet, "Block", reason)
            next_tweet()
    with col2:
        if st.button("✅ Keep", disabled=is_disabled, use_container_width=True):
            save_response(tweet, "Keep", reason)
            next_tweet()

# --- MAIN APP LOGIC ---

def main():
    st.set_page_config(page_title="Moderation Experiment", page_icon="⚖️")
    init_session_state()

    # Router
    if st.session_state.experiment_complete:
        st.balloons()
        st.title("Experiment Complete")
        st.success("Thank you for your participation!")
        st.write("Your responses have been recorded.")
        # Optional: Show them their own data
        #st.dataframe(pd.DataFrame(st.session_state.responses))
        
    elif 'started' not in st.session_state:
        render_intro()
        
    else:
        # Experiment Loop
        current_tweet = TWEETS[st.session_state.current_tweet_index]
        
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