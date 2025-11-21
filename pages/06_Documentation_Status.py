"""
📚 Documentation Status Analysis page for BPMN Analysis app.
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
render_page_header("Documentation Status", "📚")

# Check if data is available
if not has_data():
    upload_icon = "👆"
    st.info("👆 Please upload BPMN XML files on the main page to start the analysis.")
else:
    # Get data from session state
    combined_tasks = get_combined_tasks()
    analysis_data = get_analysis_data()
    
    # Display subheader
    st.subheader("📚 Documentation Status Analysis")
    

    # Define the 4 documentation statuses from your schema with color coding
    doc_status_colors = {
        "Documentation Not Needed": "#FFFFFF",  # White
        "Documented": "#28A745",               # Green
        "In Process to be Documented": "#007BFF", # Blue
        "Not Documented": "#FFC107",           # Yellow
        "Unknown": "#6C757D"                   # Gray for unknown statuses
    }

    # Group by documentation status
    doc_status_analysis = {}
    for task in combined_tasks:
        # Handle empty, null, or whitespace-only doc_status values
        doc_status = task.get('doc_status', '')
        if not doc_status or doc_status.strip() == '' or doc_status == 'None':
            doc_status = 'Unknown'
        else:
            doc_status = doc_status.strip()

        if doc_status not in doc_status_analysis:
            doc_status_analysis[doc_status] = {
                'task_count': 0,
                'total_cost': 0,
                'total_time_minutes': 0,
                'tasks_with_urls': 0,
                'tasks_without_urls': 0
            }

        doc_status_analysis[doc_status]['task_count'] += 1
        doc_status_analysis[doc_status]['total_cost'] += task.get('total_cost', 0)
        doc_status_analysis[doc_status]['total_time_minutes'] += task.get('time_minutes', 0)

        # Count tasks with/without URLs
        # Check if doc_url is valid (not empty, NR, NO URL, etc.)
        doc_url = task.get('doc_url', '')
        doc_url_str = str(doc_url).strip().lower() if doc_url else ''
        if doc_url and doc_url_str not in ['', 'nr', 'no url', 'nourl', 'unknown']:
            doc_status_analysis[doc_status]['tasks_with_urls'] += 1
        else:
            doc_status_analysis[doc_status]['tasks_without_urls'] += 1

    # Create documentation status dataframe
    doc_status_df = pd.DataFrame(doc_status_analysis).T.reset_index()
    doc_status_df.columns = ['Documentation Status', 'Task Count', 'Total Cost', 'total_time_minutes', 'Tasks with URLs', 'Tasks without URLs']

    # Calculate hours from minutes
    doc_status_df['Total Time (hrs)'] = doc_status_df['total_time_minutes'] / 60

    # Calculate percentages
    total_tasks = doc_status_df['Task Count'].sum()
    doc_status_df['Percentage'] = (doc_status_df['Task Count'] / total_tasks * 100).round(1)

    # Reorder columns for better display
    doc_status_df = doc_status_df[['Documentation Status', 'Task Count', 'Percentage', 'Total Cost', 'Total Time (hrs)', 'Tasks with URLs', 'Tasks without URLs']]

    # Format numeric columns to one decimal place
    numeric_columns = ['Task Count', 'Percentage', 'Total Cost', 'Total Time (hrs)', 'Tasks with URLs', 'Tasks without URLs']
    for col in numeric_columns:
        if col in doc_status_df.columns:
            doc_status_df[col] = doc_status_df[col].round(1)

    # Key Metrics - Standardized layout (already has 4-column layout, keep it but ensure consistency)
    # Documentation metrics are already well-structured, just ensure divider

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_documented = doc_status_analysis.get('Documented', {}).get('task_count', 0)
        st.metric(
            "✅ Documented Tasks", 
            f"{total_documented}/{total_tasks}",
            f"{total_documented/total_tasks*100:.1f}%" if total_tasks > 0 else "0%"
        )

    with col2:
        total_in_process = doc_status_analysis.get('In Process to be Documented', {}).get('task_count', 0)
        st.metric(
            "🔄 In Process", 
            f"{total_in_process}/{total_tasks}",
            f"{total_in_process/total_tasks*100:.1f}%" if total_tasks > 0 else "0%"
        )

    with col3:
        total_not_documented = doc_status_analysis.get('Not Documented', {}).get('task_count', 0)
        st.metric(
            "⚠️ Not Documented", 
            f"{total_not_documented}/{total_tasks}",
            f"{total_not_documented/total_tasks*100:.1f}%" if total_tasks > 0 else "0%"
        )

    with col4:
        total_unknown = doc_status_analysis.get('Unknown', {}).get('task_count', 0)
        st.metric(
            "❓ Unknown Status", 
            f"{total_unknown}/{total_tasks}",
            f"{total_unknown/total_tasks*100:.1f}%" if total_tasks > 0 else "0%"
        )

    # Add a second row for additional metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_with_urls = sum(status_data.get('tasks_with_urls', 0) for status_data in doc_status_analysis.values())
        st.metric(
            "🔗 With URLs", 
            f"{total_with_urls}/{total_tasks}",
            f"{total_with_urls/total_tasks*100:.1f}%" if total_tasks > 0 else "0%"
        )

    with col2:
        total_without_urls = sum(status_data.get('tasks_without_urls', 0) for status_data in doc_status_analysis.values())
        st.metric(
            "🔗 Without URLs", 
            f"{total_without_urls}/{total_tasks}",
            f"{total_without_urls/total_tasks*100:.1f}%" if total_tasks > 0 else "0%"
        )

    with col3:
        total_needing_docs = (doc_status_analysis.get('Not Documented', {}).get('task_count', 0) + 
                            doc_status_analysis.get('Unknown', {}).get('task_count', 0))
        st.metric(
            "📝 Needs Documentation", 
            f"{total_needing_docs}/{total_tasks}",
            f"{total_needing_docs/total_tasks*100:.1f}%" if total_tasks > 0 else "0%"
        )

    with col4:
        # Calculate tasks that require attention
        # Tasks that are "Not Documented" or "In Process to be Documented" without URLs need attention
        total_not_documented = doc_status_analysis.get('Not Documented', {}).get('task_count', 0)
        in_process_without_urls = doc_status_analysis.get('In Process to be Documented', {}).get('tasks_without_urls', 0)
        requires_attention = total_not_documented + in_process_without_urls
        st.metric(
            "⚠️ Requires Attention", 
            f"{requires_attention}/{total_tasks}",
            f"{requires_attention/total_tasks*100:.1f}%" if total_tasks > 0 else "0%"
        )

    st.markdown("---")

    # Display detailed status table
    st.write("**📊 Detailed Documentation Status Breakdown**")

    # Apply color coding to the dataframe
    def color_status(val):
        if val in doc_status_colors:
            return f'background-color: {doc_status_colors[val]}'
        return ''

    styled_df = doc_status_df.style.applymap(color_status, subset=['Documentation Status'])
    st.dataframe(styled_df, use_container_width=True)

    # Flag tasks with unknown documentation status
    if 'Unknown' in doc_status_analysis:
        st.markdown("---")
        st.warning("⚠️ **Tasks with Unknown Documentation Status**")
        st.write("The following tasks have missing or invalid documentation status values:")

        # Get tasks with unknown status
        unknown_tasks = [task for task in combined_tasks 
                       if not task.get('doc_status') or 
                       task.get('doc_status', '').strip() == '' or 
                       task.get('doc_status') == 'None']

        if unknown_tasks:
            unknown_df = pd.DataFrame(unknown_tasks)
            display_columns = ['name', 'swimlane', 'task_owner', 'doc_status', 'doc_url', 'time_display', 'total_cost']
            available_columns = [col for col in display_columns if col in unknown_df.columns]

            st.dataframe(
                unknown_df[available_columns],
                use_container_width=True,
                column_config={
                    "doc_status": st.column_config.TextColumn(
                        "Current Status",
                        help="Current documentation status (empty/None)",
                        max_chars=30
                    ),
                    "doc_url": st.column_config.LinkColumn(
                        "Documentation URL",
                        help="Click to open documentation link",
                        max_chars=50
                    )
                }
            )

            # Summary of unknown status tasks
            total_unknown_cost = sum(task.get('total_cost', 0) for task in unknown_tasks)
            total_unknown_time = sum(task.get('time_hours', 0) for task in unknown_tasks)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Tasks with Unknown Status", len(unknown_tasks))
            with col2:
                st.metric("Total Cost at Risk", f"${total_unknown_cost:,.2f}")
            with col3:
                st.metric("Total Time at Risk", f"{total_unknown_time:.1f} hrs")

            st.info("💡 **Recommendation**: Update these tasks in your BPMN files with proper documentation status values from your schema.")
        else:
            st.success("✅ No tasks with unknown documentation status found!")

    # Create two columns for charts
    col1, col2 = st.columns(2)

    with col1:
        # Pie chart with color coding
        fig = px.pie(
            doc_status_df,
            values='Task Count',
            names='Documentation Status',
            title='📊 Tasks by Documentation Status',
            color_discrete_map=doc_status_colors
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Bar chart for cost analysis
        fig2 = px.bar(
            doc_status_df,
            x='Documentation Status',
            y='Total Cost',
            title='💰 Total Cost by Documentation Status',
            color='Task Count',
            color_continuous_scale='viridis'
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Documentation coverage analysis
    st.markdown("---")
    st.write("**🔍 Documentation Coverage Analysis**")

    # Calculate coverage metrics
    documented_tasks = doc_status_analysis.get('Documented', {}).get('task_count', 0)
    in_process_tasks = doc_status_analysis.get('In Process to be Documented', {}).get('task_count', 0)
    coverage_percentage = ((documented_tasks + in_process_tasks) / total_tasks * 100) if total_tasks > 0 else 0

    col1, col2, col3 = st.columns(3)

    with col1:
        if coverage_percentage >= 80:
            st.success(f"📈 Documentation Coverage: {coverage_percentage:.1f}%")
        elif coverage_percentage >= 60:
            st.warning(f"📊 Documentation Coverage: {coverage_percentage:.1f}%")
        else:
            st.error(f"📉 Documentation Coverage: {coverage_percentage:.1f}%")

    with col2:
        tasks_needing_docs = doc_status_analysis.get('Not Documented', {}).get('task_count', 0)
        st.metric("📝 Tasks Needing Documentation", tasks_needing_docs)

    with col3:
        tasks_in_process = doc_status_analysis.get('In Process to be Documented', {}).get('task_count', 0)
        st.metric("🔄 Tasks In Process", tasks_in_process)

    # Tasks requiring documentation attention
    st.markdown("---")
    st.write("**⚠️ Tasks Requiring Documentation Attention**")

    # Filter tasks that need documentation
    tasks_needing_docs = [task for task in combined_tasks 
                        if task.get('doc_status') in ['Not Documented', 'In Process to be Documented']]

    if tasks_needing_docs:
        attention_df = pd.DataFrame(tasks_needing_docs)
        display_columns = ['name', 'swimlane', 'task_owner', 'doc_status', 'doc_url', 'time_display', 'total_cost']
        available_columns = [col for col in display_columns if col in attention_df.columns]

        # Format doc_url for display - treat NR/NO URL as empty
        def format_doc_url_display(url):
            if pd.isna(url):
                return ''
            url_str = str(url).strip()
            if url_str.lower() in ['nr', 'no url', 'nourl', 'unknown', '']:
                return ''
            return url_str
        
        attention_df_display = attention_df.copy()
        if 'doc_url' in attention_df_display.columns:
            attention_df_display['doc_url_display'] = attention_df_display['doc_url'].apply(format_doc_url_display)
            # Replace doc_url with formatted version for display
            display_cols = [col if col != 'doc_url' else 'doc_url_display' for col in available_columns]
            display_cols = [col for col in display_cols if col in attention_df_display.columns]
        else:
            display_cols = available_columns

        st.dataframe(
            attention_df_display[display_cols],
            use_container_width=True,
            column_config={
                "doc_status": st.column_config.TextColumn(
                    "Documentation Status",
                    help="Current documentation status",
                    max_chars=30
                ),
                "doc_url_display": st.column_config.TextColumn(
                    "Documentation URL",
                    help="Documentation link (empty if NR/NO URL)",
                    max_chars=50
                ) if 'doc_url_display' in display_cols else None
            }
        )

        # Summary of documentation attention needed
        total_attention_cost = sum(task.get('total_cost', 0) for task in tasks_needing_docs)
        total_attention_time = sum(task.get('time_hours', 0) for task in tasks_needing_docs)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tasks Needing Docs", len(tasks_needing_docs))
        with col2:
            st.metric("Total Cost at Risk", f"${total_attention_cost:,.2f}")
        with col3:
            st.metric("Total Time at Risk", f"{total_attention_time:.1f} hrs")
    else:
        st.success("🎉 All tasks are properly documented! No documentation attention needed.")

