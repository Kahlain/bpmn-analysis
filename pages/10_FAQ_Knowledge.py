"""
❓ FAQ Knowledge Analysis page for BPMN Analysis app.
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
render_page_header("FAQ Knowledge", "❓")

# Check if data is available
if not has_data():
    st.info("👆 Please upload BPMN XML files on the main page to start the analysis.")
else:
    # Get data from session state
    combined_tasks = get_combined_tasks()
    analysis_data = get_analysis_data()
    
    # Collect all FAQs
    faq_data = []
    for task in combined_tasks:
        task_name = task.get('name', 'Unknown')
        swimlane = task.get('swimlane', 'Unknown')
        owner = task.get('task_owner', 'Unknown')

        # Check each FAQ field
        for i in range(1, 4):
            question = task.get(f'faq_q{i}', '')
            answer = task.get(f'faq_a{i}', '')

            if question and answer and question.strip() and answer.strip():
                faq_data.append({
                    'Task': task_name,
                    'Department': swimlane,
                    'Owner': owner,
                    'Question': question,
                    'Answer': answer,
                    'FAQ #': i
                })

    if faq_data:
        # Key Metrics - Standardized layout
        total_faqs = len(faq_data)
        unique_tasks = len(set(faq['Task'] for faq in faq_data))
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total FAQs", total_faqs)
        with col2:
            st.metric("Tasks with FAQs", unique_tasks)
        with col3:
            st.metric("Tasks Total", len(combined_tasks))
        with col4:
            coverage = (unique_tasks / len(combined_tasks) * 100) if len(combined_tasks) > 0 else 0
            st.metric("FAQ Coverage", f"{coverage:.1f}%")
        
        st.markdown("---")
        
        faq_df = pd.DataFrame(faq_data)

        # Show full FAQ text organized by department
        st.subheader("📚 Full FAQ Content by Department")
        for dept in faq_df['Department'].unique():
            dept_faqs = faq_df[faq_df['Department'] == dept]
            with st.expander(f"🏭 {dept} ({len(dept_faqs)} FAQs)", expanded=False):
                for _, faq in dept_faqs.iterrows():
                    st.write(f"**Q{faq['FAQ #']}: {faq['Question']}**")
                    st.write(f"**A:** {faq['Answer']}")
                    st.write(f"*Task: {faq['Task']} | Owner: {faq['Owner']}*")
                    st.divider()

        # Summary table
        st.subheader("📊 FAQ Summary Table")
        st.dataframe(faq_df, use_container_width=True)

        # FAQ distribution by department
        dept_faq_counts = faq_df['Department'].value_counts()
        fig = px.bar(
            x=dept_faq_counts.index,
            y=dept_faq_counts.values,
            title='FAQ Distribution by Department',
            color=dept_faq_counts.values,
            color_continuous_scale='blues'
        )
        st.plotly_chart(fig, use_container_width=True)

        # FAQ by owner
        owner_faq_counts = faq_df['Owner'].value_counts()
        fig2 = px.pie(
            values=owner_faq_counts.values,
            names=owner_faq_counts.index,
            title='FAQ Distribution by Owner'
        )
        fig2.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig2, use_container_width=True)

        # Search FAQs
        st.subheader("🔍 Search FAQs")
        search_term = st.text_input("Search for specific topics in FAQs:", placeholder="e.g., notification, approval, process")

        if search_term:
            filtered_faqs = faq_df[
                faq_df['Question'].str.contains(search_term, case=False, na=False) |
                faq_df['Answer'].str.contains(search_term, case=False, na=False)
            ]
            if not filtered_faqs.empty:
                st.write(f"Found {len(filtered_faqs)} FAQs containing '{search_term}':")
                st.dataframe(filtered_faqs, use_container_width=True)
            else:
                st.info(f"No FAQs found containing '{search_term}'")
    else:
        st.info("No FAQs captured in the uploaded BPMN files.")

