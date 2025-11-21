"""
⚠️ Issues & Risks Analysis page for BPMN Analysis app.
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
render_page_header("Issues & Risks", "⚠️")

# Check if data is available
if not has_data():
    st.info("👆 Please upload BPMN XML files on the main page to start the analysis.")
else:
    # Get data from session state
    combined_tasks = get_combined_tasks()
    analysis_data = get_analysis_data()
    
    # Display subheader
    st.subheader("⚠️ Issues & Risks Analysis")
    

    # Group by issues
    issues_analysis = {}
    for task in combined_tasks:
        issues_text = task.get('issues_text', '')
        issues_priority = task.get('issues_priority', 'Unknown')

        if issues_text and issues_text.strip():
            if issues_text not in issues_analysis:
                issues_analysis[issues_text] = {
                    'task_count': 0,
                    'total_cost': 0,
                    'total_time_minutes': 0,
                    'priority': issues_priority,
                    'swimlanes': set(),
                    'owners': set()
                }

            issues_analysis[issues_text]['task_count'] += 1
            issues_analysis[issues_text]['total_cost'] += task.get('total_cost', 0)
            issues_analysis[issues_text]['total_time_minutes'] += task.get('time_minutes', 0)
            issues_analysis[issues_text]['swimlanes'].add(task.get('swimlane', 'Unknown'))
            issues_analysis[issues_text]['owners'].add(task.get('task_owner', 'Unknown'))

    if issues_analysis:
        # Convert sets to lists for display
        for issue in issues_analysis:
            issues_analysis[issue]['swimlanes'] = list(issues_analysis[issue]['swimlanes'])
            issues_analysis[issue]['owners'] = list(issues_analysis[issue]['owners'])

        # Create issues dataframe with smart categorization
        issues_df = pd.DataFrame(issues_analysis).T.reset_index()
        # Rename columns to match expected structure
        issues_df.columns = ['Issue', 'Task Count', 'Total Cost', 'total_time_minutes', 'Priority', 'Swimlanes', 'Owners']
        # Calculate hours from minutes
        issues_df['Total Time (hrs)'] = issues_df['total_time_minutes'] / 60
        # Rename the minutes column for display
        issues_df = issues_df.rename(columns={'total_time_minutes': 'Total Time (min)'})
        issues_df['Risk Score'] = issues_df['Total Cost'] * (issues_df['Task Count'] / 10)  # Risk scoring

        # Add smart categorization
        issues_df['Category'] = issues_df['Issue'].apply(categorize_issue)
        issues_df['Short Description'] = issues_df['Issue'].apply(lambda x: x[:60] + '...' if len(x) > 60 else x)

        # Key Metrics - Standardized layout
        total_issues = len(issues_df)
        total_tasks = issues_df['Task Count'].sum()
        total_risk = issues_df['Risk Score'].sum()
        high_priority = len(issues_df[issues_df['Priority'].str.contains('High', case=False, na=False)])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Issues", total_issues)
        with col2:
            st.metric("Affected Tasks", f"{total_tasks:,}")
        with col3:
            st.metric("Total Risk Score", f"{total_risk:,.2f}")
        with col4:
            st.metric("High Priority", high_priority, delta=f"{high_priority} urgent" if high_priority > 0 else None)
        
        st.markdown("---")

        # Display categorized issues
        st.markdown("**📊 Issues by Category**")
        category_summary = issues_df.groupby('Category').agg({
            'Task Count': 'sum',
            'Total Cost': 'sum',
            'Risk Score': 'sum'
        }).round(2)
        st.dataframe(category_summary, use_container_width=True)

        # Show full text for each category
        st.subheader("📝 Full Issue Text by Category")
        for category in category_summary.index:
            with st.expander(f"🔍 {category} ({category_summary.loc[category, 'Task Count']} issues)", expanded=False):
                category_issues = issues_df[issues_df['Category'] == category]
                for _, row in category_issues.iterrows():
                    st.write(f"**{row['Issue']}**")
                    st.write(f"*Priority: {row['Priority']} | Department: {', '.join(row['Swimlanes'])} | Owner: {', '.join(row['Owners'])} | Cost: ${row['Total Cost']:.2f}*")
                    st.divider()

        # Category distribution chart
        fig_category = px.pie(
            values=category_summary['Task Count'],
            names=category_summary.index,
            title='Issues Distribution by Category',
            color_discrete_sequence=px.colors.qualitative.Set1
        )
        fig_category.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_category, use_container_width=True)

        # Issues by priority (using categories for better readability)
        priority_colors = {'High Priority': 'red', 'Medium Priority': 'orange', 'Low Priority': 'yellow'}
        fig = px.bar(
            issues_df.groupby(['Category', 'Priority'])['Risk Score'].sum().reset_index(),
            x='Category',
            y='Risk Score',
            title='Risk Score by Issue Category and Priority',
            color='Priority',
            color_discrete_map=priority_colors
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        # Priority distribution
        priority_counts = issues_df['Priority'].value_counts()
        fig2 = px.pie(
            values=priority_counts.values,
            names=priority_counts.index,
            title='Issues by Priority Level',
            color_discrete_sequence=['red', 'orange', 'yellow']
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Detailed issues table (expandable)
        with st.expander("📋 Detailed Issues Table", expanded=False):
            st.dataframe(issues_df[['Short Description', 'Category', 'Priority', 'Task Count', 'Total Cost', 'Total Time (hrs)', 'Risk Score', 'Swimlanes']], use_container_width=True)

        # Issues by department (simplified)
        st.subheader("🏭 Issues by Department")
        dept_issue_data = []
        for issue, data in issues_analysis.items():
            for swimlane in data['swimlanes']:
                dept_issue_data.append({
                    'Department': swimlane,
                    'Category': categorize_issue(issue),
                    'Priority': data['priority'],
                    'Task Count': data['task_count'],
                    'Total Cost': data['total_cost']
                })

        if dept_issue_data:
            dept_issue_df = pd.DataFrame(dept_issue_data)
            dept_pivot = dept_issue_df.pivot_table(
                index='Department', 
                columns='Category', 
                values='Task Count', 
                aggfunc='sum'
            ).fillna(0)

            fig3 = go.Figure(data=go.Heatmap(
                z=dept_pivot.values,
                x=dept_pivot.columns,
                y=dept_pivot.index,
                colorscale='reds',
                text=dept_pivot.values,
                texttemplate="%{text}",
                textfont={"size": 10},
                hoverongaps=False
            ))
            fig3.update_layout(
                title='Issues by Department and Category',
                xaxis_title='Issue Category',
                yaxis_title='Department'
            )
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No issues captured in the uploaded BPMN files.")

