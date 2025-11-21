"""
❓ Help & Guide page for BPMN Analysis app.
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
render_page_header("Help & Guide", "❓")

# Check if data is available
if not has_data():
    st.info("👆 Please upload BPMN XML files on the main page to start the analysis.")
else:
    # Get data from session state
    combined_tasks = get_combined_tasks()
    analysis_data = get_analysis_data()
    
    # Display subheader    # Header already rendered by render_page_header() above
    

    # Main help content
    st.markdown("""
    ## 🎯 **BPMN Analysis Tool - Complete User Guide**

    This tool is specifically designed to analyze BPMN (Business Process Model and Notation) files that use the **Inocta JSON template** in **Camunda** to extract, validate, and analyze business metadata for process optimization and documentation generation.
    """)

    # Getting Started Section
    with st.expander("🚀 **Getting Started**", expanded=True):
        st.markdown("""
        ### **1. Prepare Your BPMN Files**
        - Ensure your BPMN files use the **Inocta JSON template** structure
        - Files should be in `.xml` or `.bpmn` format
        - Upload files using the sidebar file uploader

        ### **2. Required Camunda Properties**
        Your BPMN tasks must include these properties for full analysis:

        | Property | Description | Example |
        |----------|-------------|---------|
        | `time_hhmm` | Time estimate in HH:MM format | `"2:30"` |
        | `cost_per_hour` | Labor cost per hour | `150` |
        | `currency` | Cost currency | `"USD"`, `"CAD"`, `"EUR"` |
        | `task_owner` | Person responsible | `"John Smith"` |
        | `task_status` | Current status | `"In Progress"`, `"Completed"` |
        | `swimlane` | Department/team | `"Marketing"`, `"IT"` |
        | `task_description` | Task details | `"Review and approve content"` |

        ### **3. Optional Enhanced Properties**
        For advanced analysis, include these additional properties:

        | Property | Description | Example |
        |----------|-------------|---------|
        | `doc_status` | Documentation status | `"Complete"`, `"In Progress"`, `"Not Needed"` |
        | `doc_url` | Documentation link | `"https://wiki.company.com/task-docs"` |
        | `tools_used` | Tools and systems | `"Excel, CRM, Email"` |
        | `opportunities` | Improvement ideas | `"Automate repetitive steps"` |
        | `issues_text` | Problems/risks | `"Manual process prone to errors"` |
        | `issues_priority` | Issue priority | `"High"`, `"Medium"`, `"Low"` |
        | `faq_q1`, `faq_a1` | FAQ knowledge | `"How to handle exceptions?"` |
        | `task_industry` | Industry context | `"Healthcare"`, `"Finance"` |
        """)

    # Features Overview Section
    with st.expander("🔍 **Core Features Overview**", expanded=True):
        st.markdown("""
        ### **📋 Tasks Overview Table**
        - **Comprehensive task display** with all metadata
        - **Smart filtering** by department, owner, status, and documentation
        - **Documentation tracking** with visual indicators and clickable URLs
        - **Real-time statistics** on task coverage and costs

        ### **📊 Status Analysis**
        - **Task status distribution** with pie charts and visual indicators
        - **Attention tracking** for tasks requiring immediate action
        - **Progress monitoring** across all process stages

        ### **📚 Documentation Status Analysis**
        - **State of the nation** view for documentation coverage
        - **Schema-aligned statuses** matching your Inocta template
        - **Action item identification** for missing documentation
        - **Coverage metrics** and compliance tracking

        ### **🔧 Tools Analysis**
        - **Tool usage patterns** across all processes
        - **Data cleaning recommendations** for inconsistent entries
        - **Task breakdown** by tool with detailed analysis
        - **Standardization guidance** for better data quality

        ### **✅ Quality Control**
        - **Data validation** with priority classification
        - **Missing information detection** (Critical, Warning, Info)
        - **Quality scoring** and compliance percentages
        - **Improvement recommendations** for data completeness

        ### **💾 Export Data & Reports**
        - **Multi-format exports**: Excel, CSV, JSON, Markdown
        - **Focused exports**: Tasks only, Issues & Opportunities, FAQ Knowledge
        - **AI-ready data** for documentation generation
        - **Comprehensive analysis** with all insights and metrics
        """)

    # Inocta Template Integration Section
    with st.expander("🔗 **Inocta JSON Template Integration**", expanded=True):
        st.markdown("""
        ### **📋 Template Structure**
        This tool is specifically designed to work with the **Inocta JSON template** structure used in Camunda:

        ```json
        {
          "properties": {
            "time_hhmm": "2:30",
            "cost_per_hour": 150,
            "currency": "USD",
            "task_owner": "John Smith",
            "task_status": "In Progress",
            "doc_status": "Documentation In Progress",
            "doc_url": "https://docs.company.com/task-123",
            "tools_used": "Excel, CRM, Email",
            "opportunities": "Automate manual steps",
            "issues_text": "Process takes too long",
            "issues_priority": "Medium",
            "faq_q1": "What if the process fails?",
            "faq_a1": "Follow escalation procedure in SOP-001",
            "task_industry": "Healthcare"
          }
        }
        ```

        ### **🎯 Template Benefits**
        - **Standardized metadata** across all processes
        - **Consistent analysis** and reporting
        - **Easy integration** with existing Camunda workflows
        - **Scalable approach** for enterprise process management
        """)

    # AI Documentation Generation Section
    with st.expander("🤖 **AI Documentation Generation**", expanded=True):
        st.markdown("""
        ### **📚 Export Data for AI Agents**
        The export functionality provides **AI-ready data** that can be used to generate various types of documentation:

        #### **📋 Standard Operating Procedures (SOPs)**
        - **Task sequences** and dependencies
        - **Time estimates** and resource requirements
        - **Tools and systems** used in each step
        - **Quality control** checkpoints and validation rules

        #### **🔍 SWOT Analysis**
        - **Strengths**: Well-documented processes, efficient tools
        - **Weaknesses**: Missing documentation, inconsistent data
        - **Opportunities**: Automation potential, process improvements
        - **Threats**: Quality issues, compliance gaps

        #### **❓ FAQ Documentation**
        - **Common questions** extracted from task metadata
        - **Standard answers** for process guidance
        - **Knowledge base** for training and reference
        - **Troubleshooting** guides for common issues

        #### **📊 Process Documentation**
        - **Process maps** with detailed task information
        - **Resource allocation** and cost analysis
        - **Timeline estimates** and critical path analysis
        - **Risk assessment** and mitigation strategies

        ### **🚀 AI Integration Workflow**
        1. **Export data** from BPMN Analysis tool
        2. **Feed to AI agent** (ChatGPT, Claude, etc.)
        3. **Generate documentation** using AI prompts
        4. **Review and refine** generated content
        5. **Publish and maintain** documentation

        ### **💡 AI Prompt Examples**

        **For SOP Generation:**
        ```
        Using this BPMN process data, create a comprehensive Standard Operating Procedure (SOP) that includes:
        - Step-by-step process flow
        - Required tools and resources
        - Time estimates and dependencies
        - Quality control checkpoints
        - Troubleshooting guidelines
        ```

        **For SWOT Analysis:**
        ```
        Analyze this BPMN process data to create a SWOT analysis covering:
        - Process strengths and efficiencies
        - Areas for improvement and weaknesses
        - Opportunities for optimization
        - Potential risks and threats
        ```

        **For FAQ Generation:**
        ```
        Based on this process data, generate a comprehensive FAQ covering:
        - Common process questions
        - Troubleshooting scenarios
        - Best practices and tips
        - Escalation procedures
        ```
        """)

    # Best Practices Section
    with st.expander("⭐ **Best Practices & Tips**", expanded=True):
        st.markdown("""
        ### **📝 Data Quality Best Practices**

        #### **1. Consistent Naming Conventions**
        - Use **standardized department names** (e.g., "Marketing", "IT", "Finance")
        - Maintain **consistent task status values** across all processes
        - Use **clear, descriptive task names** that explain the purpose

        #### **2. Complete Metadata**
        - **Always include** time estimates and cost information
        - **Document all tools** used in each task
        - **Capture opportunities** and issues for continuous improvement
        - **Maintain FAQ knowledge** for knowledge transfer

        #### **3. Regular Updates**
        - **Review and update** process metadata quarterly
        - **Validate costs** and time estimates annually
        - **Update documentation** status as processes evolve
        - **Refresh FAQ content** based on user feedback

        ### **🔧 Tool Usage Tips**

        #### **1. Start with Overview**
        - Begin with **Tasks Overview** to understand your data
        - Use **filters** to focus on specific departments or owners
        - Check **documentation coverage** to identify gaps

        #### **2. Quality Assessment**
        - Run **Quality Control** to identify data issues
        - Address **critical issues** first (missing owners, costs, times)
        - Use **warning issues** to improve data completeness

        #### **3. Export Strategy**
        - **Export complete analysis** for comprehensive reviews
        - Use **focused exports** for specific stakeholders
        - **JSON exports** are ideal for AI integration
        - **Excel exports** work best for business reviews
        """)

    # Troubleshooting Section
    with st.expander("🛠️ **Troubleshooting & Support**", expanded=True):
        st.markdown("""
        ### **❌ Common Issues & Solutions**

        #### **1. File Upload Problems**
        - **Issue**: File not uploading
        - **Solution**: Ensure file is `.xml` or `.bpmn` format, check file size

        #### **2. Missing Data**
        - **Issue**: Tasks showing "Unknown" or missing information
        - **Solution**: Check BPMN file for required Camunda properties

        #### **3. Export Errors**
        - **Issue**: Export fails or generates incomplete files
        - **Solution**: Verify data completeness, check file permissions

        #### **4. Performance Issues**
        - **Issue**: App runs slowly with large files
        - **Solution**: Break large processes into smaller files, optimize metadata

        ### **📞 Getting Help**
        - **GitHub Issues**: Report bugs and request features
        - **Documentation**: Check this help guide first
        - **Community**: Share experiences and best practices
        - **Support**: Contact the development team for technical issues
        """)

    # Footer
    st.markdown("---")
    st.markdown("""
    **💡 Pro Tip**: Use the **Export Data** tab to generate AI-ready data for creating comprehensive documentation, 
    including SOPs, SWOT analysis, and FAQ guides. The structured export format is perfect for AI agent integration!
    """)
    st.markdown("""
    This tool expects BPMN files with the following structure:

    - **Processes**: Business processes with tasks and activities
    - **Tasks**: Individual work items with metadata
    - **Camunda Properties**: Business metadata including:
    - `time_hhmm`: Time estimate (HH:MM format)
    - `cost_per_hour`: Labor cost per hour
    - `currency`: Currency for costs
    - `task_owner`: Person responsible for the task
    - `task_status`: Current status of the task
    - `issues_priority`: Priority level for issues
    - `opportunities`: Improvement opportunities
    - `tools_used`: Tools and systems used

    **Supported File Types:**
    - XML files (.xml)
    - BPMN files (.bpmn)
    """)

