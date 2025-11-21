"""
Shared utilities for BPMN Analysis app.
Provides session state management and common functions for all pages.
"""
import streamlit as st
from typing import Dict, List, Any, Optional


# Inocta Branding Constants
INOCTA_LOGO_WHITE_URL = "https://inocta.io/wp-content/uploads/2025/03/inocta-logo-primary-white-rgb-4090px-w-72ppi.png"
INOCTA_LOGO_URL = "https://inocta.io/wp-content/uploads/2024/06/inocta-logo-secondary-full-color-rgb-4090px-w-72ppi.png"
INOCTA_COLORS = {
    'slate': '#43505B',
    'deep_teal': '#50817C',
    'terracotta': '#CE8365',
    'warm_sand': '#E0A967',
    'off_white': '#F3F4EF',
    'light_slate': '#99A0A4',
    'light_teal': '#87ADA2',
    'beige': '#D5BA98',
    'dark_grey': '#2C3E50',
    'text': '#080808',
    'danger': '#962531',
    'warning': '#D18F33',
    'success': '#4A7C59'
}
APP_VERSION = "v3.5.0"
APP_NAME = "Inocta BPM Analysis"


def init_session_state():
    """Initialize session state variables if they don't exist."""
    if 'analyzer' not in st.session_state:
        # Import here to avoid circular imports
        from bpmn_analyzer import BPMNAnalyzer
        st.session_state.analyzer = BPMNAnalyzer()
    
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = None
    
    if 'all_analysis_data' not in st.session_state:
        st.session_state.all_analysis_data = []
    
    if 'combined_tasks' not in st.session_state:
        st.session_state.combined_tasks = []
    
    if 'analysis_data' not in st.session_state:
        st.session_state.analysis_data = {}


def setup_file_upload():
    """Set up file upload section in sidebar - available on all pages."""
    # Initialize session state
    init_session_state()
    
    # Get analyzer instance
    analyzer = get_analyzer()
    
    # File upload in sidebar - Streamlit-native
    st.sidebar.header("📁 File Upload")
    
    # Check if we already have files in session state
    has_stored_files = (st.session_state.uploaded_files is not None and 
                       hasattr(st.session_state.uploaded_files, '__len__') and 
                       len(st.session_state.uploaded_files) > 0)
    
    # Also check if we have analysis data (more reliable indicator)
    has_analysis_data = (st.session_state.all_analysis_data is not None and 
                        len(st.session_state.all_analysis_data) > 0)
    
    # File uploader - this will return None when navigating between pages
    uploaded_files = st.sidebar.file_uploader(
        "Upload BPMN XML files",
        type=['xml', 'bpmn'],
        accept_multiple_files=True,
        help="Upload one or more BPMN XML files for analysis",
        key="file_uploader_sidebar"
    )
    
    # Process files if new files uploaded
    if uploaded_files:
        # Check if files have changed (new upload)
        current_files = [f.name for f in uploaded_files]
        stored_files = [f.name for f in st.session_state.uploaded_files] if st.session_state.uploaded_files else []
        
        if current_files != stored_files:
            st.sidebar.success(f"✅ {len(uploaded_files)} file(s) uploaded")
            
            # Process uploaded files
            all_analysis_data = process_uploaded_files(analyzer, uploaded_files)
            
            # Update session state with analysis data
            if all_analysis_data:
                update_analysis_data(uploaded_files, all_analysis_data)
                
                # Auto-redirect to Executive Summary page after successful upload
                st.session_state.auto_redirect_to_exec = True
        
        # Show uploaded files list
        if st.session_state.uploaded_files:
            st.sidebar.markdown("**Uploaded Files:**")
            for file in st.session_state.uploaded_files:
                st.sidebar.write(f"📄 {file.name}")
    elif has_stored_files or has_analysis_data:
        # We have files/data in session state but file_uploader returned None (page navigation)
        # Keep the existing files and data - don't clear them!
        if has_stored_files:
            st.sidebar.info(f"📄 {len(st.session_state.uploaded_files)} file(s) loaded")
            st.sidebar.markdown("**Uploaded Files:**")
            for file in st.session_state.uploaded_files:
                st.sidebar.write(f"📄 {file.name}")
        elif has_analysis_data:
            # Show file count from analysis data if we don't have file objects
            file_count = len(st.session_state.all_analysis_data)
            st.sidebar.info(f"📄 {file_count} file(s) loaded")
            st.sidebar.markdown("**Uploaded Files:**")
            for data in st.session_state.all_analysis_data:
                filename = data.get('filename', 'Unknown')
                st.sidebar.write(f"📄 {filename}")
        
        # Add a button to clear files
        if st.sidebar.button("🗑️ Clear Files", key="clear_files_btn_sidebar"):
            st.session_state.uploaded_files = None
            st.session_state.all_analysis_data = []
            st.session_state.combined_tasks = []
            st.session_state.analysis_data = {}
            st.rerun()
    else:
        # No files in session state and no new uploads - this is the initial state
        pass


def setup_file_upload_main():
    """Set up file upload section on main page content area (not sidebar)."""
    # Initialize session state
    init_session_state()
    
    # Get analyzer instance
    analyzer = get_analyzer()
    
    # File upload in main content area - Streamlit-native
    st.markdown("---")
    st.markdown("### 📁 File Upload")
    
    # Check if we already have files in session state
    has_stored_files = (st.session_state.uploaded_files is not None and 
                       hasattr(st.session_state.uploaded_files, '__len__') and 
                       len(st.session_state.uploaded_files) > 0)
    
    # Also check if we have analysis data (more reliable indicator)
    has_analysis_data = (st.session_state.all_analysis_data is not None and 
                        len(st.session_state.all_analysis_data) > 0)
    
    # File uploader - this will return None when navigating between pages
    uploaded_files = st.file_uploader(
        "Upload BPMN XML files",
        type=['xml', 'bpmn'],
        accept_multiple_files=True,
        help="Upload one or more BPMN XML files for analysis",
        key="file_uploader_main"
    )
    
    # Process files if new files uploaded
    if uploaded_files:
        # Check if files have changed (new upload)
        current_files = [f.name for f in uploaded_files]
        stored_files = [f.name for f in st.session_state.uploaded_files] if st.session_state.uploaded_files else []
        
        if current_files != stored_files:
            st.success(f"✅ {len(uploaded_files)} file(s) uploaded")
            
            # Process uploaded files
            all_analysis_data = process_uploaded_files(analyzer, uploaded_files)
            
            # Update session state with analysis data
            if all_analysis_data:
                update_analysis_data(uploaded_files, all_analysis_data)
                
                # Auto-redirect to Executive Summary page after successful upload
                st.session_state.auto_redirect_to_exec = True
        
        # Show uploaded files list
        if st.session_state.uploaded_files:
            st.markdown("**📄 Uploaded Files:**")
            file_col1, file_col2 = st.columns([3, 1])
            with file_col1:
                for file in st.session_state.uploaded_files:
                    st.write(f"📄 {file.name}")
            with file_col2:
                if st.button("🗑️ Clear Files", key="clear_files_btn", type="secondary"):
                    st.session_state.uploaded_files = None
                    st.session_state.all_analysis_data = []
                    st.session_state.combined_tasks = []
                    st.session_state.analysis_data = {}
                    st.rerun()
    elif has_stored_files or has_analysis_data:
        # We have files/data in session state but file_uploader returned None (page navigation)
        # Keep the existing files and data - don't clear them!
        if has_stored_files:
            st.info(f"📄 {len(st.session_state.uploaded_files)} file(s) loaded")
            st.markdown("**📄 Uploaded Files:**")
            file_col1, file_col2 = st.columns([3, 1])
            with file_col1:
                for file in st.session_state.uploaded_files:
                    st.write(f"📄 {file.name}")
            with file_col2:
                if st.button("🗑️ Clear Files", key="clear_files_btn", type="secondary"):
                    st.session_state.uploaded_files = None
                    st.session_state.all_analysis_data = []
                    st.session_state.combined_tasks = []
                    st.session_state.analysis_data = {}
                    st.rerun()
        elif has_analysis_data:
            # Show file count from analysis data if we don't have file objects
            file_count = len(st.session_state.all_analysis_data)
            st.info(f"📄 {file_count} file(s) loaded")
            st.markdown("**📄 Uploaded Files:**")
            file_col1, file_col2 = st.columns([3, 1])
            with file_col1:
                for data in st.session_state.all_analysis_data:
                    filename = data.get('filename', 'Unknown')
                    st.write(f"📄 {filename}")
            with file_col2:
                if st.button("🗑️ Clear Files", key="clear_files_btn", type="secondary"):
                    st.session_state.uploaded_files = None
                    st.session_state.all_analysis_data = []
                    st.session_state.combined_tasks = []
                    st.session_state.analysis_data = {}
                    st.rerun()
    else:
        # No files in session state and no new uploads - this is the initial state
        pass


def get_analyzer():
    """Get or create BPMNAnalyzer instance from session state."""
    init_session_state()
    return st.session_state.analyzer


def process_uploaded_files(analyzer, uploaded_files: List) -> List[Dict[str, Any]]:
    """
    Process uploaded BPMN files and return analysis data.
    
    Args:
        analyzer: BPMNAnalyzer instance
        uploaded_files: List of uploaded file objects
        
    Returns:
        List of analysis data dictionaries
    """
    all_analysis_data = []
    
    for uploaded_file in uploaded_files:
        st.write(f"📄 {uploaded_file.name}")
        
        # Read file content
        file_content = uploaded_file.read().decode('utf-8')
        
        # Parse BPMN file
        with st.spinner(f"Analyzing {uploaded_file.name}..."):
            parsed_data = analyzer.parse_bpmn_file(file_content)
            
            if parsed_data:
                # Analyze business insights
                analysis_data = analyzer.analyze_business_insights(parsed_data)
                analysis_data['filename'] = uploaded_file.name
                all_analysis_data.append(analysis_data)
                
                # Show success with task count
                task_count = len(parsed_data.get('tasks', []))
                st.success(f"✅ Successfully analyzed {uploaded_file.name} - Found {task_count} tasks")
            else:
                st.error(f"❌ Failed to analyze {uploaded_file.name}")
    
    return all_analysis_data


def update_analysis_data(uploaded_files: List, all_analysis_data: List[Dict[str, Any]]):
    """
    Update session state with uploaded files and analysis data.
    Also computes combined_tasks and merged analysis_data.
    
    Args:
        uploaded_files: List of uploaded file objects
        all_analysis_data: List of analysis data dictionaries
    """
    st.session_state.uploaded_files = uploaded_files
    st.session_state.all_analysis_data = all_analysis_data
    
    # Combine all tasks from all files
    combined_tasks = []
    for data in all_analysis_data:
        tasks = data.get('tasks', [])
        if tasks:  # Only extend if tasks exist
            combined_tasks.extend(tasks)
    st.session_state.combined_tasks = combined_tasks
    
    # Merge all analysis data for combined view
    if all_analysis_data:
        merged_analysis = {
            'summary': {
                'total_tasks': len(combined_tasks),
                'total_cost': sum(task.get('total_cost', 0) for task in combined_tasks),
                'total_time_minutes': sum(task.get('time_minutes', 0) for task in combined_tasks),
                'total_time_hours': sum(task.get('time_hours', 0) for task in combined_tasks),
                'currencies': list(set(task.get('currency', 'Unknown') for task in combined_tasks if task.get('currency')))
            },
            'swimlane_analysis': {},
            'owner_analysis': {},
            'status_analysis': {},
            'priority_analysis': {},
            'doc_status_analysis': {},
            'tasks': combined_tasks
        }
        
        # Merge swimlane analysis
        for data in all_analysis_data:
            for swimlane, info in data.get('swimlane_analysis', {}).items():
                if swimlane not in merged_analysis['swimlane_analysis']:
                    merged_analysis['swimlane_analysis'][swimlane] = {
                        'task_count': 0,
                        'total_cost': 0,
                        'total_time_minutes': 0,
                        'total_time_hours': 0,
                        'tasks': []
                    }
                merged_analysis['swimlane_analysis'][swimlane]['task_count'] += info.get('task_count', 0)
                merged_analysis['swimlane_analysis'][swimlane]['total_cost'] += info.get('total_cost', 0)
                merged_analysis['swimlane_analysis'][swimlane]['total_time_minutes'] += info.get('total_time_minutes', 0)
                merged_analysis['swimlane_analysis'][swimlane]['total_time_hours'] += info.get('total_time_hours', 0)
                merged_analysis['swimlane_analysis'][swimlane]['tasks'].extend(info.get('tasks', []))
        
        # Merge owner analysis
        for data in all_analysis_data:
            for owner, info in data.get('owner_analysis', {}).items():
                if owner not in merged_analysis['owner_analysis']:
                    merged_analysis['owner_analysis'][owner] = {
                        'task_count': 0,
                        'total_cost': 0,
                        'total_time_minutes': 0
                    }
                merged_analysis['owner_analysis'][owner]['task_count'] += info.get('task_count', 0)
                merged_analysis['owner_analysis'][owner]['total_cost'] += info.get('total_cost', 0)
                merged_analysis['owner_analysis'][owner]['total_time_minutes'] += info.get('total_time_minutes', 0)
        
        # Merge status analysis
        for data in all_analysis_data:
            for status, info in data.get('status_analysis', {}).items():
                if status not in merged_analysis['status_analysis']:
                    merged_analysis['status_analysis'][status] = {
                        'task_count': 0,
                        'total_cost': 0,
                        'total_time_minutes': 0
                    }
                merged_analysis['status_analysis'][status]['task_count'] += info.get('task_count', 0)
                merged_analysis['status_analysis'][status]['total_cost'] += info.get('total_cost', 0)
                merged_analysis['status_analysis'][status]['total_time_minutes'] += info.get('total_time_minutes', 0)
        
        # Merge priority analysis
        for data in all_analysis_data:
            for priority, info in data.get('priority_analysis', {}).items():
                if priority not in merged_analysis['priority_analysis']:
                    merged_analysis['priority_analysis'][priority] = {
                        'task_count': 0,
                        'total_cost': 0,
                        'total_time_minutes': 0
                    }
                merged_analysis['priority_analysis'][priority]['task_count'] += info.get('task_count', 0)
                merged_analysis['priority_analysis'][priority]['total_cost'] += info.get('total_cost', 0)
                merged_analysis['priority_analysis'][priority]['total_time_minutes'] += info.get('total_time_minutes', 0)
        
        # Merge doc_status analysis
        for data in all_analysis_data:
            for doc_status, info in data.get('doc_status_analysis', {}).items():
                if doc_status not in merged_analysis['doc_status_analysis']:
                    merged_analysis['doc_status_analysis'][doc_status] = {
                        'task_count': 0,
                        'total_cost': 0,
                        'total_time_minutes': 0
                    }
                merged_analysis['doc_status_analysis'][doc_status]['task_count'] += info.get('task_count', 0)
                merged_analysis['doc_status_analysis'][doc_status]['total_cost'] += info.get('total_cost', 0)
                merged_analysis['doc_status_analysis'][doc_status]['total_time_minutes'] += info.get('total_time_minutes', 0)
        
        st.session_state.analysis_data = merged_analysis
    else:
        st.session_state.analysis_data = {}


def get_combined_tasks() -> List[Dict[str, Any]]:
    """Get combined tasks from all uploaded files."""
    init_session_state()
    return st.session_state.combined_tasks


def get_analysis_data() -> Dict[str, Any]:
    """Get merged analysis data from all uploaded files."""
    init_session_state()
    # Ensure we return a dict, never None
    data = st.session_state.analysis_data
    return data if data is not None else {}


def has_data() -> bool:
    """Check if there is any analysis data available."""
    init_session_state()
    tasks = st.session_state.combined_tasks
    return tasks is not None and len(tasks) > 0


def display_summary_metrics(combined_tasks: List[Dict[str, Any]]):
    """Display summary metrics for the analysis."""
    total_cost = sum(task.get('total_cost', 0) for task in combined_tasks)
    total_time = sum(task.get('time_minutes', 0) for task in combined_tasks)
    total_tasks = len(combined_tasks)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Tasks", total_tasks)
    
    with col2:
        st.metric("Total Cost", f"${total_cost:,.2f}")
    
    with col3:
        st.metric("Total Time", f"{total_time/60:.1f} hours")
    
    with col4:
        currencies = set(task.get('currency', 'Unknown') for task in combined_tasks if task.get('currency'))
        st.metric("Currencies", ", ".join(currencies) if currencies else "Unknown")


def inject_iconify_cdn():
    """No-op function for compatibility - icons now use emoji (Streamlit-native)."""
    pass  # Emoji icons don't need CDN injection


def render_icon(icon_name: str, size: int = 20, color: str = INOCTA_COLORS['slate']) -> str:
    """
    Convert HeroIcon name to emoji (Streamlit-compatible).
    This is a compatibility function that maps Iconify icon names to emoji.
    
    Args:
        icon_name: Icon name (e.g., 'heroicons:chart-bar-square' or emoji like '📊')
        size: Ignored (kept for compatibility)
        color: Ignored (kept for compatibility)
        
    Returns:
        Emoji string compatible with Streamlit
    """
    # If already an emoji, return as-is
    if not icon_name.startswith('heroicons:'):
        return icon_name
    
    # Map HeroIcons to emoji (commonly used ones)
    icon_map = {
        'heroicons:chart-bar-square': '📊',
        'heroicons:clipboard-document-list': '📋',
        'heroicons:building-office-2': '🏭',
        'heroicons:user-group': '👥',
        'heroicons:chart-bar': '📊',
        'heroicons:book-open': '📚',
        'heroicons:wrench-screwdriver': '🔧',
        'heroicons:sparkles': '💡',
        'heroicons:exclamation-triangle': '⚠️',
        'heroicons:question-mark-circle': '❓',
        'heroicons:check-circle': '✅',
        'heroicons:arrow-down-tray': '💾',
        'heroicons:information-circle': '❓',
        'heroicons:folder-open': '📁',
        'heroicons:document-text': '📄',
        'heroicons:arrow-up-tray': '👆',
        'heroicons:trash': '🗑️',
        'heroicons:exclamation-circle': '❌',
        'heroicons:map': '🧭',
        'heroicons:check-badge': '✅',
    }
    
    return icon_map.get(icon_name, '📋')  # Default emoji if not found


def render_page_header(page_title: str = None, icon_name: str = "heroicons:chart-bar-square"):
    """
    Render professional page header with Iconify icons and Inocta branding.
    
    Args:
        page_title: Optional page title (defaults to app name)
        icon_name: HeroIcon name (default: chart-bar-square)
    """
    # Inject Iconify CDN on first call
    if 'iconify_injected' not in st.session_state:
        inject_iconify_cdn()
        st.session_state.iconify_injected = True
    
    # Use app name if no title provided
    title = page_title or APP_NAME
    
    # Render header with icon and version
    icon_html = render_icon(icon_name, size=32, color=INOCTA_COLORS['deep_teal'])
    
    st.markdown(f"""
    <div style="margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 2px solid {INOCTA_COLORS['light_teal']};">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
            <span style="font-size: 32px;">{icon_html}</span>
            <h1 style="margin: 0; color: {INOCTA_COLORS['deep_teal']}; font-family: 'Poppins', sans-serif; font-weight: 600; font-size: 2rem;">
                {title}
            </h1>
        </div>
        <p style="margin: 0; color: {INOCTA_COLORS['slate']}; font-family: 'Roboto', sans-serif; font-size: 0.9rem;">
            Version {APP_VERSION}
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar_header():
    """Render simple sidebar header with app name using Streamlit-native components."""
    # Simple, Streamlit-native sidebar header
    # Streamlit's native multi-page navigation will appear automatically below
    
    # Footer section at bottom of sidebar
    # Note: Streamlit's navigation menu already provides spacing, so we use minimal spacing
    st.sidebar.markdown("")  # Small spacing instead of separator
    st.sidebar.markdown(f"**📊 {APP_NAME}**")
    st.sidebar.markdown(f"*Version: {APP_VERSION}*")

