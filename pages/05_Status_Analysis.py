"""
📊 Status Analysis page for BPMN Analysis app.
This page is automatically generated from the main application tabs.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from bpmn_analyzer import categorize_opportunity, categorize_issue
from utils.shared import setup_file_upload, get_combined_tasks, get_analysis_data, has_data, render_page_header, render_sidebar_header
import numpy as np

# Render sidebar header
render_sidebar_header()

# Set up file upload in sidebar (visible on all pages)
setup_file_upload()

# Render page header
render_page_header("Status Analysis", "📊")

# Check if data is available
if not has_data():
    st.info("👆 Please upload BPMN XML files on the main page to start the analysis.")
else:
    # Get data from session state
    combined_tasks = get_combined_tasks()
    analysis_data = get_analysis_data()
    
    # Normalize task_status values - convert empty/None/0/Unknown to 'Unknown'
    def normalize_task_status(status):
        """Normalize task status values - convert empty/None/0/Unknown to 'Unknown'."""
        if status is None or pd.isna(status):
            return 'Unknown'
        status_str = str(status).strip()
        # Handle empty strings, '0', 'unknown', etc.
        if status_str == '' or status_str == '0' or status_str.lower() == 'unknown':
            return 'Unknown'
        return status_str
    
    # Group by status
    status_analysis = {}
    for task in combined_tasks:
        raw_status = task.get('task_status', 'Unknown')
        status = normalize_task_status(raw_status)  # Normalize empty/0/None to 'Unknown'
        if status not in status_analysis:
            status_analysis[status] = {
                'task_count': 0,
                'total_cost': 0
            }

        status_analysis[status]['task_count'] += 1
        status_analysis[status]['total_cost'] += task.get('total_cost', 0)

    status_df = pd.DataFrame(status_analysis).T.reset_index()
    status_df.columns = ['Status', 'Task Count', 'Total Cost']

    # Key Metrics - Standardized layout
    total_statuses = len(status_df)
    total_tasks = status_df['Task Count'].sum()
    total_cost = status_df['Total Cost'].sum()
    avg_cost_per_status = total_cost / total_statuses if total_statuses > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Status Types", total_statuses)
    with col2:
        st.metric("Total Tasks", f"{total_tasks:,}")
    with col3:
        st.metric("Total Cost", f"${total_cost:,.2f}")
    with col4:
        st.metric("Avg Cost/Status", f"${avg_cost_per_status:,.2f}")
    
    st.markdown("---")

    # Display status summary
    st.markdown("**📊 Task Status Summary**")
    st.dataframe(status_df, use_container_width=True)
    
    st.markdown("---")

    # Create two columns for charts
    col1, col2 = st.columns(2)

    with col1:
        # Bar chart for task status
        fig = px.bar(
            status_df,
            x='Status',
            y='Task Count',
            title='Tasks by Status',
            color='Task Count',
            color_continuous_scale='viridis'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Pie chart for task status
        fig = px.pie(
            status_df,
            values='Task Count',
            names='Status',
            title='Task Status Distribution',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)

    # Tasks requiring attention table
    st.markdown("---")
    st.write("**⚠️ Tasks Requiring Attention**")

    # Filter tasks that require attention (using normalized status)
    attention_tasks = []
    for task in combined_tasks:
        raw_status = task.get('task_status', 'Unknown')
        normalized_status = normalize_task_status(raw_status)
        # Check if status indicates attention needed (normalize to lowercase for comparison)
        if normalized_status and normalized_status.lower() in ['requires attention', 'pending', 'blocked', 'issue']:
            attention_tasks.append(task)

    if attention_tasks:
        attention_df = pd.DataFrame(attention_tasks)
        # Select relevant columns for display
        display_columns = ['name', 'swimlane', 'task_owner', 'time_display', 'total_cost', 'currency', 'task_status']
        available_columns = [col for col in display_columns if col in attention_df.columns]

        st.dataframe(
            attention_df[available_columns],
            use_container_width=True,
            column_config={
                "task_status": st.column_config.TextColumn(
                    "Status",
                    help="Current status of the task",
                    max_chars=20
                )
            }
        )

        # Summary of attention tasks
        total_attention_cost = sum(task.get('total_cost', 0) for task in attention_tasks)
        total_attention_time = sum(task.get('time_hours', 0) for task in attention_tasks)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tasks Requiring Attention", len(attention_tasks))
        with col2:
            st.metric("Total Cost at Risk", f"${total_attention_cost:,.2f}")
        with col3:
            st.metric("Total Time at Risk", f"{total_attention_time:.1f} hrs")
    else:
        st.success("🎉 All tasks are in good status! No tasks require attention.")

