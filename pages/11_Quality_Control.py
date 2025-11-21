"""
✅ Quality Control page for BPMN Analysis app.
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
render_page_header("Quality Control", "✅")

# Check if data is available
if not has_data():
    st.info("👆 Please upload BPMN XML files on the main page to start the analysis.")
else:
    # Get data from session state
    combined_tasks = get_combined_tasks()
    analysis_data = get_analysis_data()
    
    # Display subheader    # Header already rendered by render_page_header() above
    

    # Quality check results
    quality_issues = []
    critical_issues = []
    warning_issues = []
    info_issues = []

    for task in combined_tasks:
        issues = []
        critical_count = 0
        warning_count = 0
        info_count = 0

        # CRITICAL ISSUES (Red - High Impact) - Business Critical
        if not task.get('swimlane') or task.get('swimlane') == 'Unknown':
            issues.append("🚨 Missing/Invalid Swimlane")
            critical_count += 1

        if not task.get('task_owner') or task.get('task_owner') == '':
            issues.append("🚨 Missing Task Owner")
            critical_count += 1

        if not task.get('time_hhmm') or task.get('time_hhmm') == '':
            issues.append("🚨 Missing Time Estimate")
            critical_count += 1

        # Check if cost_per_hour is missing (None, empty string) but not 0
        cost_per_hour = task.get('cost_per_hour')
        if cost_per_hour is None or cost_per_hour == '':
            issues.append("🚨 Missing Cost per Hour")
            critical_count += 1
        # Note: cost_per_hour == 0 is valid for tasks that don't cost anything

        # WARNING ISSUES (Orange - Medium Impact) - Important for Compliance
        if not task.get('task_status') or task.get('task_status') == '':
            issues.append("⚠️ Missing Task Status")
            warning_count += 1

        if not task.get('doc_status') or task.get('doc_status') == '':
            issues.append("⚠️ Missing Documentation Status")
            warning_count += 1

        # Check documentation URL if status indicates documentation is needed
        doc_status = task.get('doc_status', '')
        if doc_status and doc_status not in ['Documentation Not Needed', 'Unknown']:
            doc_url = task.get('doc_url', '')
            # Treat NR, NO URL, No URL as empty
            doc_url_str = str(doc_url).strip().lower() if doc_url else ''
            if not doc_url or doc_url_str in ['', 'nr', 'no url', 'nourl', 'unknown']:
                issues.append("⚠️ Missing Documentation URL")
                warning_count += 1

        if not task.get('task_description') or task.get('task_description') == '':
            issues.append("⚠️ Missing Task Description")
            warning_count += 1

        # INFO ISSUES (Blue - Low Impact) - Enhancement Opportunities
        if not task.get('tools_used') or task.get('tools_used') == '':
            issues.append("ℹ️ Missing Tools Information")
            info_count += 1

        if not task.get('opportunities') or task.get('opportunities') == '':
            issues.append("ℹ️ Missing Opportunities")
            info_count += 1

        if not task.get('issues_text') or task.get('issues_text') == '':
            issues.append("ℹ️ Missing Issues Information")
            info_count += 1

        # Check FAQ fields - only if any FAQ field exists
        faq_fields = ['faq_q1', 'faq_a1', 'faq_q2', 'faq_a2', 'faq_q3', 'faq_a3']
        has_any_faq = any(task.get(field, '') for field in faq_fields)
        if has_any_faq:
            # Check if FAQ pairs are complete
            for i in range(1, 4):
                q_key = f'faq_q{i}'
                a_key = f'faq_a{i}'
                question = task.get(q_key, '')
                answer = task.get(a_key, '')
                if question and not answer:
                    issues.append(f"ℹ️ Incomplete FAQ {i} (missing answer)")
                    info_count += 1
                elif answer and not question:
                    issues.append(f"ℹ️ Incomplete FAQ {i} (missing question)")
                    info_count += 1
        else:
            issues.append("ℹ️ No FAQ Knowledge Captured")
            info_count += 1

        if not task.get('task_industry') or task.get('task_industry') == '':
            issues.append("ℹ️ Missing Industry Context")
            info_count += 1

        if issues:
            quality_issues.append({
                'Task Name': task.get('name', 'Unknown'),
                'Swimlane': task.get('swimlane', 'Unknown'),
                'Owner': task.get('task_owner', 'Unknown'),
                'Issues': '; '.join(issues),
                'Critical Issues': critical_count,
                'Warning Issues': warning_count,
                'Info Issues': info_count,
                'Total Issues': len(issues),
                'Current Cost': task.get('total_cost', 0),
                'Current Time': task.get('time_hhmm', '00:00'),
                'Priority': 'High' if critical_count > 0 else 'Medium' if warning_count > 0 else 'Low'
            })

    if quality_issues:
        # Sort by priority and total issues (critical first, then by issue count)
        quality_issues.sort(key=lambda x: (x['Priority'] == 'High', x['Total Issues']), reverse=True)

        # Count by priority
        high_priority = sum(1 for issue in quality_issues if issue['Priority'] == 'High')
        medium_priority = sum(1 for issue in quality_issues if issue['Priority'] == 'Medium')
        low_priority = sum(1 for issue in quality_issues if issue['Priority'] == 'Low')

        # Display priority-based alerts
        if high_priority > 0:
            st.error(f"🚨 CRITICAL: {high_priority} tasks have high-priority issues that need immediate attention!")
        if medium_priority > 0:
            st.warning(f"⚠️ WARNING: {medium_priority} tasks have medium-priority issues to address")
        if low_priority > 0:
            st.info(f"ℹ️ INFO: {low_priority} tasks have low-priority issues for future improvement")

        # Summary statistics with priority breakdown
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Tasks with Issues", len(quality_issues))
        with col2:
            critical_issues_count = sum(issue['Critical Issues'] for issue in quality_issues)
            st.metric("Critical Issues", critical_issues_count, delta=f"+{critical_issues_count}")
        with col3:
            warning_issues_count = sum(issue['Warning Issues'] for issue in quality_issues)
            st.metric("Warning Issues", warning_issues_count, delta=f"+{warning_issues_count}")
        with col4:
            info_issues_count = sum(issue['Info Issues'] for issue in quality_issues)
            st.metric("Info Issues", info_issues_count, delta=f"+{info_issues_count}")

        # Data Quality Score and Compliance Metrics
        st.markdown("---")
        st.subheader("📊 Data Quality Score & Compliance")

        # Calculate overall data quality score
        total_tasks = len(combined_tasks)
        total_possible_fields = total_tasks * 15  # Approximate number of fields per task
        total_issues = sum(issue['Total Issues'] for issue in quality_issues)
        quality_score = max(0, ((total_possible_fields - total_issues) / total_possible_fields * 100)) if total_possible_fields > 0 else 100

        # Calculate compliance scores by category
        critical_compliance = max(0, ((total_tasks - high_priority) / total_tasks * 100)) if total_tasks > 0 else 100
        warning_compliance = max(0, ((total_tasks - medium_priority) / total_tasks * 100)) if total_tasks > 0 else 100
        info_compliance = max(0, ((total_tasks - low_priority) / total_tasks * 100)) if total_tasks > 0 else 100

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if quality_score >= 90:
                st.success(f"🎯 Overall Quality Score: {quality_score:.1f}%")
            elif quality_score >= 75:
                st.warning(f"📊 Overall Quality Score: {quality_score:.1f}%")
            else:
                st.error(f"📉 Overall Quality Score: {quality_score:.1f}%")

        with col2:
            if critical_compliance >= 95:
                st.success(f"🚨 Critical Compliance: {critical_compliance:.1f}%")
            elif critical_compliance >= 80:
                st.warning(f"⚠️ Critical Compliance: {critical_compliance:.1f}%")
            else:
                st.error(f"❌ Critical Compliance: {critical_compliance:.1f}%")

        with col3:
            if warning_compliance >= 80:
                st.success(f"⚠️ Warning Compliance: {warning_compliance:.1f}%")
            elif warning_compliance >= 60:
                st.warning(f"📊 Warning Compliance: {warning_compliance:.1f}%")
            else:
                st.error(f"📉 Warning Compliance: {warning_compliance:.1f}%")

        with col4:
            if info_compliance >= 70:
                st.success(f"ℹ️ Info Compliance: {info_compliance:.1f}%")
            elif info_compliance >= 50:
                st.warning(f"📊 Info Compliance: {info_compliance:.1f}%")
            else:
                st.error(f"📉 Info Compliance: {info_compliance:.1f}%")

        # Quality improvement recommendations
        st.markdown("---")
        st.subheader("💡 Quality Improvement Recommendations")

        recommendations = []
        if critical_compliance < 95:
            recommendations.append("🚨 **Immediate Action Required**: Address critical issues to ensure business continuity")
        if warning_compliance < 80:
            recommendations.append("⚠️ **Compliance Focus**: Improve documentation and status tracking for regulatory compliance")
        if info_compliance < 70:
            recommendations.append("ℹ️ **Knowledge Enhancement**: Capture more opportunities, issues, and FAQ knowledge")
        if quality_score < 90:
            recommendations.append("📊 **Overall Improvement**: Focus on data completeness across all fields")

        if recommendations:
            for rec in recommendations:
                st.info(rec)
        else:
            st.success("🎉 **Excellent Data Quality**: All compliance thresholds met!")

        # Priority-based filtering
        st.subheader("🔍 Filter by Priority")
        priority_filter = st.selectbox(
            "Select priority level to view:",
            ["All Priorities", "High Priority", "Medium Priority", "Low Priority"]
        )

        filtered_issues = quality_issues
        if priority_filter == "High Priority":
            filtered_issues = [issue for issue in quality_issues if issue['Priority'] == 'High']
        elif priority_filter == "Medium Priority":
            filtered_issues = [issue for issue in quality_issues if issue['Priority'] == 'Medium']
        elif priority_filter == "Low Priority":
            filtered_issues = [issue for issue in quality_issues if issue['Priority'] == 'Low']

        # Quality issues table with priority highlighting
        st.subheader(f"Quality Issues by Task - {priority_filter}")
        quality_df = pd.DataFrame(filtered_issues)

        # Apply color coding to the dataframe
        def highlight_priority(val):
            if val == 'High':
                return 'background-color: #ffcccc; color: #cc0000; font-weight: bold;'
            elif val == 'Medium':
                return 'background-color: #fff2cc; color: #cc6600; font-weight: bold;'
            else:
                return 'background-color: #ccf2ff; color: #0066cc;'

        styled_df = quality_df.style.map(highlight_priority, subset=['Priority'])
        st.dataframe(styled_df, use_container_width=True)

        # Issues breakdown by priority
        st.subheader("Issues Breakdown by Priority")
        col1, col2 = st.columns(2)

        with col1:
            # Critical and Warning issues (high impact)
            high_impact_issues = []
            for issue in quality_issues:
                if issue['Priority'] in ['High', 'Medium']:
                    for individual_issue in issue['Issues'].split('; '):
                        if '🚨' in individual_issue or '⚠️' in individual_issue:
                            high_impact_issues.append(individual_issue.strip())

            if high_impact_issues:
                high_impact_counts = pd.Series(high_impact_issues).value_counts()
                fig = px.bar(
                    x=high_impact_counts.index,
                    y=high_impact_counts.values,
                    title='High Impact Issues (Critical & Warning)',
                    labels={'x': 'Issue Type', 'y': 'Count'},
                    color_discrete_sequence=['red', 'orange']
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Info issues (low impact)
            info_issues = []
            for issue in quality_issues:
                for individual_issue in issue['Issues'].split('; '):
                    if 'ℹ️' in individual_issue:
                        info_issues.append(individual_issue.strip())

            if info_issues:
                info_counts = pd.Series(info_issues).value_counts()
                fig2 = px.pie(
                    values=info_counts.values,
                    names=info_counts.index,
                    title='Information Issues (Low Impact)',
                    color_discrete_sequence=['lightblue', 'lightcyan', 'lightsteelblue']
                )
                st.plotly_chart(fig2, use_container_width=True)

        # Field-by-field quality breakdown
        st.subheader("🔍 Field-by-Field Quality Analysis")

        # Count issues by field type
        field_issues = {
            'Swimlane': 0,
            'Task Owner': 0,
            'Time Estimate': 0,
            'Cost per Hour': 0,
            'Task Status': 0,
            'Documentation Status': 0,
            'Documentation URL': 0,
            'Task Description': 0,
            'Tools Used': 0,
            'Opportunities': 0,
            'Issues Text': 0,
            'FAQ Knowledge': 0,
            'Industry Context': 0
        }

        for issue in quality_issues:
            issues_text = issue['Issues']
            if '🚨 Missing/Invalid Swimlane' in issues_text:
                field_issues['Swimlane'] += 1
            if '🚨 Missing Task Owner' in issues_text:
                field_issues['Task Owner'] += 1
            if '🚨 Missing Time Estimate' in issues_text:
                field_issues['Time Estimate'] += 1
            if '🚨 Missing Cost per Hour' in issues_text:
                field_issues['Cost per Hour'] += 1
            if '⚠️ Missing Task Status' in issues_text:
                field_issues['Task Status'] += 1
            if '⚠️ Missing Documentation Status' in issues_text:
                field_issues['Documentation Status'] += 1
            if '⚠️ Missing Documentation URL' in issues_text:
                field_issues['Documentation URL'] += 1
            if '⚠️ Missing Task Description' in issues_text:
                field_issues['Task Description'] += 1
            if 'ℹ️ Missing Tools Information' in issues_text:
                field_issues['Tools Used'] += 1
            if 'ℹ️ Missing Opportunities' in issues_text:
                field_issues['Opportunities'] += 1
            if 'ℹ️ Missing Issues Information' in issues_text:
                field_issues['Issues Text'] += 1
            if 'ℹ️ No FAQ Knowledge Captured' in issues_text or 'ℹ️ Incomplete FAQ' in issues_text:
                field_issues['FAQ Knowledge'] += 1
            if 'ℹ️ Missing Industry Context' in issues_text:
                field_issues['Industry Context'] += 1

        # Create field quality chart
        field_df = pd.DataFrame(list(field_issues.items()), columns=['Field', 'Issue Count'])
        field_df = field_df[field_df['Issue Count'] > 0].sort_values('Issue Count', ascending=False)

        if not field_df.empty:
            fig_field = px.bar(
                field_df,
                x='Field',
                y='Issue Count',
                title='Quality Issues by Field Type',
                color='Issue Count',
                color_continuous_scale='RdYlGn_r'
            )
            fig_field.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_field, use_container_width=True)

            # Show field quality table
            st.write("**Field Quality Breakdown:**")
            st.dataframe(field_df, use_container_width=True)

        # Issues by swimlane with priority breakdown
        st.subheader("Quality Issues by Department")
        swimlane_issues = {}
        for issue in quality_issues:
            swimlane = issue['Swimlane']
            if swimlane not in swimlane_issues:
                swimlane_issues[swimlane] = {
                    'task_count': 0,
                    'critical_issues': 0,
                    'warning_issues': 0,
                    'info_issues': 0,
                    'total_issues': 0
                }
            swimlane_issues[swimlane]['task_count'] += 1
            swimlane_issues[swimlane]['critical_issues'] += issue['Critical Issues']
            swimlane_issues[swimlane]['warning_issues'] += issue['Warning Issues']
            swimlane_issues[swimlane]['info_issues'] += issue['Info Issues']
            swimlane_issues[swimlane]['total_issues'] += issue['Total Issues']

        swimlane_issues_df = pd.DataFrame(swimlane_issues).T.reset_index()
        swimlane_issues_df.columns = ['Department', 'Tasks with Issues', 'Critical Issues', 'Warning Issues', 'Info Issues', 'Total Issues']

        # Create stacked bar chart showing priority breakdown
        fig2 = go.Figure()

        for swimlane in swimlane_issues_df['Department']:
            row = swimlane_issues_df[swimlane_issues_df['Department'] == swimlane].iloc[0]
            fig2.add_trace(go.Bar(
                name='Critical',
                x=[swimlane],
                y=[row['Critical Issues']],
                marker_color='red',
                hovertemplate='Critical: %{y}<extra></extra>'
            ))
            fig2.add_trace(go.Bar(
                name='Warning',
                x=[swimlane],
                y=[row['Warning Issues']],
                marker_color='orange',
                hovertemplate='Warning: %{y}<extra></extra>'
            ))
            fig2.add_trace(go.Bar(
                name='Info',
                x=[swimlane],
                y=[row['Info Issues']],
                marker_color='lightblue',
                hovertemplate='Info: %{y}<extra></extra>'
            ))

        fig2.update_layout(
            title='Quality Issues by Department (Priority Breakdown)',
            barmode='stack',
            xaxis_title='Department',
            yaxis_title='Number of Issues',
            showlegend=True
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Export quality issues
        st.subheader("Export Quality Issues")
        if st.button("📊 Export Quality Issues to Excel"):
            quality_filename = f"quality_control_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            quality_df.to_excel(quality_filename, index=False)
            st.success(f"✅ Quality issues exported to {quality_filename}")
            st.download_button(
                label="📥 Download Quality Report",
                data=open(quality_filename, 'rb').read(),
                file_name=quality_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.success("🎉 All tasks meet quality standards! No issues found.")

