"""
Executive Summary page for BPMN Analysis app.
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

# Render page header - Streamlit-native
render_page_header("Executive Summary", "📊")

# Check if data is available
if not has_data():
    st.info("👆 Please upload BPMN XML files on the main page to start the analysis.")
else:
    # Get data from session state
    combined_tasks = get_combined_tasks()
    analysis_data = get_analysis_data()
    

    # High-level KPIs
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Tasks", 
            f"{len(combined_tasks):,}",
            help="Total number of tasks across all processes"
        )

    with col2:
        total_cost = sum(task.get('total_cost', 0) for task in combined_tasks)
        # Get currencies, filtering out empty/None/Unknown values
        currencies = set()
        for task in combined_tasks:
            currency = task.get('currency')
            if currency and isinstance(currency, str) and currency.strip() and currency != 'Unknown':
                currencies.add(currency)
        currency_display = list(currencies)[0] if currencies else None
        if currency_display:
            cost_display = f"{currency_display} {total_cost:,.2f}"
        else:
            cost_display = f"{total_cost:,.2f}"
        st.metric(
            "Total Cost", 
            cost_display,
            help="Total cost across all tasks"
        )

    with col3:
        total_time_hours = sum(task.get('time_minutes', 0) for task in combined_tasks) / 60
        st.metric(
            "Total Time", 
            f"{total_time_hours:.1f} hrs",
            help="Total estimated time across all tasks"
        )

    with col4:
        unique_swimlanes = len(set(task.get('swimlane', 'Unknown') for task in combined_tasks))
        st.metric(
            "Departments", 
            f"{unique_swimlanes}",
            help="Number of departments/swimlanes involved"
        )

    # Documentation Status and Task Health tables (side-by-side below Total Tasks)
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        # Documentation Status Table
        st.markdown("**📚 Documentation** 🔗")
        
        # Normalize doc_status values to avoid duplicates
        def normalize_status(status):
            if pd.isna(status) or status == '' or str(status).strip() == '':
                return 'Unknown'
            status_str = str(status).strip()
            if status_str.lower() == 'unknown':
                return 'Unknown'
            return status_str
        
        # Count documentation statuses
        doc_status_counts = {}
        for task in combined_tasks:
            doc_status = normalize_status(task.get('doc_status', 'Unknown'))
            doc_status_counts[doc_status] = doc_status_counts.get(doc_status, 0) + 1
        
        # Create dataframe for display
        doc_status_data = []
        # Ensure we have all expected statuses
        expected_statuses = ['Documented', 'Documentation Not Needed', 'In Process to be Documented', 'Not Documented', 'Unknown']
        for status in expected_statuses:
            count = doc_status_counts.get(status, 0)
            doc_status_data.append({'Status': status, 'Count': count})
        
        # Sort by predefined order (then by count descending)
        status_order = {status: i for i, status in enumerate(expected_statuses)}
        doc_status_data.sort(key=lambda x: (status_order.get(x['Status'], 999), -x['Count']))
        
        doc_status_df = pd.DataFrame(doc_status_data)
        st.dataframe(doc_status_df, use_container_width=True, hide_index=True)
    
    with col2:
        # Task Health Table (now shows actual task_status breakdown to match Status Analysis)
        st.markdown("**✅ Task Health**")
        
        # Normalize task_status values - convert empty/None/0/Unknown to 'Unknown' (same as Status Analysis)
        def normalize_task_status(status):
            """Normalize task status values - convert empty/None/0/Unknown to 'Unknown'."""
            if status is None or pd.isna(status):
                return 'Unknown'
            status_str = str(status).strip()
            # Handle empty strings, '0', 'unknown', etc.
            if status_str == '' or status_str == '0' or status_str.lower() == 'unknown':
                return 'Unknown'
            return status_str
        
        # Count tasks by normalized task_status (matching Status Analysis logic)
        task_status_counts = {}
        for task in combined_tasks:
            raw_status = task.get('task_status', 'Unknown')
            normalized_status = normalize_task_status(raw_status)
            task_status_counts[normalized_status] = task_status_counts.get(normalized_status, 0) + 1
        
        # Create dataframe for display (matching Status Analysis format)
        task_health_data = []
        for status, count in sorted(task_status_counts.items()):
            task_health_data.append({'Status': status, 'Count': count})
        
        # Sort by count descending (most common first)
        task_health_data.sort(key=lambda x: x['Count'], reverse=True)
        
        task_health_df = pd.DataFrame(task_health_data)
        st.dataframe(task_health_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")

    # Summary charts row 1
    col1, col2 = st.columns(2)

    with col1:
        # Cost distribution by department
        swimlane_costs = {}
        for task in combined_tasks:
            swimlane = task.get('swimlane', 'Unknown')
            if swimlane not in swimlane_costs:
                swimlane_costs[swimlane] = 0
            swimlane_costs[swimlane] += task.get('total_cost', 0)

        if swimlane_costs:
            fig = px.pie(
                values=list(swimlane_costs.values()),
                names=list(swimlane_costs.keys()),
                title="Cost Distribution by Department",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Time distribution by department
        swimlane_times = {}
        for task in combined_tasks:
            swimlane = task.get('swimlane', 'Unknown')
            if swimlane not in swimlane_times:
                swimlane_times[swimlane] = 0
            swimlane_times[swimlane] += task.get('time_minutes', 0)

        if swimlane_times:
            # Convert to hours for better readability
            swimlane_hours = {k: v/60 for k, v in swimlane_times.items()}
            fig = px.bar(
                x=list(swimlane_hours.keys()),
                y=list(swimlane_hours.values()),
                title="Time Distribution by Department (Hours)",
                color=list(swimlane_hours.values()),
                color_continuous_scale='viridis'
            )
            fig.update_layout(xaxis_title="Department", yaxis_title="Hours")
            st.plotly_chart(fig, use_container_width=True)

    # Summary charts row 2
    col1, col2 = st.columns(2)

    with col1:
        # Task status overview
        status_counts = {}
        for task in combined_tasks:
            status = task.get('task_status', 'Unknown')
            if status not in status_counts:
                status_counts[status] = 0
            status_counts[status] += 1

        if status_counts:
            fig = px.pie(
                values=list(status_counts.values()),
                names=list(status_counts.keys()),
                title="Task Status Overview",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Documentation status overview
        doc_status_counts = {}
        for task in combined_tasks:
            doc_status = task.get('doc_status', 'Unknown')
            if doc_status not in doc_status_counts:
                doc_status_counts[doc_status] = 0
            doc_status_counts[doc_status] += 1

        if doc_status_counts:
            fig = px.pie(
                values=list(doc_status_counts.values()),
                names=list(doc_status_counts.keys()),
                title="Documentation Status Overview",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)

    # Summary charts row 3 - Currency and Industry Analysis
    col1, col2 = st.columns(2)

    with col1:
        # Currency analysis
        currency_analysis = {}
        for task in combined_tasks:
            currency = task.get('currency', 'Unknown')
            if currency not in currency_analysis:
                currency_analysis[currency] = {
                    'task_count': 0,
                    'total_cost': 0,
                    'total_time_minutes': 0
                }

            currency_analysis[currency]['task_count'] += 1
            currency_analysis[currency]['total_cost'] += task.get('total_cost', 0)
            currency_analysis[currency]['total_time_minutes'] += task.get('time_minutes', 0)

        if currency_analysis:
            currency_df = pd.DataFrame(currency_analysis).T.reset_index()
            # Rename columns to match expected structure
            currency_df.columns = ['Currency', 'Task Count', 'Total Cost', 'total_time_minutes']
            # Calculate hours from minutes
            currency_df['Total Time (hrs)'] = currency_df['total_time_minutes'] / 60
            # Rename the minutes column for display
            currency_df = currency_df.rename(columns={'total_time_minutes': 'Total Time (min)'})

            fig = px.bar(
                currency_df,
                x='Currency',
                y='Total Cost',
                title='Cost Distribution by Currency',
                color='Task Count',
                color_continuous_scale='oranges'
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Industry analysis
        industry_analysis = {}
        for task in combined_tasks:
            industry = task.get('task_industry', 'Unknown')
            if industry not in industry_analysis:
                industry_analysis[industry] = {
                    'task_count': 0,
                    'total_cost': 0,
                    'total_time_minutes': 0
                }

            industry_analysis[industry]['task_count'] += 1
            industry_analysis[industry]['total_cost'] += task.get('total_cost', 0)
            industry_analysis[industry]['total_time_minutes'] += task.get('time_minutes', 0)

        if industry_analysis:
            industry_df = pd.DataFrame(industry_analysis).T.reset_index()
            # Rename columns to match expected structure
            industry_df.columns = ['Industry', 'Task Count', 'Total Cost', 'total_time_minutes']
            # Calculate hours from minutes
            industry_df['Total Time (hrs)'] = industry_df['total_time_minutes'] / 60
            # Rename the minutes column for display
            industry_df = industry_df.rename(columns={'total_time_minutes': 'Total Time (min)'})

            fig = px.bar(
                industry_df,
                x='Industry',
                y='Task Count',
                title='Task Distribution by Industry',
                color='Total Cost',
                color_continuous_scale='plasma'
            )
            st.plotly_chart(fig, use_container_width=True)

    # Key insights and recommendations
    st.subheader("🔍 Key Insights & Recommendations")

    # Calculate insights
    total_tasks = len(combined_tasks)
    tasks_with_issues = sum(1 for task in combined_tasks if not task.get('doc_status') or not task.get('task_status') or not task.get('time_hhmm'))
    completion_rate = ((total_tasks - tasks_with_issues) / total_tasks * 100) if total_tasks > 0 else 0

    # Top cost centers
    swimlane_costs_sorted = sorted(swimlane_costs.items(), key=lambda x: x[1], reverse=True)
    top_cost_center = swimlane_costs_sorted[0] if swimlane_costs_sorted else ('Unknown', 0)

    # Top time consumers
    swimlane_times_sorted = sorted(swimlane_times.items(), key=lambda x: x[1], reverse=True)
    top_time_consumer = swimlane_times_sorted[0] if swimlane_times_sorted else ('Unknown', 0)

    # Display insights
    col1, col2 = st.columns(2)

    with col1:
        st.info(f"**Data Quality Score: {completion_rate:.1f}%**")
        if completion_rate < 80:
            st.warning("⚠️ Consider improving data completeness for better analysis")
        else:
            st.success("✅ Good data quality for analysis")

        st.info(f"**Top Cost Center: {top_cost_center[0]}**")
        if currency_display:
            st.write(f"*{currency_display} {top_cost_center[1]:,.2f}*")
        else:
            st.write(f"*{top_cost_center[1]:,.2f}*")

        if top_cost_center[1] > total_cost * 0.3:
            st.warning("⚠️ This department represents over 30% of total costs")

    with col2:
        st.info(f"**Top Time Consumer: {top_time_consumer[0]}**")
        st.write(f"*{top_time_consumer[1]/60:.1f} hours*")

        if top_time_consumer[1] > sum(swimlane_times.values()) * 0.3:
            st.warning("⚠️ This department represents over 30% of total time")

        # Resource efficiency
        avg_cost_per_hour = total_cost / (total_time_hours) if total_time_hours > 0 else 0
        avg_cost_display = f"{currency_display} {avg_cost_per_hour:.2f}" if currency_display else f"{avg_cost_per_hour:.2f}"
        st.info(f"**Average Cost per Hour: {avg_cost_display}**")

