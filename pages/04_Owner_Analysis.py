"""
Owner Analysis page for BPMN Analysis app.
This page is automatically generated from the main application tabs.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from bpmn_analyzer import categorize_opportunity, categorize_issue
from utils.shared import setup_file_upload, get_combined_tasks, get_analysis_data, has_data, render_page_header, render_sidebar_header

# Render sidebar header
render_sidebar_header()

# Set up file upload in sidebar (visible on all pages)
setup_file_upload()

# Render page header
render_page_header("Owner Analysis", "👥")

# Check if data is available
if not has_data():
    st.info("👆 Please upload BPMN XML files on the main page to start the analysis.")
else:
    # Get data from session state
    combined_tasks = get_combined_tasks()
    analysis_data = get_analysis_data()
    

    # Group by owner
    owner_analysis = {}
    for task in combined_tasks:
        owner = task.get('task_owner', 'Unknown')
        if owner not in owner_analysis:
            owner_analysis[owner] = {
                'task_count': 0,
                'total_cost': 0,
                'total_time_minutes': 0
            }

        owner_analysis[owner]['task_count'] += 1
        owner_analysis[owner]['total_cost'] += task.get('total_cost', 0)
        owner_analysis[owner]['total_time_minutes'] += task.get('time_minutes', 0)

    # Create owner analysis dataframe
    owner_df = pd.DataFrame(owner_analysis).T.reset_index()
    # Rename columns to match expected structure
    owner_df.columns = ['Owner', 'Task Count', 'Total Cost', 'total_time_minutes']
    # Calculate hours from minutes
    owner_df['Total Time (hrs)'] = owner_df['total_time_minutes'] / 60
    # Rename the minutes column for display
    owner_df = owner_df.rename(columns={'total_time_minutes': 'Total Time (min)'})

    # Key Metrics - Standardized layout
    total_owners = len(owner_df)
    total_tasks = owner_df['Task Count'].sum()
    total_cost = owner_df['Total Cost'].sum()
    total_time = owner_df['Total Time (hrs)'].sum()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Owners", total_owners)
    with col2:
        st.metric("Total Tasks", f"{total_tasks:,}")
    with col3:
        st.metric("Total Cost", f"${total_cost:,.2f}")
    with col4:
        st.metric("Total Time", f"{total_time:.1f} hrs")
    
    st.markdown("---")

    # Data Table
    st.markdown("**📊 Owner Analysis Table**")
    st.dataframe(owner_df, use_container_width=True)
    
    st.markdown("---")

    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Owner workload chart
        fig = px.pie(
            owner_df,
            values='Task Count',
            names='Owner',
            title='Task Distribution by Owner',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Cost by owner bar chart
        fig2 = px.bar(
            owner_df,
            x='Owner',
            y='Total Cost',
            title='Total Cost by Owner',
            color='Task Count',
            color_continuous_scale='viridis'
        )
        fig2.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True)

