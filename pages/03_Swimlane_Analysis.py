"""
Swimlane/Department Analysis page for BPMN Analysis app.
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
render_page_header("Swimlane Analysis", "🏭")

# Check if data is available
if not has_data():
    st.info("👆 Please upload BPMN XML files on the main page to start the analysis.")
else:
    # Get data from session state
    combined_tasks = get_combined_tasks()
    analysis_data = get_analysis_data()
    

    # Group by swimlane
    swimlane_analysis = {}
    for task in combined_tasks:
        swimlane = task.get('swimlane', 'Unknown')
        if swimlane not in swimlane_analysis:
            swimlane_analysis[swimlane] = {
                'task_count': 0,
                'total_cost': 0,
                'total_time_minutes': 0
            }

        swimlane_analysis[swimlane]['task_count'] += 1
        swimlane_analysis[swimlane]['total_cost'] += task.get('total_cost', 0)
        swimlane_analysis[swimlane]['total_time_minutes'] += task.get('time_minutes', 0)

    # Create swimlane analysis dataframe
    swimlane_df = pd.DataFrame(swimlane_analysis).T.reset_index()
    # Rename columns to match expected structure
    swimlane_df.columns = ['Swimlane/Department', 'Task Count', 'Total Cost', 'total_time_minutes']
    # Calculate hours from minutes
    swimlane_df['Total Time (hrs)'] = swimlane_df['total_time_minutes'] / 60
    # Rename the minutes column for display
    swimlane_df = swimlane_df.rename(columns={'total_time_minutes': 'Total Time (min)'})

    # Key Metrics - Standardized layout
    total_swimlanes = len(swimlane_df)
    total_tasks = swimlane_df['Task Count'].sum()
    total_cost = swimlane_df['Total Cost'].sum()
    total_time = swimlane_df['Total Time (hrs)'].sum()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Departments", total_swimlanes)
    with col2:
        st.metric("Total Tasks", f"{total_tasks:,}")
    with col3:
        st.metric("Total Cost", f"${total_cost:,.2f}")
    with col4:
        st.metric("Total Time", f"{total_time:.1f} hrs")
    
    st.markdown("---")

    # Data Table
    st.markdown("**📊 Department Analysis Table**")
    st.dataframe(swimlane_df, use_container_width=True)
    
    st.markdown("---")

    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Swimlane cost chart
        fig = px.bar(
            swimlane_df,
            x='Swimlane/Department',
            y='Total Cost',
            title='Total Cost by Department',
            color='Task Count',
            color_continuous_scale='viridis'
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Task distribution pie chart
        fig2 = px.pie(
            swimlane_df,
            values='Task Count',
            names='Swimlane/Department',
            title='Task Distribution by Department',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig2.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig2, use_container_width=True)

