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
