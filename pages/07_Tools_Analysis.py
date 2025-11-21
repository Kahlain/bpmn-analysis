"""
Tools Analysis page for BPMN Analysis app.
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
render_page_header("Tools Analysis", "🔧")

# Check if data is available
if not has_data():
    st.info("👆 Please upload BPMN XML files on the main page to start the analysis.")
else:
    # Get data from session state
    combined_tasks = get_combined_tasks()
    analysis_data = get_analysis_data()
    
    # Display subheader    # Header already rendered by render_page_header() above
    

    # Group by tools used with enhanced cleanup
    tools_analysis = {}
    tool_to_tasks = {}  # Track which tasks use each tool

    for task in combined_tasks:
        tools = task.get('tools_used', '')
        if tools and tools.strip():
            # Split tools by comma and semicolon, then clean each tool name
            tool_list = []
            # First split by semicolon if present
            if ';' in tools:
                tool_list = [tool.strip() for tool in tools.split(';') if tool.strip()]
            else:
                # Split by comma if no semicolon
                tool_list = [tool.strip() for tool in tools.split(',') if tool.strip()]

            # Clean and normalize tool names with better deduplication
            cleaned_tools = []
            for tool in tool_list:
                # Remove common prefixes/suffixes and normalize
                cleaned_tool = tool.strip()
                if cleaned_tool:
                    # Handle special cases like "Outlook et Prextra" -> split into separate tools
                    if ' et ' in cleaned_tool:
                        sub_tools = [t.strip() for t in cleaned_tool.split(' et ')]
                        cleaned_tools.extend(sub_tools)
                    else:
                        # Additional cleanup for common mistakes
                        cleaned_tool = cleaned_tool.replace('  ', ' ')  # Remove double spaces
                        cleaned_tool = cleaned_tool.replace('Microsoft ', '')  # Remove Microsoft prefix
                        cleaned_tool = cleaned_tool.replace('MS ', '')  # Remove MS prefix
                        cleaned_tool = cleaned_tool.replace('Office ', '')  # Remove Office prefix

                        # Handle common variations
                        if cleaned_tool.lower() in ['teams', 'microsoft teams', 'ms teams']:
                            cleaned_tool = 'Teams'
                        elif cleaned_tool.lower() in ['excel', 'microsoft excel', 'ms excel']:
                            cleaned_tool = 'Excel'
                        elif cleaned_tool.lower() in ['outlook', 'microsoft outlook', 'ms outlook']:
                            cleaned_tool = 'Outlook'
                        elif cleaned_tool.lower() in ['word', 'microsoft word', 'ms word']:
                            cleaned_tool = 'Word'
                        elif cleaned_tool.lower() in ['powerpoint', 'microsoft powerpoint', 'ms powerpoint']:
                            cleaned_tool = 'PowerPoint'
                        elif cleaned_tool.lower() in ['planner', 'microsoft planner', 'ms planner']:
                            cleaned_tool = 'Planner'

                        cleaned_tools.append(cleaned_tool)

            # Remove duplicates from cleaned tools
            cleaned_tools = list(dict.fromkeys(cleaned_tools))  # Preserve order while removing duplicates

            # Analyze each individual tool
            for tool in cleaned_tools:
                if tool not in tools_analysis:
                    tools_analysis[tool] = {
                        'task_count': 0,
                        'total_cost': 0,
                        'total_time_minutes': 0,
                        'swimlanes': set(),
                        'owners': set(),
                        'original_combinations': set(),  # Track original tool combinations
                        'task_names': []  # Track task names for this tool
                    }

                tools_analysis[tool]['task_count'] += 1
                tools_analysis[tool]['total_cost'] += task.get('total_cost', 0)
                tools_analysis[tool]['total_time_minutes'] += task.get('time_minutes', 0)
                tools_analysis[tool]['swimlanes'].add(task.get('swimlane', 'Unknown'))
                tools_analysis[tool]['owners'].add(task.get('task_owner', 'Unknown'))
                tools_analysis[tool]['original_combinations'].add(tools)  # Keep original combination
                tools_analysis[tool]['task_names'].append(task.get('name', 'Unknown Task'))

                # Track tool to tasks mapping
                if tool not in tool_to_tasks:
                    tool_to_tasks[tool] = []
                tool_to_tasks[tool].append({
                    'task_name': task.get('name', 'Unknown Task'),
                    'swimlane': task.get('swimlane', 'Unknown'),
                    'task_owner': task.get('task_owner', 'Unknown'),
                    'time_display': task.get('time_display', '00:00'),
                    'total_cost': task.get('total_cost', 0),
                    'currency': task.get('currency', 'Unknown'),
                    'original_tools': tools  # Keep original tools field for reference
                })

    if tools_analysis:
        # Convert sets to lists for display
        for tool in tools_analysis:
            tools_analysis[tool]['swimlanes'] = list(tools_analysis[tool]['swimlanes'])
            tools_analysis[tool]['owners'] = list(tools_analysis[tool]['owners'])

        # Create tools analysis dataframe
        tools_df = pd.DataFrame(tools_analysis).T.reset_index()
        # Rename columns to match expected structure
        tools_df.columns = ['Tool', 'Task Count', 'Total Cost', 'total_time_minutes', 'Swimlanes', 'Owners', 'Original Combinations', 'Task Names']
        # Calculate hours from minutes
        tools_df['Total Time (hrs)'] = tools_df['total_time_minutes'] / 60
        # Rename the minutes column for display
        tools_df = tools_df.rename(columns={'total_time_minutes': 'Total Time (min)'})
        tools_df['Avg Cost per Task'] = tools_df['Total Cost'] / tools_df['Task Count']

        # Clean up the task names for better display (limit to first 3 and show count)
        def format_task_names(task_names):
            if len(task_names) <= 3:
                return ', '.join(task_names)
            else:
                return f"{', '.join(task_names[:3])}... (+{len(task_names)-3} more)"

        tools_df['Task Names'] = tools_df['Task Names'].apply(format_task_names)

        # Clean the data to ensure numeric values
        tools_df = tools_df.fillna(0)
        tools_df['Total Time (hrs)'] = pd.to_numeric(tools_df['Total Time (hrs)'], errors='coerce').fillna(0)
        tools_df['Total Cost'] = pd.to_numeric(tools_df['Total Cost'], errors='coerce').fillna(0)
        tools_df['Task Count'] = pd.to_numeric(tools_df['Task Count'], errors='coerce').fillna(0)

        # Key Metrics - Standardized layout
        total_tools = len(tools_df)
        total_tasks = tools_df['Task Count'].sum()
        total_cost = tools_df['Total Cost'].sum()
        total_time = tools_df['Total Time (hrs)'].sum()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Tools", total_tools)
        with col2:
            st.metric("Total Tasks", f"{total_tasks:,}")
        with col3:
            st.metric("Total Cost", f"${total_cost:,.2f}")
        with col4:
            st.metric("Total Time", f"{total_time:.1f} hrs")
        
        st.markdown("---")

        # Display enhanced tools analysis
        st.markdown("**📊 Tools Analysis Table**")
        st.dataframe(tools_df, use_container_width=True)

        # Add detailed task breakdown for each tool
        st.markdown("---")
        st.subheader("🔍 Detailed Task Breakdown by Tool")

        # Create expandable sections for each tool
        for tool_name, tool_data in tools_analysis.items():
            with st.expander(f"📱 {tool_name} - {tool_data['task_count']} tasks"):
                # Create detailed dataframe for this tool
                tool_tasks_df = pd.DataFrame(tool_data['task_names'], columns=['Task Name'])

                # Add additional columns from tool_to_tasks
                if tool_name in tool_to_tasks:
                    tool_tasks_df = pd.DataFrame(tool_to_tasks[tool_name])
                    # Reorder columns for better display
                    display_columns = ['task_name', 'swimlane', 'task_owner', 'time_display', 'total_cost', 'currency', 'original_tools']
                    available_columns = [col for col in display_columns if col in tool_tasks_df.columns]

                    st.dataframe(
                        tool_tasks_df[available_columns],
                        use_container_width=True,
                        column_config={
                            "task_name": st.column_config.TextColumn(
                                "Task Name",
                                help="Name of the task using this tool",
                                max_chars=50
                            ),
                            "original_tools": st.column_config.TextColumn(
                                "Original Tools Field",
                                help="Original tools field from BPMN (for cleanup reference)",
                                max_chars=80
                            )
                        }
                    )

                    # Show summary metrics for this tool
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Tasks", tool_data['task_count'])
                    with col2:
                        st.metric("Total Cost", f"${tool_data['total_cost']:,.2f}")
                    with col3:
                        st.metric("Total Time", f"{tool_data['total_time_minutes']/60:.1f} hrs")
                    with col4:
                        st.metric("Avg Cost/Task", f"${tool_data['total_cost']/tool_data['task_count']:,.2f}")
                else:
                    st.write("No detailed task information available for this tool.")

        # Show cleanup recommendations
        st.markdown("---")
        st.subheader("🧹 Tool Cleanup Recommendations")

        # Identify potential cleanup opportunities
        cleanup_opportunities = []
        for tool_name, tool_data in tools_analysis.items():
            original_combinations = list(tool_data['original_combinations'])
            if len(original_combinations) > 1:
                # Multiple different combinations for the same tool
                cleanup_opportunities.append({
                    'Tool': tool_name,
                    'Current Combinations': len(original_combinations),
                    'Examples': ', '.join(original_combinations[:3]) + ('...' if len(original_combinations) > 3 else ''),
                    'Recommendation': f"Standardize to '{tool_name}' across all tasks"
                })

        if cleanup_opportunities:
            cleanup_df = pd.DataFrame(cleanup_opportunities)
            st.dataframe(cleanup_df, use_container_width=True)
            st.info("💡 **Recommendation**: Standardize tool names in your BPMN files to improve analysis accuracy and reduce duplicates.")
        else:
            st.success("✅ **Great job!** All tool names are properly standardized.")

        # Show tool combinations analysis
        st.subheader("🔗 Tool Combinations Analysis")
        combination_analysis = {}
        for task in combined_tasks:
            tools = task.get('tools_used', '')
            if tools and tools.strip():
                if tools not in combination_analysis:
                    combination_analysis[tools] = {
                        'task_count': 0,
                        'total_cost': 0,
                        'total_time_minutes': 0,
                        'swimlanes': set(),
                        'owners': set()
                    }

                combination_analysis[tools]['task_count'] += 1
                combination_analysis[tools]['total_cost'] += task.get('total_cost', 0)
                combination_analysis[tools]['total_time_minutes'] += task.get('time_minutes', 0)
                combination_analysis[tools]['swimlanes'].add(task.get('swimlane', 'Unknown'))
                combination_analysis[tools]['owners'].add(task.get('task_owner', 'Unknown'))

        if combination_analysis:
            # Convert sets to lists for display
            for combo in combination_analysis:
                combination_analysis[combo]['swimlanes'] = list(combination_analysis[combo]['swimlanes'])
                combination_analysis[combo]['owners'] = list(combination_analysis[combo]['owners'])

            combo_df = pd.DataFrame(combination_analysis).T.reset_index()
            # Rename columns to match expected structure
            combo_df.columns = ['Tool Combination', 'Task Count', 'Total Cost', 'total_time_minutes', 'Swimlanes', 'Owners']
            # Calculate hours from minutes
            combo_df['Total Time (hrs)'] = combo_df['total_time_minutes'] / 60
            # Rename the minutes column for display
            combo_df = combo_df.rename(columns={'total_time_minutes': 'Total Time (min)'})
            combo_df['Avg Cost per Task'] = combo_df['Total Cost'] / combo_df['Task Count']

            st.dataframe(combo_df, use_container_width=True)

        # Tools usage chart
        fig = px.bar(
            tools_df,
            x='Tool',
            y='Task Count',
            title='Tool Usage by Task Count',
            color='Total Cost',
            color_continuous_scale='viridis'
        )
        st.plotly_chart(fig, use_container_width=True)

        # Tools cost efficiency chart
        try:
            # Ensure we have valid numeric data for the scatter plot
            scatter_data = tools_df.copy()
            scatter_data = scatter_data[scatter_data['Total Time (hrs)'] > 0]  # Filter out zero values

            if len(scatter_data) > 0:
                fig2 = px.scatter(
                    scatter_data,
                    x='Task Count',
                    y='Total Cost',
                    size=scatter_data['Total Time (hrs)'].values,
                    color='Tool',
                    title='Tools: Cost vs Task Count vs Time',
                    hover_data=['Avg Cost per Task']
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No valid data available for scatter plot (all time values are zero)")
        except Exception as e:
            st.warning(f"Could not create scatter plot: {str(e)}")
            st.info("Displaying tools data in table format instead")

        # Tools by swimlane
        st.subheader("Tools Usage by Department")
        tools_swimlane_data = []
        for tool, data in tools_analysis.items():
            for swimlane in data['swimlanes']:
                tools_swimlane_data.append({
                    'Tool': tool,
                    'Swimlane': swimlane,
                    'Task Count': data['task_count'],
                    'Total Cost': data['total_cost']
                })

        if tools_swimlane_data:
            tools_swimlane_df = pd.DataFrame(tools_swimlane_data)
            pivot_data = tools_swimlane_df.pivot_table(
                index='Swimlane', 
                columns='Tool', 
                values='Task Count', 
                aggfunc='sum'
            ).fillna(0)

            # Use plotly.graph_objects for heatmap
            import plotly.graph_objects as go
            fig3 = go.Figure(data=go.Heatmap(
                z=pivot_data.values,
                x=pivot_data.columns,
                y=pivot_data.index,
                colorscale='viridis',
                text=pivot_data.values,
                texttemplate="%{text}",
                textfont={"size": 10},
                hoverongaps=False
            ))
            fig3.update_layout(
                title='Tools Usage Heatmap by Department',
                xaxis_title='Tools',
                yaxis_title='Departments'
            )
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No tools information found in the uploaded BPMN files.")

