"""
Tasks Overview page for BPMN Analysis app.
This page is automatically generated from the main application tabs.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from bpmn_analyzer import categorize_opportunity, categorize_issue
from utils.shared import setup_file_upload, get_combined_tasks, get_analysis_data, has_data, render_page_header, render_sidebar_header
from bpmn_analyzer import BPMNAnalyzer
from datetime import datetime
import json
import zipfile
import io

# Render sidebar header
render_sidebar_header()

# Set up file upload in sidebar (visible on all pages)
setup_file_upload()

# Render page header
render_page_header("Tasks Overview", "📋")

# Check if data is available
if not has_data():
    st.info("👆 Please upload BPMN XML files on the main page to start the analysis.")
else:
    # Get data from session state
    combined_tasks = get_combined_tasks()
    analysis_data = get_analysis_data()
    

    # Create tasks dataframe - handle empty case
    if not combined_tasks:
        st.warning("⚠️ No tasks found in uploaded files.")
        st.stop()
    
    tasks_df = pd.DataFrame(combined_tasks)

    # Filter options - handle empty dataframe gracefully
    col1, col2, col3 = st.columns(3)

    with col1:
        swimlane_options = ["All"] + (list(tasks_df['swimlane'].unique()) if 'swimlane' in tasks_df.columns and len(tasks_df) > 0 else [])
        swimlane_filter = st.selectbox(
            "Filter by Swimlane/Department",
            swimlane_options
        )

    with col2:
        owner_options = ["All"] + (list(tasks_df['task_owner'].unique()) if 'task_owner' in tasks_df.columns and len(tasks_df) > 0 else [])
        owner_filter = st.selectbox(
            "Filter by Owner",
            owner_options
        )

    with col3:
        status_options = ["All"] + (list(tasks_df['task_status'].unique()) if 'task_status' in tasks_df.columns and len(tasks_df) > 0 else [])
        status_filter = st.selectbox(
            "Filter by Status",
            status_options
        )

    # Apply filters
    filtered_df = tasks_df.copy()

    if swimlane_filter != "All":
        filtered_df = filtered_df[filtered_df['swimlane'] == swimlane_filter]

    if owner_filter != "All":
        filtered_df = filtered_df[filtered_df['task_owner'] == owner_filter]

    if status_filter != "All":
        filtered_df = filtered_df[filtered_df['task_status'] == status_filter]

    # Create a copy of filtered_df for display formatting
    display_df = filtered_df.copy()

    # Format doc_url for better display - show clickable links
    def format_doc_url(url):
        # Treat NR, NO URL, No URL as empty
        url_str = str(url).strip() if not pd.isna(url) else ''
        if pd.isna(url) or url_str == '' or url_str.lower() in ['unknown', 'nr', 'no url', 'nourl']:
            return ''  # Return empty string instead of 'No URL' for cleaner display
        # Truncate long URLs for display
        if len(url_str) > 50:
            return f"{url_str[:47]}..."
        return url_str

    # Format doc_status for better display with emojis
    def format_doc_status(status):
        if pd.isna(status) or status == '' or status == 'Unknown':
            return '❓ Unknown'
        status_lower = str(status).lower()
        if 'complete' in status_lower or 'done' in status_lower or 'finished' in status_lower:
            return '✅ Complete'
        elif 'in progress' in status_lower or 'progress' in status_lower:
            return '🔄 In Progress'
        elif 'pending' in status_lower or 'waiting' in status_lower:
            return '⏳ Pending'
        elif 'not started' in status_lower or 'not started' in status_lower:
            return '🚫 Not Started'
        elif 'draft' in status_lower:
            return '📝 Draft'
        else:
            return f'📄 {status}'

    # Apply formatting to columns
    display_df['doc_url_display'] = display_df['doc_url'].apply(format_doc_url)
    display_df['doc_status_display'] = display_df['doc_status'].apply(format_doc_status)

    # 📚 Documentation Summary - FIRST CARD (moved to top)
    if not filtered_df.empty:
        st.markdown("---")
        st.markdown("**📚 Documentation Summary**")
        
        # Normalize doc_status values BEFORE counting to avoid duplicate "Unknown"
        def normalize_status(status):
            """Normalize status values - convert empty/None/Unknown to 'Unknown'."""
            if pd.isna(status) or status == '' or str(status).strip() == '':
                return 'Unknown'
            status_str = str(status).strip()
            if status_str.lower() == 'unknown':
                return 'Unknown'
            return status_str
        
        # Create normalized status column for accurate counting
        display_df['doc_status_normalized'] = display_df['doc_status'].apply(normalize_status)
        
        # Count documentation statuses on normalized data
        doc_status_counts = display_df['doc_status_normalized'].value_counts()
        total_tasks = len(filtered_df)
        total_tasks_with_docs = len(display_df[display_df['doc_status_normalized'] != 'Unknown'])
        # Count tasks with valid URLs (excluding NR, NO URL, No URL, Unknown, empty)
        def is_valid_url(url):
            if pd.isna(url):
                return False
            url_str = str(url).strip().lower()
            return url_str not in ['', 'unknown', 'nr', 'no url', 'nourl']
        total_tasks_with_urls = display_df['doc_url'].apply(is_valid_url).sum()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tasks with Documentation", f"{total_tasks_with_docs}/{total_tasks}")
        with col2:
            st.metric("Tasks with URLs", f"{total_tasks_with_urls}/{total_tasks}")
        with col3:
            completion_rate = (total_tasks_with_docs / total_tasks * 100) if total_tasks > 0 else 0
            st.metric("Documentation Coverage", f"{completion_rate:.1f}%")

        # Show documentation status breakdown (now with normalized values, no duplicates)
        if not doc_status_counts.empty:
            st.markdown("**Documentation Status Breakdown:**")
            for status, count in doc_status_counts.items():
                # Status is already normalized, just ensure it's a string
                status_display = str(status).strip() if not pd.isna(status) else 'Unknown'
                percentage = (count / total_tasks * 100) if total_tasks > 0 else 0
                st.markdown(f"- **{status_display}**: {count} tasks ({percentage:.1f}%)")
        
        st.markdown("---")

    # Prepare table with all requested columns (mapping to internal field names)
    # Create a copy for table display with renamed columns
    table_df = display_df.copy()
    
    # Map internal field names to requested column names
    column_mapping = {
        'id': 'taskId',
        'name': 'taskName',
        'task_owner': 'taskOwner',
        'task_industry': 'taskIndustry',
        'doc_url': 'docUrl',
        'tools_used': 'toolsUsed',
        'currency': 'currency',
        'time_hhmm': 'timeHhmm',
        'cost_per_hour': 'costPerHour',
        'other_costs': 'otherCosts',
        'process_ref': 'processRef',
        'doc_status': 'docStatus',
        'task_status': 'taskStatus'
    }
    
    # Select and rename columns for display
    display_columns = []
    for internal_col, display_col in column_mapping.items():
        if internal_col in table_df.columns:
            display_columns.append(internal_col)
    
    # Create display dataframe with renamed columns
    table_display_df = table_df[display_columns].copy()
    table_display_df = table_display_df.rename(columns=column_mapping)
    
    # Display filtered data with all requested columns
    st.dataframe(
        table_display_df,
        use_container_width=True,
        column_config={
            "taskId": st.column_config.TextColumn(
                "Task ID",
                help="Unique identifier for the task",
                max_chars=30
            ),
            "taskName": st.column_config.TextColumn(
                "Task Name",
                help="Name of the task",
                max_chars=50
            ),
            "taskOwner": st.column_config.TextColumn(
                "Task Owner",
                help="Owner responsible for this task",
                max_chars=30
            ),
            "taskIndustry": st.column_config.TextColumn(
                "Task Industry",
                help="Industry classification for this task",
                max_chars=30
            ),
            "docUrl": st.column_config.LinkColumn(
                "Documentation URL",
                help="Click to open documentation link",
                max_chars=50
            ),
            "toolsUsed": st.column_config.TextColumn(
                "Tools Used",
                help="Tools utilized for this task",
                max_chars=50
            ),
            "currency": st.column_config.TextColumn(
                "Currency",
                help="Currency used for cost calculations",
                max_chars=10
            ),
            "timeHhmm": st.column_config.TextColumn(
                "Time (HH:MM)",
                help="Time required in HH:MM format",
                max_chars=10
            ),
            "costPerHour": st.column_config.NumberColumn(
                "Cost Per Hour",
                help="Cost per hour for this task",
                format="%.2f"
            ),
            "otherCosts": st.column_config.NumberColumn(
                "Other Costs",
                help="Additional costs beyond labor",
                format="%.2f"
            ),
            "processRef": st.column_config.TextColumn(
                "Process Reference",
                help="Reference to the process this task belongs to",
                max_chars=30
            ),
            "docStatus": st.column_config.TextColumn(
                "Documentation Status",
                help="Current status of task documentation",
                max_chars=30
            ),
            "taskStatus": st.column_config.TextColumn(
                "Task Status",
                help="Current status of the task",
                max_chars=30
            )
        }
    )

    # Add summary totals row
    if not filtered_df.empty:
        total_tasks = len(filtered_df)
        total_time_hours = filtered_df['time_hours'].sum()
        total_cost = filtered_df['total_cost'].sum()

        # Format time display for summary
        total_hours_int = int(total_time_hours)
        total_minutes = int((total_time_hours - total_hours_int) * 60)
        time_display = f"{total_hours_int:02d}:{total_minutes:02d}"

        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Tasks", total_tasks)
        with col2:
            st.metric("Total Time", f"{time_display} ({total_time_hours:.2f} hrs)")
        with col3:
            st.metric("Total Cost", f"${total_cost:,.2f}")
        with col4:
            st.metric("Avg Cost/Task", f"${total_cost/total_tasks:,.2f}" if total_tasks > 0 else "$0.00")

        # Validation message - compare with grand total from combined_tasks
        grand_total_time = sum(task.get('time_hours', 0) for task in combined_tasks)
        if abs(total_time_hours - grand_total_time) < 0.01:
            success_icon = "✅"
            st.success("✅ Table totals match grand total")
        else:
            warning_icon = "⚠️"
            st.warning(f"⚠️ Table total ({total_time_hours:.2f} hrs) differs from grand total ({grand_total_time:.2f} hrs)")

    # 📚 Documentation Links - LAST SECTION (moved to end)
    if not filtered_df.empty:
        st.markdown("---")
        st.markdown("**📚 Documentation Links:**")
        has_links = False
        for idx, row in display_df.iterrows():
            doc_url = str(row['doc_url']).strip() if pd.notna(row['doc_url']) else ''
            # Treat NR, NO URL, No URL as empty
            if doc_url and doc_url.lower() not in ['unknown', 'nr', 'no url', 'nourl', '']:
                st.markdown(f"- **{row['name']}**: [Open Documentation]({doc_url})")
                has_links = True
        if not has_links:
            st.info("No documentation links available for the filtered tasks.")

