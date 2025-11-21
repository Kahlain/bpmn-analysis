"""
💡 Opportunities Analysis page for BPMN Analysis app.
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
render_page_header("Opportunities", "💡")

# Check if data is available
if not has_data():
    st.info("👆 Please upload BPMN XML files on the main page to start the analysis.")
else:
    # Get data from session state
    combined_tasks = get_combined_tasks()
    analysis_data = get_analysis_data()
    
    # Display subheader
    st.subheader("💡 Opportunities Analysis")
    

    # Group by opportunities
    opportunities_analysis = {}
    for task in combined_tasks:
        opportunities = task.get('opportunities', '')
        if opportunities and opportunities.strip():
            if opportunities not in opportunities_analysis:
                opportunities_analysis[opportunities] = {
                    'task_count': 0,
                    'total_cost': 0,
                    'total_time_minutes': 0,
                    'swimlanes': set(),
                    'owners': set(),
                    'tools': set()
                }

            opportunities_analysis[opportunities]['task_count'] += 1
            opportunities_analysis[opportunities]['total_cost'] += task.get('total_cost', 0)
            opportunities_analysis[opportunities]['total_time_minutes'] += task.get('time_minutes', 0)
            opportunities_analysis[opportunities]['swimlanes'].add(task.get('swimlane', 'Unknown'))
            opportunities_analysis[opportunities]['owners'].add(task.get('task_owner', 'Unknown'))
            if task.get('tools_used'):
                opportunities_analysis[opportunities]['tools'].add(task.get('tools_used'))

    if opportunities_analysis:
        # Convert sets to lists for display
        for opp in opportunities_analysis:
            opportunities_analysis[opp]['swimlanes'] = list(opportunities_analysis[opp]['swimlanes'])
            opportunities_analysis[opp]['owners'] = list(opportunities_analysis[opp]['owners'])
            opportunities_analysis[opp]['tools'] = list(opportunities_analysis[opp]['tools'])

        # Create opportunities dataframe with smart categorization
        opp_df = pd.DataFrame(opportunities_analysis).T.reset_index()
        # Rename columns to match expected structure
        opp_df.columns = ['Opportunity', 'Task Count', 'Total Cost', 'total_time_minutes', 'Swimlanes', 'Owners', 'Tools']
        # Calculate hours from minutes
        opp_df['Total Time (hrs)'] = opp_df['total_time_minutes'] / 60
        # Rename the minutes column for display
        opp_df = opp_df.rename(columns={'total_time_minutes': 'Total Time (min)'})
        opp_df['Potential Impact'] = opp_df['Total Cost'] + (opp_df['Total Time (hrs)'] * 50)  # Estimate impact

        # Add smart categorization
        opp_df['Category'] = opp_df['Opportunity'].apply(categorize_opportunity)
        opp_df['Short Description'] = opp_df['Opportunity'].apply(lambda x: x[:60] + '...' if len(x) > 60 else x)

        # Key Metrics - Standardized layout
        total_opportunities = len(opp_df)
        total_tasks = opp_df['Task Count'].sum()
        total_potential = opp_df['Potential Impact'].sum()
        avg_impact = opp_df['Potential Impact'].mean() if len(opp_df) > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Opportunities", total_opportunities)
        with col2:
            st.metric("Affected Tasks", f"{total_tasks:,}")
        with col3:
            st.metric("Total Potential Impact", f"${total_potential:,.2f}")
        with col4:
            st.metric("Avg Impact/Opportunity", f"${avg_impact:,.2f}")
        
        st.markdown("---")

        # Display categorized opportunities
        st.markdown("**📊 Opportunities by Category**")
        category_summary = opp_df.groupby('Category').agg({
            'Task Count': 'sum',
            'Total Cost': 'sum',
            'Potential Impact': 'sum'
        }).round(2)
        st.dataframe(category_summary, use_container_width=True)

        # Show full text for each category
        st.subheader("📝 Full Opportunity Text by Category")
        for category in category_summary.index:
            with st.expander(f"🔍 {category} ({category_summary.loc[category, 'Task Count']} opportunities)", expanded=False):
                category_opps = opp_df[opp_df['Category'] == category]
                for _, row in category_opps.iterrows():
                    st.write(f"**{row['Opportunity']}**")
                    st.write(f"*Department: {', '.join(row['Swimlanes'])} | Owner: {', '.join(row['Owners'])} | Cost: ${row['Total Cost']:.2f}*")
                    st.divider()

        # Category distribution chart
        fig_category = px.pie(
            values=category_summary['Task Count'],
            names=category_summary.index,
            title='Opportunities Distribution by Category',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_category.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_category, use_container_width=True)

        # Opportunities by impact (using categories for better readability)
        fig = px.bar(
            opp_df.groupby('Category')['Potential Impact'].sum().reset_index(),
            x='Category',
            y='Potential Impact',
            title='Potential Impact by Opportunity Category',
            color='Potential Impact',
            color_continuous_scale='greens'
        )
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        # Detailed opportunities table (expandable)
        with st.expander("📋 Detailed Opportunities Table", expanded=False):
            st.dataframe(opp_df[['Short Description', 'Category', 'Task Count', 'Total Cost', 'Total Time (hrs)', 'Potential Impact', 'Swimlanes']], use_container_width=True)

        # Opportunities by department (simplified)
        st.subheader("🏭 Opportunities by Department")
        dept_opp_data = []
        for opp, data in opportunities_analysis.items():
            for swimlane in data['swimlanes']:
                dept_opp_data.append({
                    'Department': swimlane,
                    'Category': categorize_opportunity(opp),
                    'Task Count': data['task_count'],
                    'Total Cost': data['total_cost']
                })

        if dept_opp_data:
            dept_opp_df = pd.DataFrame(dept_opp_data)
            dept_pivot = dept_opp_df.pivot_table(
                index='Department', 
                columns='Category', 
                values='Task Count', 
                aggfunc='sum'
            ).fillna(0)

            fig2 = go.Figure(data=go.Heatmap(
                z=dept_pivot.values,
                x=dept_pivot.columns,
                y=dept_pivot.index,
                colorscale='greens',
                text=dept_pivot.values,
                texttemplate="%{text}",
                textfont={"size": 10},
                hoverongaps=False
            ))
            fig2.update_layout(
                title='Opportunities by Department and Category',
                xaxis_title='Opportunity Category',
                yaxis_title='Department'
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No opportunities captured in the uploaded BPMN files.")

