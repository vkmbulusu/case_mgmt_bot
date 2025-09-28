import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import os

# Import your bot
from api_support_bot import QuickSupportBot

# Page config
st.set_page_config(
    page_title="API Support Bot",
    page_icon="🤖",
    layout="wide"
)

# Get API key from secrets
try:
    api_key = st.secrets["OPENROUTER_API_KEY"]
except:
    st.error("❌ OPENROUTER_API_KEY not found in secrets. Please add it in your Streamlit app settings.")
    st.stop()

# Initialize session state
if 'bot' not in st.session_state:
    try:
        st.session_state.bot = QuickSupportBot("balanced", api_key)
        st.session_state.messages = []
        st.success("✅ Bot initialized successfully!")
    except Exception as e:
        st.error(f"❌ Error initializing bot: {e}")
        st.stop()

# Sidebar
st.sidebar.title("🤖 API Support Bot")
st.sidebar.markdown("---")

# Model selection
model_options = ["fast", "balanced", "smart", "premium"]
selected_model = st.sidebar.selectbox("AI Model", model_options, index=1)

if st.sidebar.button("Switch Model"):
    result = st.session_state.bot.change_model(selected_model)
    st.sidebar.success(result)

# Quick stats in sidebar
try:
    conn = sqlite3.connect(st.session_state.bot.db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM cases")
    total_cases = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cases WHERE case_status = 'Open'")
    open_cases = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM updates WHERE date(timestamp) = date('now')")
    today_updates = cursor.fetchone()[0]
    
    conn.close()
    
    st.sidebar.metric("Total Cases", total_cases)
    st.sidebar.metric("Open Cases", open_cases)
    st.sidebar.metric("Today's Updates", today_updates)
    
except Exception as e:
    st.sidebar.error(f"Error loading stats: {e}")

# Main interface
st.title("🤖 API Support Bot")
st.markdown("Natural language interface for managing API integration support cases")

# Tabs
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Dashboard", "📋 Cases"])

with tab1:
    st.subheader("Chat with the Bot")
    
    # Example commands
    with st.expander("💡 Example Commands"):
        st.markdown("""
        **Create a new case:**
        - "New case for Acme Corp on Amazon marketplace, Product API integration issue, high priority"
        - "Create case for StartupXYZ having eBay inventory sync problems, urgent"
        
        **Update existing case:**
        - "Update CASE-0001: Provided API credentials to seller"
        - "Update CASE-0002: Issue resolved, seller is now live"
        
        **Query case information:**
        - "Show case CASE-0001"
        - "Display details for CASE-0002"
        """)
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get bot response
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                try:
                    response = st.session_state.bot.process_message("streamlit_user", prompt)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

with tab2:
    st.subheader("📊 Analytics Dashboard")
    
    try:
        conn = sqlite3.connect(st.session_state.bot.db_path)
        
        # Load data
        cases_df = pd.read_sql_query("SELECT * FROM cases", conn)
        updates_df = pd.read_sql_query("SELECT * FROM updates", conn)
        
        if not cases_df.empty:
            # Metrics row
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Cases", len(cases_df))
            with col2:
                open_cases = len(cases_df[cases_df['case_status'] == 'Open'])
                st.metric("Open Cases", open_cases)
            with col3:
                if len(cases_df) > 0:
                    avg_priority = cases_df['priority'].mode().iloc[0]
                else:
                    avg_priority = "N/A"
                st.metric("Most Common Priority", avg_priority)
            with col4:
                unique_marketplaces = cases_df['marketplace'].nunique()
                st.metric("Marketplaces", unique_marketplaces)
            
            # Charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Cases by Status")
                status_counts = cases_df['case_status'].value_counts()
                st.bar_chart(status_counts)
            
            with col2:
                st.subheader("Cases by Marketplace")
                marketplace_counts = cases_df['marketplace'].value_counts()
                st.bar_chart(marketplace_counts)
            
            # More charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Priority Distribution")
                priority_counts = cases_df['priority'].value_counts()
                st.bar_chart(priority_counts)
            
            with col2:
                st.subheader("API Issues")
                api_counts = cases_df['api_supported'].value_counts()
                st.bar_chart(api_counts)
        else:
            st.info("No cases found. Create some cases using the chat interface!")
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")

with tab3:
    st.subheader("📋 All Cases")
    
    try:
        conn = sqlite3.connect(st.session_state.bot.db_path)
        cases_df = pd.read_sql_query("SELECT * FROM cases ORDER BY created_at DESC", conn)
        
        if not cases_df.empty:
            # Filters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status_filter = st.selectbox("Filter by Status", 
                                           ["All"] + list(cases_df['case_status'].unique()))
            with col2:
                marketplace_filter = st.selectbox("Filter by Marketplace", 
                                                ["All"] + list(cases_df['marketplace'].unique()))
            with col3:
                priority_filter = st.selectbox("Filter by Priority", 
                                             ["All"] + list(cases_df['priority'].unique()))
            
            # Apply filters
            filtered_df = cases_df.copy()
            if status_filter != "All":
                filtered_df = filtered_df[filtered_df['case_status'] == status_filter]
            if marketplace_filter != "All":
                filtered_df = filtered_df[filtered_df['marketplace'] == marketplace_filter]
            if priority_filter != "All":
                filtered_df = filtered_df[filtered_df['priority'] == priority_filter]
            
            # Display table
            st.dataframe(
                filtered_df[['case_id', 'seller_name', 'marketplace', 'case_status', 
                            'priority', 'issue_type', 'api_supported']],
                use_container_width=True
            )
            
            # Case details
            case_options = ["Select a case..."] + list(filtered_df['case_id'].tolist())
            selected_case = st.selectbox("View Case Details", case_options)
            
            if selected_case != "Select a case...":
                case_details = filtered_df[filtered_df['case_id'] == selected_case].iloc[0]
                
                st.markdown(f"### Case {selected_case}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Seller:** {case_details['seller_name']}")
                    st.markdown(f"**Marketplace:** {case_details['marketplace']}")
                    st.markdown(f"**Priority:** {case_details['priority']}")
                    st.markdown(f"**Status:** {case_details['case_status']}")
                
                with col2:
                    st.markdown(f"**API:** {case_details['api_supported']}")
                    st.markdown(f"**Issue Type:** {case_details['issue_type']}")
                    st.markdown(f"**Specialist:** {case_details['specialist_name']}")
                    st.markdown(f"**Created:** {case_details['created_at'][:10]}")
                
                st.markdown(f"**Notes:** {case_details['notes']}")
                
                # Show updates
                updates_df = pd.read_sql_query(
                    "SELECT * FROM updates WHERE case_id = ? ORDER BY timestamp DESC", 
                    conn, params=(selected_case,)
                )
                
                if not updates_df.empty:
                    st.markdown("**Recent Updates:**")
                    for _, update in updates_df.iterrows():
                        st.markdown(f"• {update['timestamp'][:10]} by {update['updated_by']}: {update['note']}")
        else:
            st.info("No cases found. Create some cases using the chat interface!")
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error loading cases: {e}")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### 💡 Quick Actions")
if st.sidebar.button("🔄 Refresh Data"):
    st.experimental_rerun()

st.sidebar.markdown("### ℹ️ About")
st.sidebar.info("API Support Bot v1.0 - Natural language interface for managing API integration support cases.")
