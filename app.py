import streamlit as st
import sqlite3
from datetime import datetime, date
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
        st.session_state.awaiting_case_info = False
        st.success("✅ Bot initialized successfully!")
    except Exception as e:
        st.error(f"❌ Error initializing bot: {e}")
        st.stop()

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
    active_cases = len([c for c in cases if c[3] in ['SUBMITTED', 'WIP', 'AWAITING INFORMATION']])
    
    st.sidebar.metric("Total Cases", total_cases)
    st.sidebar.metric("Active Cases", active_cases)
    
except Exception as e:
    st.sidebar.error(f"Error loading stats: {e}")

# Main interface
st.title("🤖 API Support Bot Enhanced")
st.markdown("Advanced case management with analytics and interactive workflows")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "➕ Create Case", "📊 Dashboard", "📋 Cases"])

with tab1:
    st.subheader("Chat Interface")
    
    # Quick actions
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🆕 Start New Case"):
            st.session_state.awaiting_case_info = True
            st.session_state.messages.append({
                "role": "assistant", 
                "content": """🆕 **Starting New Case Creation**

Please provide the following information to create a new case:

**Required:**
- Seller name
- Issue description

**Optional:**
- Amazon Case ID (AMZ-xxxxxxxx)
- Marketplace (EU, NA, etc.)
- Priority (Low/Medium/High)
- Workstream
- API involved

You can provide this information in natural language, for example:
"New case for TechCorp on EU marketplace, Product API authentication issue, high priority, Amazon case AMZ-123456789"
"""
            })
    
    with col2:
        if st.button("🔍 Query Case"):
            st.session_state.messages.append({
                "role": "assistant", 
                "content": """🔍 **Query Case Information**

Please provide a case ID to get detailed information.

Examples:
- "Show case CASE-0001"
- "Display details for CASE-0002" 
- "Get info on CASE-0003"
"""
            })
    
    with col3:
        if st.button("🔄 Update Case"):
            st.session_state.messages.append({
                "role": "assistant", 
                "content": """🔄 **Update Case**

Please specify the case ID and update details.

Examples:
- "Update CASE-0001: API credentials validated, moving to PMA"
- "Update CASE-0002: Issue resolved, CSAT score 5, feedback received"
- "Update CASE-0003: On hold due to seller unavailability"

You can include:
- Sub-status changes
- Completion dates
- CSAT scores
- Feedback status
"""
            })
    
    with col4:
        if st.button("📊 Analytics"):
            st.session_state.messages.append({
                "role": "assistant", 
                "content": """📊 **Analytics Queries**

Ask me about case statistics and analysis.

Examples:
- "How many cases are in WIP status?"
- "Show me EU marketplace cases"
- "Count Smart Connect workstream cases"
- "High priority cases by marketplace"
- "Cases in ON_HOLD sub-status"
"""
            })
    
    # Example queries
    with st.expander("💡 Example Commands"):
        st.markdown("""
        **Create Cases:**
        - "New case for Acme Corp on EU marketplace, Product API integration issue, high priority, Amazon case AMZ-123456789"
        
        **Update Cases:**
        - "Update CASE-0001: Credentials validated, moving to PMA status"
        - "Update CASE-0002: Issue resolved, completion date 2024-01-20, CSAT 5"
        
        **Query Cases:**
        - "Show case CASE-0001"
        - "Display details for CASE-0002"
        
        **Analytics:**
        - "How many WIP cases in EU marketplace for Smart Connect workstream?"
        - "Show me high priority cases by marketplace"
        - "Count of cases in PMA sub-status"
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
        
        # Process message
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                try:
                    # Process through the bot
                    response = st.session_state.bot.process_message("streamlit_user", prompt)
                    
                    # Check if this was a case creation attempt
                    intent = st.session_state.bot.determine_intent(prompt)
                    if "create" in intent and st.session_state.awaiting_case_info:
                        st.session_state.awaiting_case_info = False
                        # Extract and store data for Create Case tab
                        extracted_data = st.session_state.bot.extract_case_info(prompt)
                        if "error" not in extracted_data:
                            st.session_state.extracted_data = extracted_data
                            response += "\n\n🎯 **Information extracted!** Please review and complete in the 'Create Case' tab."
                    
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
            issue_type = st.text_input("Issue Type *", value=extracted.get('issue_type', ''))
        
        with col2:
            complexity = st.selectbox("Complexity *", COMPLEXITIES,
                                    index=COMPLEXITIES.index(extracted.get('complexity')) if extracted.get('complexity') in COMPLEXITIES else 1)
            priority = st.selectbox("Priority *", PRIORITIES,
                                  index=PRIORITIES.index(extracted.get('priority')) if extracted.get('priority') in PRIORITIES else 1)
            seller_type = st.selectbox("Seller Type *", SELLER_TYPES,
                                     index=SELLER_TYPES.index(extracted.get('seller_type')) if extracted.get('seller_type') in SELLER_TYPES else 1)
            api_supported = st.text_input("API Supported", value=extracted.get('api_supported', 'General API'))
            
            # Fixed date input with proper null handling
            listing_start_date = st.date_input("Listing Start Date (Optional)", value=None)
            listing_completion_date = st.date_input("Listing Completion Date (Optional)", value=None)
            
            feedback_received = st.selectbox("Feedback Received", ["No", "Yes"])
        
        notes = st.text_area("Notes", value=extracted.get('notes', ''), height=100)
        
        # CSAT score only if feedback received
        if feedback_received == "Yes":
            csat_score = st.slider("CSAT Score", 1.0, 5.0, 3.0, 0.5)
        else:
            csat_score = None
        
        # Form submission buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            submit_case = st.form_submit_button("✅ Create Case", type="primary")
        
        with col2:
            clear_form = st.form_submit_button("🔄 Clear Form")
        
        # Handle form submission
        if submit_case:
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
                    'listing_start_date': listing_start_date.strftime('%Y-%m-%d') if listing_start_date else '',
                    'listing_completion_date': listing_completion_date.strftime('%Y-%m-%d') if listing_completion_date else '',
                    'feedback_received': feedback_received,
                    'csat_score': csat_score,
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
                    
                except Exception as e:
                    st.error(f"❌ Error creating case: {e}")
            else:
                st.error("❌ Please fill in all required fields (marked with *)")
        
        if clear_form:
            st.session_state.extracted_data = {}
            st.rerun()

with tab3:
    st.subheader("📊 Advanced Analytics Dashboard")
    
    # Date filters
    st.markdown("### 📅 Date Filters")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        listing_start = st.date_input("Listing Start Date From", value=date(2024, 1, 1))
    with col2:
        listing_end = st.date_input("Listing Start Date To", value=date.today())
    with col3:
        created_start = st.date_input("Created Date From", value=date(2024, 1, 1))
    with col4:
        created_end = st.date_input("Created Date To", value=date.today())
    
    # Get hierarchical data
    try:
        df = st.session_state.bot.get_hierarchical_data(
            listing_start.strftime('%Y-%m-%d'),
            listing_end.strftime('%Y-%m-%d'),
            created_start.strftime('%Y-%m-%d'),
            created_end.strftime('%Y-%m-%d')
        )
        
        if not df.empty:
            # Summary metrics
            st.markdown("### 📈 Summary Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Cases", len(df))
            with col2:
                st.metric("Workstreams", df['workstream'].nunique())
            with col3:
                st.metric("Marketplaces", df['marketplace'].nunique())
            with col4:
                st.metric("Specialists", df['specialist_id'].nunique())
            
            # Hierarchical Data Table
            st.markdown("### 🗂️ Hierarchical Case Data")
            st.markdown("**Workstream → Marketplace → Issue Type → API → Status → Latest Sub Status**")
            
            # Filters for the hierarchical table
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                workstream_filter = st.multiselect("Filter Workstreams", 
                                                 options=df['workstream'].unique(),
                                                 default=df['workstream'].unique())
            with col2:
                marketplace_filter = st.multiselect("Filter Marketplaces", 
                                                   options=df['marketplace'].unique(),
                                                   default=df['marketplace'].unique())
            with col3:
                status_filter = st.multiselect("Filter Case Status", 
                                             options=df['case_status'].unique(),
                                             default=df['case_status'].unique())
            with col4:
                specialist_filter = st.multiselect("Filter Specialists", 
                                                  options=df['specialist_id'].unique(),
                                                  default=df['specialist_id'].unique())
            
            # Apply filters
            filtered_df = df[
                (df['workstream'].isin(workstream_filter)) &
                (df['marketplace'].isin(marketplace_filter)) &
                (df['case_status'].isin(status_filter)) &
                (df['specialist_id'].isin(specialist_filter))
            ]
            
            # Display hierarchical table
            if not filtered_df.empty:
                # Reorder columns for hierarchical view
                display_df = filtered_df[[
                    'case_id', 'seller_name', 'specialist_id', 'workstream', 
                    'marketplace', 'issue_type', 'api_supported', 
                    'case_status', 'last_sub_status', 'priority', 'created_at'
                ]].copy()
                
                display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    column_config={
                        "case_id": "Case ID",
                        "seller_name": "Seller",
                        "specialist_id": "Specialist",
                        "workstream": "Workstream",
                        "marketplace": "Marketplace",
                        "issue_type": "Issue Type",
                        "api_supported": "API",
                        "case_status": "Status",
                        "last_sub_status": "Sub-Status",
                        "priority": "Priority",
                        "created_at": "Created"
                    }
                )
                
                # Export functionality
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="📄 Download as CSV",
                    data=csv,
                    file_name=f"case_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No cases match the selected filters.")
            
            # Charts Section
            st.markdown("### 📊 Analytics Charts")
            
            # First row of charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Cases by Workstream")
                ws_counts = filtered_df['workstream'].value_counts()
                st.bar_chart(ws_counts)
            
            with col2:
                st.subheader("Cases by Marketplace")
                mp_counts = filtered_df['marketplace'].value_counts()
                st.bar_chart(mp_counts)
            
            # Second row of charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Cases by Sub-Status")
                ss_counts = filtered_df['last_sub_status'].value_counts()
                st.bar_chart(ss_counts)
            
            with col2:
                st.subheader("Cases by API")
                api_counts = filtered_df['api_supported'].value_counts()
                st.bar_chart(api_counts)
            
            # Specialist Performance Chart
            st.markdown("### 👥 Specialist Performance")
            
            try:
                specialist_df = st.session_state.bot.get_specialist_case_counts()
                
                if not specialist_df.empty:
                    # Create pivot table for better visualization
                    pivot_df = specialist_df.pivot(index=['specialist_id', 'specialist_name'], 
                                                 columns='case_status', 
                                                 values='count').fillna(0)
                    
                    # Display as stacked bar chart
                    st.bar_chart(pivot_df)
                    
                    # Also show as detailed table
                    with st.expander("📋 Detailed Specialist Breakdown"):
                        st.dataframe(specialist_df, use_container_width=True)
                else:
                    st.info("No specialist data available.")
                    
            except Exception as e:
                st.error(f"Error loading specialist data: {e}")
            
        else:
            st.info("No cases found for the selected date range.")
            
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")
        st.error(f"Debug info: {str(e)}")

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
                                st.markdown(f"**Listing Start:** {case_dict.get('listing_start_date', 'Not set')}")
                            
                            with subcol2:
                                st.markdown(f"**Issue Type:** {case_dict['issue_type']}")
                                st.markdown(f"**API:** {case_dict['api_supported']}")
                                st.markdown(f"**Workstream:** {case_dict['workstream']}")
                                st.markdown(f"**Sub-status:** {case_dict['last_sub_status']}")
                                st.markdown(f"**Feedback:** {case_dict.get('feedback_received', 'No')}")
                                st.markdown(f"**CSAT:** {case_dict.get('csat_score', 'Not rated')}")
                            
                            st.markdown(f"**Notes:** {case_dict['notes']}")
                        
                        with col2:
                            st.markdown("### Update Case")
                            
                            # Toggle between quick update and full edit
                            update_mode = st.radio("Update Mode", ["Quick Update", "Full Edit"])
                            
                            if update_mode == "Quick Update":
                                with st.form(f"quick_update_form_{selected_case}"):
                                    update_note = st.text_area("Update Note", height=100)
                                    new_substatus = st.selectbox("New Sub-Status", SUB_STATUSES, 
                                                               index=SUB_STATUSES.index(case_dict['last_sub_status']) if case_dict['last_sub_status'] in SUB_STATUSES else 0)
                                    
                                    # Additional fields for completion
                                    completion_date = st.date_input("Completion Date (if applicable)", value=None)
                                    feedback_received = st.selectbox("Feedback Received", ["No Change", "No", "Yes"])
                                    
                                    if feedback_received == "Yes":
                                        csat_score = st.slider("CSAT Score", 1.0, 5.0, 3.0, 0.5)
                                    else:
                                        csat_score = None
                                    
                                    if st.form_submit_button("Update Case"):
                                        if update_note:
                                            additional_data = {}
                                            if completion_date:
                                                additional_data['listing_completion_date'] = completion_date.strftime('%Y-%m-%d')
                                            if feedback_received != "No Change":
                                                additional_data['feedback_received'] = feedback_received
                                            if csat_score:
                                                additional_data['csat_score'] = csat_score
                                            
                                            success, message = st.session_state.bot.update_case_status(
                                                selected_case,
                                                update_note,
                                                new_substatus,
                                                'Web User',
                                                additional_data if additional_data else None
                                            )
                                            
                                            if success:
                                                st.success(message)
                                                st.rerun()
                                            else:
                                                st.error(message)
                                        else:
                                            st.error("Please provide an update note")
                            
                            else:  # Full Edit Mode
                                with st.form(f"full_edit_form_{selected_case}"):
                                    st.markdown("**Edit All Fields**")
                                    
                                    # Editable fields
                                    edit_seller_name = st.text_input("Seller Name", value=case_dict['seller_name'])
                                    edit_amazon_case_id = st.text_input("Amazon Case ID", value=case_dict.get('amazon_case_id', ''))
                                    edit_marketplace = st.selectbox("Marketplace", MARKETPLACES, 
                                                                  index=MARKETPLACES.index(case_dict['marketplace']) if case_dict['marketplace'] in MARKETPLACES else 0)
                                    edit_workstream = st.selectbox("Workstream", WORKSTREAMS,
                                                                 index=WORKSTREAMS.index(case_dict['workstream']) if case_dict['workstream'] in WORKSTREAMS else 0)
                                    edit_priority = st.selectbox("Priority", PRIORITIES,
                                                               index=PRIORITIES.index(case_dict['priority']) if case_dict['priority'] in PRIORITIES else 0)
                                    edit_issue_type = st.text_input("Issue Type", value=case_dict['issue_type'])
                                    edit_api_supported = st.text_input("API Supported", value=case_dict['api_supported'])
                                    edit_notes = st.text_area("Notes", value=case_dict['notes'], height=100)
                                    
                                    # Date fields
                                    current_start_date = datetime.strptime(case_dict['listing_start_date'], '%Y-%m-%d').date() if case_dict.get('listing_start_date') else None
                                    current_completion_date = datetime.strptime(case_dict['listing_completion_date'], '%Y-%m-%d').date() if case_dict.get('listing_completion_date') else None
                                    
                                    edit_start_date = st.date_input("Listing Start Date", value=current_start_date)
                                    edit_completion_date = st.date_input("Listing Completion Date", value=current_completion_date)
                                    
                                    edit_feedback = st.selectbox("Feedback Received", ["No", "Yes"], 
                                                               index=0 if case_dict.get('feedback_received', 'No') == 'No' else 1)
                                    
                                    if edit_feedback == "Yes":
                                        edit_csat = st.slider("CSAT Score", 1.0, 5.0, float(case_dict.get('csat_score', 3.0)), 0.5)
                                    else:
                                        edit_csat = None
                                    
                                    edit_substatus = st.selectbox("Sub-Status", SUB_STATUSES,
                                                                index=SUB_STATUSES.index(case_dict['last_sub_status']) if case_dict['last_sub_status'] in SUB_STATUSES else 0)
                                    
                                    update_note = st.text_area("Update Note (Required)", height=80)
                                    
                                    if st.form_submit_button("Save All Changes"):
                                        if update_note:
                                            # Update case in database
                                            additional_data = {
                                                'listing_start_date': edit_start_date.strftime('%Y-%m-%d') if edit_start_date else '',
                                                'listing_completion_date': edit_completion_date.strftime('%Y-%m-%d') if edit_completion_date else '',
                                                'feedback_received': edit_feedback,
                                                'csat_score': edit_csat,
                                            }
                                            
                                            success, message = st.session_state.bot.update_case_status(
                                                selected_case,
                                                f"Full case update: {update_note}",
                                                edit_substatus,
                                                'Web User',
                                                additional_data
                                            )
                                            
                                            if success:
                                                st.success("Case updated successfully!")
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
- Click "Start New Case" for guided input
- Or type naturally in chat
- Complete missing info in Create Case tab
- Dates are optional during creation

**Analytics Queries:**
- "How many WIP cases?"
- "EU marketplace cases count"  
- "Smart Connect workstream stats"

**Updates:**
- Quick Update: Note + sub-status change
- Full Edit: Modify all case fields

**Dashboard:**
- Hierarchical table view
- Multiple filters available
- Export to CSV
- Specialist performance charts
""")
