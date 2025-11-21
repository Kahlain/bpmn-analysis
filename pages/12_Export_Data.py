"""
💾 Export Data & Reports page for BPMN Analysis app.
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
render_page_header("Export Data", "💾")

# Check if data is available
if not has_data():
    st.info("👆 Please upload BPMN XML files on the main page to start the analysis.")
else:
    # Get data from session state
    combined_tasks = get_combined_tasks()
    analysis_data = get_analysis_data()
    
    # Display subheader
    st.subheader("💾 Export Data & Reports")
    

    # Export options
    col1, col2 = st.columns(2)

    with col1:
        export_format = st.selectbox(
            "Select export format:",
            ["Excel (.xlsx)", "Markdown (.md)", "CSV", "JSON"]
        )

        export_scope = st.selectbox(
            "Select export scope:",
            ["Complete Analysis", "Tasks Only", "Summary Only", "Issues & Opportunities Only", "FAQ Knowledge Only", "Documentation Status Only", "Tools Analysis Only"]
        )

    with col2:
        st.write("**Export Options:**")
        st.write("• **Complete Analysis**: All data + charts")
        st.write("• **Tasks Only**: Raw task data")
        st.write("• **Summary Only**: Key metrics & insights")

    # Export button
    if st.button("🚀 Generate Export", type="primary"):
        if export_format == "Excel (.xlsx)":
            # Generate comprehensive Excel report
            try:
                filename = f"bpmn_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

                if export_scope == "Complete Analysis":
                    # Use the existing analysis_data that's already computed
                    analyzer.generate_excel_report(analysis_data, filename)
                    st.success(f"✅ Complete Excel report generated: {filename}")
                elif export_scope == "Tasks Only":
                    # Export only tasks data
                    tasks_df = pd.DataFrame(combined_tasks)
                    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                        tasks_df.to_excel(writer, sheet_name='Tasks', index=False)
                    st.success(f"✅ Tasks Excel report generated: {filename}")
                elif export_scope == "Issues & Opportunities Only":
                    # Export only issues and opportunities data
                    issues_opportunities_data = []
                    for task in combined_tasks:
                        # Add opportunities
                        opportunities = task.get('opportunities', '')
                        if opportunities and opportunities.strip():
                            issues_opportunities_data.append({
                                'Type': 'Opportunity',
                                'Task Name': task.get('name', 'Unknown'),
                                'Department': task.get('swimlane', 'Unknown'),
                                'Owner': task.get('task_owner', 'Unknown'),
                                'Content': opportunities,
                                'Current Cost': task.get('total_cost', 0),
                                'Current Time (hrs)': task.get('time_hours', 0),
                                'Status': task.get('task_status', 'Unknown'),
                                'Tools Used': task.get('tools_used', 'N/A')
                            })

                        # Add issues
                        issues_text = task.get('issues_text', '')
                        if issues_text and issues_text.strip():
                            issues_opportunities_data.append({
                                'Type': 'Issue/Risk',
                                'Task Name': task.get('name', 'Unknown'),
                                'Department': task.get('swimlane', 'Unknown'),
                                'Owner': task.get('task_owner', 'Unknown'),
                                'Content': issues_text,
                                'Priority': task.get('issues_priority', 'Unknown'),
                                'Current Cost': task.get('total_cost', 0),
                                'Current Time (hrs)': task.get('time_hours', 0),
                                'Status': task.get('task_status', 'Unknown'),
                                'Tools Used': task.get('tools_used', 'N/A')
                            })

                    if issues_opportunities_data:
                        issues_df = pd.DataFrame(issues_opportunities_data)
                        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                            issues_df.to_excel(writer, sheet_name='Issues_Opportunities', index=False)
                        st.success(f"✅ Issues & Opportunities Excel report generated: {filename}")
                    else:
                        st.warning("⚠️ No issues or opportunities found in the data")

                elif export_scope == "FAQ Knowledge Only":
                    # Export only FAQ data
                    faq_data = []
                    for task in combined_tasks:
                        # Check for FAQ fields
                        faq_fields = ['faq_q1', 'faq_a1', 'faq_q2', 'faq_a2', 'faq_q3', 'faq_a3']
                        task_has_faqs = False

                        for i in range(1, 4):
                            q_key = f'faq_q{i}'
                            a_key = f'faq_a{i}'
                            question = task.get(q_key, '')
                            answer = task.get(a_key, '')

                            if question and question.strip() and answer and answer.strip():
                                task_has_faqs = True
                                faq_data.append({
                                    'Task Name': task.get('name', 'Unknown'),
                                    'Department': task.get('swimlane', 'Unknown'),
                                    'Owner': task.get('task_owner', 'Unknown'),
                                    'FAQ #': i,
                                    'Question': question.strip(),
                                    'Answer': answer.strip(),
                                    'Current Cost': task.get('total_cost', 0),
                                    'Current Time (hrs)': task.get('time_hours', 0),
                                    'Status': task.get('task_status', 'Unknown'),
                                    'Tools Used': task.get('tools_used', 'N/A')
                                })

                        # If no FAQs found, add a placeholder row
                        if not task_has_faqs:
                            faq_data.append({
                                'Task Name': task.get('name', 'Unknown'),
                                'Department': task.get('swimlane', 'Unknown'),
                                'Owner': task.get('task_owner', 'Unknown'),
                                'FAQ #': 'N/A',
                                'Question': 'No FAQ captured',
                                'Answer': 'No FAQ captured',
                                'Current Cost': task.get('total_cost', 0),
                                'Current Time (hrs)': task.get('time_hours', 0),
                                'Status': task.get('task_status', 'Unknown'),
                                'Tools Used': task.get('tools_used', 'N/A')
                            })

                    if faq_data:
                        faq_df = pd.DataFrame(faq_data)
                        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                            faq_df.to_excel(writer, sheet_name='FAQ_Knowledge', index=False)
                        st.success(f"✅ FAQ Knowledge Excel report generated: {filename}")
                    else:
                        st.warning("⚠️ No FAQ data found in the tasks")
                elif export_scope == "Documentation Status Only":
                    # Export only documentation status data
                    doc_status_data = []
                    for task in combined_tasks:
                        doc_status_data.append({
                            'Task Name': task.get('name', 'Unknown'),
                            'Department': task.get('swimlane', 'Unknown'),
                            'Owner': task.get('task_owner', 'Unknown'),
                            'Documentation Status': task.get('doc_status', 'Unknown'),
                            'Documentation URL': task.get('doc_url', '') or 'N/A',  # Empty/NR/NO URL shows as N/A
                            'Current Cost': task.get('total_cost', 0),
                            'Current Time (hrs)': task.get('time_hours', 0),
                            'Status': task.get('task_status', 'Unknown'),
                            'Tools Used': task.get('tools_used', 'N/A')
                        })

                    if doc_status_data:
                        doc_df = pd.DataFrame(doc_status_data)
                        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                            doc_df.to_excel(writer, sheet_name='Documentation_Status', index=False)
                        st.success(f"✅ Documentation Status Excel report generated: {filename}")
                    else:
                        st.warning("⚠️ No documentation status data found")
                elif export_scope == "Tools Analysis Only":
                    # Export only tools analysis data
                    tools_data = []
                    for task in combined_tasks:
                        tools = task.get('tools_used', '')
                        if tools and tools.strip():
                            # Split tools and add each one
                            tool_list = [tool.strip() for tool in tools.split(',') if tool.strip()]
                            for tool in tool_list:
                                tools_data.append({
                                    'Task Name': task.get('name', 'Unknown'),
                                    'Department': task.get('swimlane', 'Unknown'),
                                    'Owner': task.get('task_owner', 'Unknown'),
                                    'Tool Used': tool,
                                    'Original Tools Field': tools,
                                    'Current Cost': task.get('total_cost', 0),
                                    'Current Time (hrs)': task.get('time_hours', 0),
                                    'Status': task.get('task_status', 'Unknown')
                                })
                        else:
                            # Task with no tools
                            tools_data.append({
                                'Task Name': task.get('name', 'Unknown'),
                                'Department': task.get('swimlane', 'Unknown'),
                                'Owner': task.get('task_owner', 'Unknown'),
                                'Tool Used': 'No tools specified',
                                'Original Tools Field': 'N/A',
                                'Current Cost': task.get('total_cost', 0),
                                'Current Time (hrs)': task.get('time_hours', 0),
                                'Status': task.get('task_status', 'Unknown')
                            })

                    if tools_data:
                        tools_df = pd.DataFrame(tools_data)
                        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                            tools_df.to_excel(writer, sheet_name='Tools_Analysis', index=False)
                        st.success(f"✅ Tools Analysis Excel report generated: {filename}")
                    else:
                        st.warning("⚠️ No tools data found in the tasks")
                else:  # Summary Only
                    # Export summary metrics
                    summary_data = {
                        'Metric': ['Total Tasks', 'Total Cost', 'Total Time (hrs)', 'Departments', 'Task Owners'],
                        'Value': [
                            len(combined_tasks),
                            f"{analysis_data.get('total_costs', 0):.2f}",
                            f"{analysis_data.get('total_time', 0) / 60:.2f}",
                            len(set(task.get('swimlane', 'Unknown') for task in combined_tasks)),
                            len(set(task.get('task_owner', 'Unknown') for task in combined_tasks))
                        ]
                    }
                    summary_df = pd.DataFrame(summary_data)
                    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                        summary_df.to_excel(writer, sheet_name='Summary', index=False)
                    st.success(f"✅ Summary Excel report generated: {filename}")

                # Provide download link
                with open(filename, "rb") as file:
                    st.download_button(
                        label="📥 Download Excel Report",
                        data=file.read(),
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            except Exception as e:
                st.error(f"❌ Error generating Excel report: {str(e)}")
                st.error("Please check if the file is open in another application.")

        elif export_format == "CSV":
            # Export data as CSV
            try:
                if export_scope == "Complete Analysis":
                    # Export all analysis data
                    csv_files = {}

                    # Tasks CSV
                    tasks_df = pd.DataFrame(combined_tasks)
                    csv_files['tasks'] = tasks_df.to_csv(index=False)

                    # Swimlane analysis CSV
                    if 'swimlane_analysis' in analysis_data:
                        swimlane_df = pd.DataFrame(analysis_data['swimlane_analysis']).T.reset_index()
                        csv_files['swimlane_analysis'] = swimlane_df.to_csv(index=False)

                    # Owner analysis CSV
                    if 'owner_analysis' in analysis_data:
                        owner_df = pd.DataFrame(analysis_data['owner_analysis']).T.reset_index()
                        csv_files['owner_analysis'] = owner_df.to_csv(index=False)

                    # Create zip file with multiple CSVs
                    import zipfile
                    import io

                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for name, csv_data in csv_files.items():
                            zip_file.writestr(f"{name}.csv", csv_data)

                    zip_buffer.seek(0)
                    st.download_button(
                        label="📥 Download All CSVs (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name=f"bpmn_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip"
                    )
                elif export_scope == "Issues & Opportunities Only":
                    # Export only issues and opportunities data
                    issues_opportunities_data = []
                    for task in combined_tasks:
                        # Add opportunities
                        opportunities = task.get('opportunities', '')
                        if opportunities and opportunities.strip():
                            issues_opportunities_data.append({
                                'Type': 'Opportunity',
                                'Task Name': task.get('name', 'Unknown'),
                                'Department': task.get('swimlane', 'Unknown'),
                                'Owner': task.get('task_owner', 'Unknown'),
                                'Content': opportunities,
                                'Current Cost': task.get('total_cost', 0),
                                'Current Time (hrs)': task.get('time_hours', 0),
                                'Status': task.get('task_status', 'Unknown'),
                                'Tools Used': task.get('tools_used', 'N/A')
                            })

                        # Add issues
                        issues_text = task.get('issues_text', '')
                        if issues_text and issues_text.strip():
                            issues_opportunities_data.append({
                                'Type': 'Issue/Risk',
                                'Task Name': task.get('name', 'Unknown'),
                                'Department': task.get('swimlane', 'Unknown'),
                                'Owner': task.get('task_owner', 'Unknown'),
                                'Content': issues_text,
                                'Priority': task.get('issues_priority', 'Unknown'),
                                'Current Cost': task.get('total_cost', 0),
                                'Current Time (hrs)': task.get('time_hours', 0),
                                'Status': task.get('task_status', 'Unknown'),
                                'Tools Used': task.get('tools_used', 'N/A')
                            })

                    if issues_opportunities_data:
                        issues_df = pd.DataFrame(issues_opportunities_data)
                        csv_data = issues_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Issues & Opportunities CSV",
                            data=csv_data,
                            file_name=f"bpmn_issues_opportunities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning("⚠️ No issues or opportunities found in the data")

                elif export_scope == "FAQ Knowledge Only":
                    # Export only FAQ data
                    faq_data = []
                    for task in combined_tasks:
                        # Check for FAQ fields
                        faq_fields = ['faq_q1', 'faq_a1', 'faq_q2', 'faq_a2', 'faq_q3', 'faq_a3']
                        task_has_faqs = False

                        for i in range(1, 4):
                            q_key = f'faq_q{i}'
                            a_key = f'faq_a{i}'
                            question = task.get(q_key, '')
                            answer = task.get(a_key, '')

                            if question and question.strip() and answer and answer.strip():
                                task_has_faqs = True
                                faq_data.append({
                                    'Task Name': task.get('name', 'Unknown'),
                                    'Department': task.get('swimlane', 'Unknown'),
                                    'Owner': task.get('task_owner', 'Unknown'),
                                    'FAQ #': i,
                                    'Question': question.strip(),
                                    'Answer': answer.strip(),
                                    'Current Cost': task.get('total_cost', 0),
                                    'Current Time (hrs)': task.get('time_hours', 0),
                                    'Status': task.get('task_status', 'Unknown'),
                                    'Tools Used': task.get('tools_used', 'N/A')
                                })

                        # If no FAQs found, add a placeholder row
                        if not task_has_faqs:
                            faq_data.append({
                                'Task Name': task.get('name', 'Unknown'),
                                'Department': task.get('swimlane', 'Unknown'),
                                'Owner': task.get('task_owner', 'Unknown'),
                                'FAQ #': 'N/A',
                                'Question': 'No FAQ captured',
                                'Answer': 'No FAQ captured',
                                'Current Cost': task.get('total_cost', 0),
                                'Current Time (hrs)': task.get('time_hours', 0),
                                'Status': task.get('task_status', 'Unknown'),
                                'Tools Used': task.get('tools_used', 'N/A')
                            })

                    if faq_data:
                        faq_df = pd.DataFrame(faq_data)
                        csv_data = faq_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download FAQ Knowledge CSV",
                            data=csv_data,
                            file_name=f"bpmn_faq_knowledge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning("⚠️ No FAQ data found in the tasks")
                elif export_scope == "Documentation Status Only":
                    # Export only documentation status data
                    doc_status_data = []
                    for task in combined_tasks:
                        doc_status_data.append({
                            'Task Name': task.get('name', 'Unknown'),
                            'Department': task.get('swimlane', 'Unknown'),
                            'Owner': task.get('task_owner', 'Unknown'),
                            'Documentation Status': task.get('doc_status', 'Unknown'),
                            'Documentation URL': task.get('doc_url', '') or 'N/A',  # Empty/NR/NO URL shows as N/A
                            'Current Cost': task.get('total_cost', 0),
                            'Current Time (hrs)': task.get('time_hours', 0),
                            'Status': task.get('task_status', 'Unknown'),
                            'Tools Used': task.get('tools_used', 'N/A')
                        })

                    if doc_status_data:
                        doc_df = pd.DataFrame(doc_status_data)
                        csv_data = doc_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Documentation Status CSV",
                            data=csv_data,
                            file_name=f"bpmn_documentation_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning("⚠️ No documentation status data found")
                elif export_scope == "Tools Analysis Only":
                    # Export only tools analysis data
                    tools_data = []
                    for task in combined_tasks:
                        tools = task.get('tools_used', '')
                        if tools and tools.strip():
                            # Split tools and add each one
                            tool_list = [tool.strip() for tool in tools.split(',') if tool.strip()]
                            for tool in tool_list:
                                tools_data.append({
                                    'Task Name': task.get('name', 'Unknown'),
                                    'Department': task.get('swimlane', 'Unknown'),
                                    'Owner': task.get('task_owner', 'Unknown'),
                                    'Tool Used': tool,
                                    'Original Tools Field': tools,
                                    'Current Cost': task.get('total_cost', 0),
                                    'Current Time (hrs)': task.get('time_hours', 0),
                                    'Status': task.get('task_status', 'Unknown')
                                })
                        else:
                            # Task with no tools
                            tools_data.append({
                                'Task Name': task.get('name', 'Unknown'),
                                'Department': task.get('swimlane', 'Unknown'),
                                'Owner': task.get('task_owner', 'Unknown'),
                                'Tool Used': 'No tools specified',
                                'Original Tools Field': 'N/A',
                                'Current Cost': task.get('total_cost', 0),
                                'Current Time (hrs)': task.get('time_hours', 0),
                                'Status': task.get('task_status', 'Unknown')
                            })

                    if tools_data:
                        tools_df = pd.DataFrame(tools_data)
                        csv_data = tools_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Tools Analysis CSV",
                            data=csv_data,
                            file_name=f"bpmn_tools_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning("⚠️ No tools data found in the tasks")
                else:
                    # Export single CSV
                    tasks_df = pd.DataFrame(combined_tasks)
                    csv_data = tasks_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=f"bpmn_tasks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )

            except Exception as e:
                st.error(f"❌ Error generating CSV: {str(e)}")

        elif export_format == "Markdown (.md)":
            # Export as comprehensive Markdown report
            try:
                if export_scope == "Complete Analysis":
                    markdown_content = generate_markdown_report(analysis_data, combined_tasks)
                elif export_scope == "Tasks Only":
                    markdown_content = generate_tasks_markdown(combined_tasks)
                elif export_scope == "Issues & Opportunities Only":
                    markdown_content = generate_issues_opportunities_markdown(combined_tasks)
                elif export_scope == "FAQ Knowledge Only":
                    markdown_content = generate_faq_markdown(combined_tasks)
                elif export_scope == "Documentation Status Only":
                    markdown_content = generate_documentation_status_markdown(combined_tasks)
                elif export_scope == "Tools Analysis Only":
                    markdown_content = generate_tools_analysis_markdown(combined_tasks)
                else:  # Summary Only
                    markdown_content = generate_summary_markdown(analysis_data, combined_tasks)

                st.download_button(
                    label="📥 Download Markdown Report",
                    data=markdown_content,
                    file_name=f"bpmn_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )

            except Exception as e:
                st.error(f"❌ Error generating Markdown report: {str(e)}")

        elif export_format == "JSON":
            # Export as JSON
            try:
                if export_scope == "Complete Analysis":
                    json_data = json.dumps(analysis_data, indent=2, default=str)
                elif export_scope == "Tasks Only":
                    json_data = json_data = json.dumps(combined_tasks, indent=2, default=str)
                elif export_scope == "Issues & Opportunities Only":
                    # Export only issues and opportunities data
                    issues_opportunities_data = []
                    for task in combined_tasks:
                        # Add opportunities
                        opportunities = task.get('opportunities', '')
                        if opportunities and opportunities.strip():
                            issues_opportunities_data.append({
                                'type': 'Opportunity',
                                'task_name': task.get('name', 'Unknown'),
                                'department': task.get('swimlane', 'Unknown'),
                                'owner': task.get('task_owner', 'Unknown'),
                                'content': opportunities,
                                'current_cost': task.get('total_cost', 0),
                                'current_time_hours': task.get('time_hours', 0),
                                'status': task.get('task_status', 'Unknown'),
                                'tools_used': task.get('tools_used', 'N/A')
                            })

                        # Add issues
                        issues_text = task.get('issues_text', '')
                        if issues_text and issues_text.strip():
                            issues_opportunities_data.append({
                                'type': 'Issue/Risk',
                                'task_name': task.get('name', 'Unknown'),
                                'department': task.get('swimlane', 'Unknown'),
                                'owner': task.get('task_owner', 'Unknown'),
                                'content': issues_text,
                                'priority': task.get('issues_priority', 'Unknown'),
                                'current_cost': task.get('total_cost', 0),
                                'current_time_hours': task.get('time_hours', 0),
                                'status': task.get('task_status', 'Unknown'),
                                'tools_used': task.get('tools_used', 'N/A')
                            })

                    if issues_opportunities_data:
                        json_data = json.dumps(issues_opportunities_data, indent=2, default=str)
                    else:
                        st.warning("⚠️ No issues or opportunities found in the data")

                elif export_scope == "FAQ Knowledge Only":
                    # Export only FAQ data
                    faq_data = []
                    for task in combined_tasks:
                        # Check for FAQ fields
                        faq_fields = ['faq_q1', 'faq_a1', 'faq_q2', 'faq_a2', 'faq_q3', 'faq_a3']
                        task_has_faqs = False

                        for i in range(1, 4):
                            q_key = f'faq_q{i}'
                            a_key = f'faq_a{i}'
                            question = task.get(q_key, '')
                            answer = task.get(a_key, '')

                            if question and question.strip() and answer and answer.strip():
                                task_has_faqs = True
                                faq_data.append({
                                    'type': 'FAQ',
                                    'task_name': task.get('name', 'Unknown'),
                                    'department': task.get('swimlane', 'Unknown'),
                                    'owner': task.get('task_owner', 'Unknown'),
                                    'faq_number': i,
                                    'question': question.strip(),
                                    'answer': answer.strip(),
                                    'current_cost': task.get('total_cost', 0),
                                    'current_time_hours': task.get('time_hours', 0),
                                    'status': task.get('task_status', 'Unknown'),
                                    'tools_used': task.get('tools_used', 'N/A')
                                })

                        # If no FAQs found, add a placeholder row
                        if not task_has_faqs:
                            faq_data.append({
                                'type': 'FAQ',
                                'task_name': task.get('name', 'Unknown'),
                                'department': task.get('swimlane', 'Unknown'),
                                'owner': task.get('task_owner', 'Unknown'),
                                'faq_number': 'N/A',
                                'question': 'No FAQ captured',
                                'answer': 'No FAQ captured',
                                'current_cost': task.get('total_cost', 0),
                                'current_time_hours': task.get('time_hours', 0),
                                'status': task.get('task_status', 'Unknown'),
                                'tools_used': task.get('tools_used', 'N/A')
                            })

                    if faq_data:
                        json_data = json.dumps(faq_data, indent=2, default=str)
                    else:
                        st.warning("⚠️ No FAQ data found in the tasks")
                elif export_scope == "Documentation Status Only":
                    # Export only documentation status data
                    doc_status_data = []
                    for task in combined_tasks:
                        doc_status_data.append({
                            'type': 'Documentation',
                            'task_name': task.get('name', 'Unknown'),
                            'department': task.get('swimlane', 'Unknown'),
                            'owner': task.get('task_owner', 'Unknown'),
                            'documentation_status': task.get('doc_status', 'Unknown'),
                            'documentation_url': task.get('doc_url', '') or 'N/A',  # Empty/NR/NO URL shows as N/A
                            'current_cost': task.get('total_cost', 0),
                            'current_time_hours': task.get('time_hours', 0),
                            'status': task.get('task_status', 'Unknown'),
                            'tools_used': task.get('tools_used', 'N/A')
                        })

                    if doc_status_data:
                        json_data = json.dumps(doc_status_data, indent=2, default=str)
                    else:
                        st.warning("⚠️ No documentation status data found")
                elif export_scope == "Tools Analysis Only":
                    # Export only tools analysis data
                    tools_data = []
                    for task in combined_tasks:
                        tools = task.get('tools_used', '')
                        if tools and tools.strip():
                            # Split tools and add each one
                            tool_list = [tool.strip() for tool in tools.split(',') if tool.strip()]
                            for tool in tool_list:
                                tools_data.append({
                                    'type': 'Tool',
                                    'task_name': task.get('name', 'Unknown'),
                                    'department': task.get('swimlane', 'Unknown'),
                                    'owner': task.get('task_owner', 'Unknown'),
                                    'tool_used': tool,
                                    'original_tools_field': tools,
                                    'current_cost': task.get('total_cost', 0),
                                    'current_time_hours': task.get('time_hours', 0),
                                    'status': task.get('task_status', 'Unknown')
                                })
                        else:
                            # Task with no tools
                            tools_data.append({
                                'type': 'Tool',
                                'task_name': task.get('name', 'Unknown'),
                                'department': task.get('swimlane', 'Unknown'),
                                'owner': task.get('task_owner', 'Unknown'),
                                'tool_used': 'No tools specified',
                                'original_tools_field': 'N/A',
                                'current_cost': task.get('total_cost', 0),
                                'current_time_hours': task.get('time_hours', 0),
                                'status': task.get('task_status', 'Unknown')
                            })

                    if tools_data:
                        json_data = json.dumps(tools_data, indent=2, default=str)
                    else:
                        st.warning("⚠️ No tools data found in the tasks")
                else:  # Summary Only
                    summary_data = {
                        'summary': {
                            'total_tasks': len(combined_tasks),
                            'total_cost': analysis_data.get('total_costs', 0),
                            'total_time_hours': analysis_data.get('total_time', 0) / 60,
                            'departments_count': len(set(task.get('swimlane', 'Unknown') for task in combined_tasks)),
                            'owners_count': len(set(task.get('task_owner', 'Unknown') for task in combined_tasks))
                        }
                    }
                    json_data = json.dumps(summary_data, indent=2, default=str)

                st.download_button(
                    label="📥 Download JSON",
                    data=json_data,
                    file_name=f"bpmn_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

            except Exception as e:
                st.error(f"❌ Error generating JSON: {str(e)}")

    # Show export preview
    st.subheader("📊 Export Preview")

    if export_scope == "Complete Analysis":
        st.write("**Complete Analysis Export includes:**")
        st.write("• All task details with metadata")
        st.write("• Swimlane/Department analysis")
        st.write("• Owner analysis and workload distribution")
        st.write("• Status and priority analysis")
        st.write("• Documentation status analysis")
        st.write("• Tools usage analysis")
        st.write("• Opportunities and improvement ideas")
        st.write("• Issues and risk analysis")
        st.write("• FAQ knowledge capture")
        st.write("• Quality control metrics")

        if export_format == "Markdown (.md)":
            pass

