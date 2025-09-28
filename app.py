import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import os

# Import your enhanced bot
from api_support_bot import QuickSupportBot, MARKETPLACES, CASE_SOURCES, WORKSTREAMS, COMPLEXITIES, PRIORITIES, SELLER_TYPES, SUB_STATUSES

# Page config
st.set_page_config(
    page_title="API Support Bot Enhanced",
    page_icon="🤖",
    layout="wide"
)

# Get API key from secrets
try:
    api_key = st.secrets["OPENROUTER_API_KEY"]
except:
    st.error("❌ OPENROUTER_API_KEY not found in secrets.")
    st.stop()

# Initialize session state
if 'bot' not in st.session_state:
    try:
        st.session_state.bot = QuickSupportBot("balanced", api_key)
        st.session_state.messages = []
        st.session_state.case_creation_mode = False
        st.session_state.extracted_data = {}
        st.success("✅ Bot initialized successfully!")
    except Exception as e:
        st.error(f"❌ Error initializing bot: {e}")
        st.stop()

# Helper function to validate and clean data
def validate_case_data(data):
    """Validate case data against business rules"""
    errors = []
    
    if not data.get('seller_name'):
        errors.append("Seller name is required")
    
    if data.get('marketplace') and data['marketplace'] not in MARKETPLACES:
        errors.append(f"Marketplace must be one of: {', '.join(MARKETPLACES)}")
    
    if data.get('case_source') and data['case_source'] not in CASE_SOURCES:
        errors.append(f"Case source must be one of: {', '.join(CASE_SOURCES)}")
    
    if data.get('workstream') and data['workstream'] not in WORKSTREAMS:
        errors.append(f"Workstream must be one of: {', '.join(WORKSTREAMS)}")
    
    return errors

# Sidebar
st.sidebar.title("🤖 API Support Bot Enhanced")
st.sidebar.markdown("---")

# Model selection
model_options = ["fast", "balanced", "smart", "premium"]
selected_model = st.sidebar.selectbox("AI Model", model_options, index=1)

if st.sidebar.button("Switch Model"):
    result = st.session_state.bot.change_model(selected_model)
    st.sidebar.success(result)

# Quick stats
try:
    cases = st.session_state.bot.show_all_cases()
    total_cases = len(cases)
    open_cases = len([c for c in cases if c[3] in ['SUBMITTED', 'WIP', 'AWAITING INFORMATION']])
    
    st.sidebar.metric("Total Cases", total_cases)
    st.sidebar.metric("Active Cases", open_cases)
    
except Exception as e:
    st.sidebar.error(f"Error loading stats: {e}")

# Main interface
st.title("🤖 API Support Bot Enhanced")
st.markdown("Advanced case management with interactive workflows")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "➕ Create Case", "📊 Dashboard", "📋 Cases"])

with tab1:
    st.subheader("Chat Interface")
    
    # Quick actions
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🆕 Start New Case"):
            st.session_state.case_creation_mode = True
            st.rerun()
    
    with col2:
        if st.button("🔍 Query Case"):
            st.session_state.messages.append({
                "role": "assistant", 
                "content": "Please provide a case ID (e.g., CASE-0001) to query."
            })
    
    with col3:
        if st.button("🔄 Update Case"):
            st.session_state.messages.append({
                "role": "assistant", 
                "content": "Please specify the case ID and update details (e.g., 'Update CASE-0001: Issue resolved')."
            })
    
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
        
        # Process message
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                try:
                    # Determine intent
                    intent = st.session_state.bot.determine_intent(prompt)
                    
                    if "create" in intent:
                        # Extract information for case creation
                        extracted_data = st.session_state.bot.extract_case_info(prompt)
                        
                        if "error" not in extracted_data:
                            st.session_state.extracted_data = extracted_data
                            st.session_state.case_creation_mode = True
                            
                            response = "🎯 **Information Extracted!** Please review and complete the missing information in the 'Create Case' tab."
                        else:
                            response = f"❌ Error extracting information: {extracted_data['error']}"
                    
                    elif "update" in intent:
                        # Extract update information
                        update_data = st.session_state.bot.extract_update_info(prompt)
                        
                        if "error" not in update_data and update_data.get('case_id'):
                            success, message = st.session_state.bot.update_case_status(
                                update_data['case_id'],
                                update_data.get('note', 'Update from chat'),
                                update_data.get('sub_status', 'Note'),
                                'Chat User'
                            )
                            
                            if success:
                                response = f"✅ **{message}**\n\n**Note:** {update_data.get('note', 'Update recorded')}\n**Sub-status:** {update_data.get('sub_status', 'Note')}"
                            else:
                                response = f"❌ {message}"
                        else:
                            response = "❌ Please specify a valid case ID and update details."
                    
                    elif "query" in intent:
                        # Extract case ID from prompt
                        words = prompt.upper().split()
                        case_id = None
                        for word in words:
                            if word.startswith('CASE-'):
                                case_id = word
                                break
                        
                        if case_id:
                            case_dict, updates = st.session_state.bot.query_case(case_id)
                            
                            if case_dict:
                                updates_text = ""
                                if updates:
                                    updates_text = "\n\n**Recent Updates:**"
                                    for note, updated_by, timestamp, sub_status in updates:
                                        date = timestamp.split('T')[0]
                                        updates_text += f"\n• {date}: {note} ({sub_status})"
                                
                                response = f"""📋 **Case {case_id}**

**Seller:** {case_dict['seller_name']} (ID: {case_dict['seller_id']})
**Amazon Case ID:** {case_dict.get('amazon_case_id', 'Not provided')}
**Marketplace:** {case_dict['marketplace']}
**Issue:** {case_dict['issue_type']}
**Priority:** {case_dict['priority']} | **Status:** {case_dict['case_status']}
**Sub-status:** {case_dict.get('last_sub_status', 'None')}
**API:** {case_dict['api_supported']}
**Workstream:** {case_dict['workstream']}
**Specialist:** {case_dict['specialist_name']}

**Notes:** {case_dict.get('notes', 'None')}{updates_text}"""
                            else:
                                response = f"❌ Case {case_id} not found"
                        else:
                            response = "❌ Please specify a case ID (e.g., 'show case CASE-0001')"
                    
                    else:
                        response = """❓ I'm not sure what you want to do. Try:
- 'New case for [seller] on [marketplace]'
- 'Update CASE-0001: [description]'  
- 'Show case CASE-0001'
- Or use the quick action buttons above"""
                    
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

with tab2:
    st.subheader("➕ Create New Case")
    
    # Use extracted data if available
    if st.session_state.get('extracted_data'):
        st.success("🎯 Information extracted from your message!")
        extracted = st.session_state.extracted_data
    else:
        extracted = {}
    
    # Case creation form
    with st.form("case_creation_form"):
        st.markdown("### Case Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            seller_name = st.text_input("Seller Name *", value=extracted.get('seller_name', ''))
            amazon_case_id = st.text_input("Amazon Case ID", value=extracted.get('amazon_case_id', ''))
            marketplace = st.selectbox("Marketplace *", MARKETPLACES, 
                                     index=MARKETPLACES.index(extracted.get('marketplace')) if extracted.get('marketplace') in MARKETPLACES else 0)
            case_source = st.selectbox("Case Source *", CASE_SOURCES,
                                     index=CASE_SOURCES.index(extracted.get('case_source')) if extracted.get('case_source') in CASE_SOURCES else 0)
            workstream = st.selectbox("Workstream *", WORKSTREAMS,
                                    index=WORKSTREAMS.index(extracted.get('workstream')) if extracted.get('workstream') in WORKSTREAMS else 0)
        
        with col2:
            issue_type = st.text_input("Issue Type *", value=extracted.get('issue_type', ''))
            complexity = st.selectbox("Complexity *", COMPLEXITIES,
                                    index=COMPLEXITIES.index(extracted.get('complexity')) if extracted.get('complexity') in COMPLEXITIES else 1)
            priority = st.selectbox("Priority *", PRIORITIES,
                                  index=PRIORITIES.index(extracted.get('priority')) if extracted.get('priority') in PRIORITIES else 1)
            seller_type = st.selectbox("Seller Type *", SELLER_TYPES,
                                     index=SELLER_TYPES.index(extracted.get('seller_type')) if extracted.get('seller_type') in SELLER_TYPES else 1)
            api_supported = st.text_input("API Supported", value=extracted.get('api_supported', 'General API'))
        
        notes = st.text_area("Notes", value=extracted.get('notes', ''), height=100)
        
        # Form submission
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.form_submit_button("✅ Create Case", type="primary"):
                # Validate required fields
                if seller_name and issue_type:
                    case_data = {
                        'seller_name': seller_name,
                        'amazon_case_id': amazon_case_id,
                        'marketplace': marketplace,
                        'case_source': case_source,
                        'workstream': workstream,
                        'issue_type': issue_type,
                        'complexity': complexity,
                        'priority': priority,
                        'seller_type': seller_type,
                        'api_supported': api_supported,
                        'notes': notes
                    }
                    
                    try:
                        case_id, created_case = st.session_state.bot.create_case_from_data(case_data)
                        
                        st.success(f"""✅ **Case Created Successfully!**
                        
**Case ID:** {case_id}
**Seller:** {created_case['seller_name']}
**Marketplace:** {created_case['marketplace']}
**Priority:** {created_case['priority']}
**Workstream:** {created_case['workstream']}""")
                        
                        # Clear form data
                        st.session_state.extracted_data = {}
                        st.session_state.case_creation_mode = False
                        
                    except Exception as e:
                        st.error(f"❌ Error creating case: {e}")
                else:
                    st.error("❌ Please fill in all required fields (marked with *)")
        
        with col2:
            if st.form_submit_button("🔄 Clear Form"):
                st.session_state.extracted_data = {}
                st.rerun()

with tab3:
    st.subheader("📊 Analytics Dashboard")
    
    try:
        cases = st.session_state.bot.show_all_cases()
        
        if cases:
            # Convert to DataFrame
            df = pd.DataFrame(cases, columns=['case_id', 'seller_name', 'marketplace', 'case_status', 'priority', 'issue_type', 'last_sub_status'])
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Cases", len(df))
            with col2:
                active_cases = len(df[df['case_status'].isin(['SUBMITTED', 'WIP', 'AWAITING INFORMATION'])])
                st.metric("Active Cases", active_cases)
            with col3:
                high_priority = len(df[df['priority'] == 'High'])
                st.metric("High Priority", high_priority)
            with col4:
                unique_marketplaces = df['marketplace'].nunique()
                st.metric("Marketplaces", unique_marketplaces)
            
            # Charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Cases by Status")
                status_counts = df['case_status'].value_counts()
                st.bar_chart(status_counts)
            
            with col2:
                st.subheader("Cases by Sub-Status")
                substatus_counts = df['last_sub_status'].value_counts()
                st.bar_chart(substatus_counts)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Cases by Marketplace")
                marketplace_counts = df['marketplace'].value_counts()
                st.bar_chart(marketplace_counts)
            
            with col2:
                st.subheader("Priority Distribution")
                priority_counts = df['priority'].value_counts()
                st.bar_chart(priority_counts)
        else:
            st.info("No cases found. Create some cases to see analytics!")
            
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")

with tab4:
    st.subheader("📋 Case Management")
    
    try:
        cases = st.session_state.bot.show_all_cases()
        
        if cases:
            # Convert to DataFrame for filtering
            df = pd.DataFrame(cases, columns=['case_id', 'seller_name', 'marketplace', 'case_status', 'priority', 'issue_type', 'last_sub_status'])
            
            # Filters
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                status_filter = st.selectbox("Filter by Status", ["All"] + list(df['case_status'].unique()))
            with col2:
                marketplace_filter = st.selectbox("Filter by Marketplace", ["All"] + list(df['marketplace'].unique()))
            with col3:
                priority_filter = st.selectbox("Filter by Priority", ["All"] + list(df['priority'].unique()))
            with col4:
                substatus_filter = st.selectbox("Filter by Sub-Status", ["All"] + list(df['last_sub_status'].unique()))
            
            # Apply filters
            filtered_df = df.copy()
            if status_filter != "All":
                filtered_df = filtered_df[filtered_df['case_status'] == status_filter]
            if marketplace_filter != "All":
                filtered_df = filtered_df[filtered_df['marketplace'] == marketplace_filter]
            if priority_filter != "All":
                filtered_df = filtered_df[filtered_df['priority'] == priority_filter]
            if substatus_filter != "All":
                filtered_df = filtered_df[filtered_df['last_sub_status'] == substatus_filter]
            
            # Display table
            st.dataframe(filtered_df, use_container_width=True)
            
            # Case details and update section
            if len(filtered_df) > 0:
                st.markdown("---")
                
                selected_case = st.selectbox("Select Case for Details/Update", 
                                           ["Select a case..."] + list(filtered_df['case_id'].tolist()))
                
                if selected_case != "Select a case...":
                    case_dict, updates = st.session_state.bot.query_case(selected_case)
                    
                    if case_dict:
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"### Case {selected_case}")
                            
                            subcol1, subcol2 = st.columns(2)
                            
                            with subcol1:
                                st.markdown(f"**Seller:** {case_dict['seller_name']}")
                                st.markdown(f"**Amazon Case ID:** {case_dict.get('amazon_case_id', 'Not provided')}")
                                st.markdown(f"**Marketplace:** {case_dict['marketplace']}")
                                st.markdown(f"**Priority:** {case_dict['priority']}")
                                st.markdown(f"**Status:** {case_dict['case_status']}")
                            
                            with subcol2:
                                st.markdown(f"**Issue Type:** {case_dict['issue_type']}")
                                st.markdown(f"**API:** {case_dict['api_supported']}")
                                st.markdown(f"**Workstream:** {case_dict['workstream']}")
                                st.markdown(f"**Sub-status:** {case_dict['last_sub_status']}")
                                st.markdown(f"**Created:** {case_dict['created_at'][:10]}")
                            
                            st.markdown(f"**Notes:** {case_dict['notes']}")
                        
                        with col2:
                            st.markdown("### Quick Update")
                            
                            with st.form(f"update_form_{selected_case}"):
                                update_note = st.text_area("Update Note", height=100)
                                new_substatus = st.selectbox("New Sub-Status", SUB_STATUSES)
                                
                                if st.form_submit_button("Update Case"):
                                    if update_note:
                                        success, message = st.session_state.bot.update_case_status(
                                            selected_case,
                                            update_note,
                                            new_substatus,
                                            'Web User'
                                        )
                                        
                                        if success:
                                            st.success(message)
                                            st.rerun()
                                        else:
                                            st.error(message)
                                    else:
                                        st.error("Please provide an update note")
                        
                        # Show update history
                        if updates:
                            st.markdown("### Update History")
                            for note, updated_by, timestamp, sub_status in updates:
                                with st.expander(f"{timestamp[:16]} - {sub_status}"):
                                    st.markdown(f"**Updated by:** {updated_by}")
                                    st.markdown(f"**Note:** {note}")
        else:
            st.info("No cases found. Create some cases using the chat interface or Create Case tab!")
            
    except Exception as e:
        st.error(f"Error loading cases: {e}")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### 💡 Quick Guide")
st.sidebar.markdown("""
**Creating Cases:**
- Use natural language in chat
- Fill missing info in Create Case tab
- Confirm before creation

**Updating Cases:**
- Focus on sub-status changes
- Each update gets timestamped
- Latest sub-status = current status

**Querying:**
- Use case ID (CASE-0001)
- View full history
- Export data
""")
