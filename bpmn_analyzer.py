import streamlit as st
import xmltodict
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import json
import os
from typing import Dict, List, Any, Tuple

class BPMNAnalyzer:
    """
    A comprehensive BPMN analysis tool that extracts business insights,
    calculates costs, and provides KPI analysis from BPMN XML files.
    """
    
    def __init__(self):
        self.processes = {}
        self.tasks = []
        self.collaborations = {}
        self.total_costs = 0
        self.total_time = 0
        self.currencies = set()
        
    def parse_bpmn_file(self, file_content: str) -> Dict[str, Any]:
        """
        Parse BPMN XML content and extract structured data.
        
        Args:
            file_content: XML content as string
            
        Returns:
            Dictionary containing parsed BPMN data
        """
        try:
            # Parse XML to dictionary
            xml_dict = xmltodict.parse(file_content)
            
            # Null check for parsed XML
            if xml_dict is None:
                st.error("Failed to parse XML content")
                return {}
            
            # Extract basic file information
            definitions = xml_dict.get('bpmn:definitions', {})
            
            # Extract collaborations (process participants)
            collaborations = definitions.get('bpmn:collaboration', [])
            if not isinstance(collaborations, list):
                collaborations = [collaborations] if collaborations else []
                
            # Extract processes
            processes = definitions.get('bpmn:process', [])
            if not isinstance(processes, list):
                processes = [processes] if processes else []
                
            # Parse collaborations and create process-to-swimlane mapping
            parsed_collaborations = {}
            process_to_swimlane = {}  # Map process ID to swimlane name
            
            for collab in collaborations:
                if collab:
                    collab_id = collab.get('@id', 'Unknown')
                    participants = collab.get('bpmn:participant', [])
                    if not isinstance(participants, list):
                        participants = [participants] if participants else []
                    
                    parsed_collaborations[collab_id] = {
                        'participants': [
                            {
                                'id': p.get('@id', 'Unknown'),
                                'name': p.get('@name', 'Unknown'),
                                'process_ref': p.get('@processRef', 'Unknown')
                            }
                            for p in participants
                        ],
                        'message_flows': collab.get('bpmn:messageFlow', [])
                    }
                    
                    # Create mapping from process ID to swimlane name
                    for participant in parsed_collaborations[collab_id]['participants']:
                        process_to_swimlane[participant['process_ref']] = participant['name']
            
            # Parse processes and extract tasks
            parsed_processes = {}
            all_tasks = []
            
            for process in processes:
                if process:
                    process_id = process.get('@id', 'Unknown')
                    process_name = process.get('@name', 'Unknown')
                    
                    # Get swimlane name for this process
                    swimlane_name = process_to_swimlane.get(process_id, process_name)
                    
                    # Extract tasks from this process
                    process_tasks = []
                    
                    # Look for different types of tasks
                    task_types = ['bpmn:task', 'bpmn:sendTask', 'bpmn:manualTask']
                    
                    for task_type in task_types:
                        tasks = process.get(task_type, [])
                        if not isinstance(tasks, list):
                            tasks = [tasks] if tasks else []
                        
                        for task in tasks:
                            if task:
                                parsed_task = self._parse_task(task, swimlane_name, task_type, process_id)
                                if parsed_task:
                                    process_tasks.append(parsed_task)
                                    all_tasks.append(parsed_task)
                    
                    parsed_processes[process_id] = {
                        'name': process_name,
                        'swimlane': swimlane_name,
                        'tasks': process_tasks,
                        'start_events': process.get('bpmn:startEvent', []),
                        'end_events': process.get('bpmn:endEvent', []),
                        'gateways': process.get('bpmn:exclusiveGateway', [])
                    }
            
            return {
                'collaborations': parsed_collaborations,
                'processes': parsed_processes,
                'tasks': all_tasks,
                'process_to_swimlane': process_to_swimlane,
                'file_info': {
                    'exporter': definitions.get('@exporter', 'Unknown'),
                    'exporter_version': definitions.get('@exporterVersion', 'Unknown'),
                    'target_namespace': definitions.get('@targetNamespace', 'Unknown')
                }
            }
            
        except Exception as e:
            st.error(f"Error parsing BPMN file: {str(e)}")
            return {}
    
    def _parse_task(self, task: Dict, swimlane_name: str, task_type: str, process_id: str = 'Unknown') -> Dict[str, Any]:
        """
        Parse individual task and extract business metadata.
        
        Args:
            task: Task dictionary from XML
            swimlane_name: Name of the swimlane/department this task belongs to
            task_type: Type of BPMN task
            
        Returns:
            Parsed task dictionary
        """
        try:
            # Add null checks for task parameter
            if task is None:
                return self._create_default_task(swimlane_name, task_type)
            
            task_id = task.get('@id', 'Unknown')
            task_name = task.get('@name', 'Unknown')
            
            # Extract extension elements (Camunda properties)
            extension_elements = task.get('bpmn:extensionElements', {})
            camunda_properties = {}
            
            if extension_elements:
                properties = extension_elements.get('camunda:properties', {})
                if properties:
                    prop_list = properties.get('camunda:property', [])
                    if not isinstance(prop_list, list):
                        prop_list = [prop_list] if prop_list else []
                    
                    for prop in prop_list:
                        if prop:
                            name = prop.get('@name', '')
                            value = prop.get('@value', '')
                            camunda_properties[name] = value
            
            # Calculate costs and time
            time_hhmm = camunda_properties.get('time_hhmm', '00:00')
            
            # Handle empty string values for numeric fields
            cost_per_hour_str = camunda_properties.get('cost_per_hour', '0')
            cost_per_hour = float(cost_per_hour_str) if cost_per_hour_str and cost_per_hour_str.strip() else 0
            
            currency = camunda_properties.get('currency', 'Unknown')
            
            other_costs_str = camunda_properties.get('other_costs', '0')
            other_costs = float(other_costs_str) if other_costs_str and other_costs_str.strip() else 0
            
            # Parse time from HH:MM format
            time_minutes = self._parse_time_to_minutes(time_hhmm)
            time_hours = time_minutes / 60 if time_minutes > 0 else 0
            
            # Calculate total cost for this task
            labor_cost = time_hours * cost_per_hour
            total_task_cost = labor_cost + other_costs
            
            return {
                'id': task_id,
                'name': task_name,
                'swimlane': swimlane_name,
                'type': task_type.replace('bpmn:', ''),
                'time_hhmm': time_hhmm,
                'time_display': self._format_time_display(time_hhmm),  # Formatted for display
                'time_minutes': time_minutes,
                'time_hours': time_hours,
                'cost_per_hour': cost_per_hour,
                'currency': currency,
                'other_costs': other_costs,
                'labor_cost': labor_cost,
                'total_cost': total_task_cost,
                'task_owner': camunda_properties.get('task_owner', 'Unknown'),
                'task_description': camunda_properties.get('task_description', ''),
                'task_status': camunda_properties.get('task_status', 'Unknown'),
                'doc_status': camunda_properties.get('doc_status', 'Unknown'),
                'tools_used': camunda_properties.get('tools_used', ''),
                'opportunities': camunda_properties.get('opportunities', ''),
                'issues_text': camunda_properties.get('issues_text', ''),
                'issues_priority': camunda_properties.get('issues_priority', ''),
                'faq_q1': camunda_properties.get('faq_q1', ''),
                'faq_a1': camunda_properties.get('faq_a1', ''),
                'faq_q2': camunda_properties.get('faq_q2', ''),
                'faq_a2': camunda_properties.get('faq_a2', ''),
                'faq_q3': camunda_properties.get('faq_q3', ''),
                'faq_a3': camunda_properties.get('faq_a3', ''),
                'task_industry': camunda_properties.get('task_industry', ''),
                'doc_url': self._normalize_doc_url(camunda_properties.get('doc_url', '')),
                'process_ref': process_id  # Store process ID/reference for each task
            }
            
        except Exception as e:
            # Log error but don't show it to user to avoid cluttering the interface
            print(f"Warning: Error parsing task {task.get('@id', 'Unknown')}: {str(e)}")
            # Return a minimal task object instead of None to avoid breaking the analysis
            process_id_from_context = task.get('@processRef', 'Unknown') if task else 'Unknown'
            return self._create_default_task(swimlane_name, task_type, process_id_from_context)
    
    def _normalize_doc_url(self, doc_url: str) -> str:
        """
        Normalize document URL - treat NR, NO URL, No URL as empty.
        
        Args:
            doc_url: Document URL string from BPMN
            
        Returns:
            Normalized URL string (empty if NR/NO URL/No URL)
        """
        if not doc_url or not isinstance(doc_url, str):
            return ''
        url_str = doc_url.strip()
        # Treat NR, NO URL, No URL (case-insensitive) as empty
        if url_str.lower() in ['nr', 'no url', 'nourl', 'unknown']:
            return ''
        return url_str
    
    def _create_default_task(self, swimlane_name: str, task_type: str, process_id: str = 'Unknown') -> Dict[str, Any]:
        """Create a default task object when parsing fails."""
        return {
            'id': 'Unknown',
            'name': 'Unknown',
            'swimlane': swimlane_name,
            'type': task_type.replace('bpmn:', ''),
            'time_hhmm': '00:00',
            'time_display': '00:00',
            'time_minutes': 0,
            'time_hours': 0,
            'cost_per_hour': 0,
            'currency': 'Unknown',
            'other_costs': 0,
            'labor_cost': 0,
            'total_cost': 0,
            'task_owner': 'Unknown',
            'task_description': '',
            'task_status': 'Unknown',
            'doc_status': 'Unknown',
            'tools_used': '',
            'opportunities': '',
            'issues_text': '',
            'issues_priority': '',
            'faq_q1': '',
            'faq_a1': '',
            'faq_q2': '',
            'faq_a2': '',
            'faq_q3': '',
            'faq_a3': '',
            'task_industry': '',
            'doc_url': '',
            'process_ref': 'Unknown'
        }
    
    def _parse_time_to_minutes(self, time_str: str) -> int:
        """
        Convert HH:MM time format to minutes.
        
        Args:
            time_str: Time string in HH:MM format (e.g., "1:30", "2:00") or just hours (e.g., "6", "1", "5")
            
        Returns:
            Time in minutes
        """
        try:
            if not time_str or time_str == '' or time_str.strip() == '':
                return 0
            
            # Handle cases where time might be just a number (assume it's hours)
            if ':' not in time_str:
                try:
                    # If it's just a number like "6", "1", "5", assume it's hours
                    # This matches the BPMN file format where some tasks have "6" meaning 6 hours
                    hours = float(time_str)
                    return int(hours * 60)
                except ValueError:
                    return 0
            
            # Handle HH:MM format
            parts = time_str.split(':')
            if len(parts) == 2:
                hours = int(parts[0]) if parts[0].strip() else 0
                minutes = int(parts[1]) if parts[1].strip() else 0
                return hours * 60 + minutes
            return 0
        except (ValueError, TypeError):
            return 0
    
    def _format_time_display(self, time_str: str) -> str:
        """
        Format time string for consistent display in HH:MM format.
        
        Args:
            time_str: Time string (e.g., "6", "1:00", "0:30")
            
        Returns:
            Formatted time string in HH:MM format
        """
        try:
            if not time_str or time_str == '' or time_str.strip() == '':
                return "0:00"
            
            # If it's just a number, assume it's hours and format as HH:00
            if ':' not in time_str:
                try:
                    hours = int(float(time_str))
                    return f"{hours:02d}:00"
                except ValueError:
                    return "0:00"
            
            # If it's already in HH:MM format, ensure consistent formatting
            parts = time_str.split(':')
            if len(parts) == 2:
                hours = int(parts[0]) if parts[0].strip() else 0
                minutes = int(parts[1]) if parts[1].strip() else 0
                return f"{hours:02d}:{minutes:02d}"
            
            return "0:00"
        except (ValueError, TypeError):
            return "0:00"
    
    def analyze_business_insights(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze parsed BPMN data and extract business insights.
        
        Args:
            parsed_data: Parsed BPMN data
            
        Returns:
            Dictionary containing business insights and KPIs
        """
        tasks = parsed_data.get('tasks', [])
        processes = parsed_data.get('processes', {})
        collaborations = parsed_data.get('collaborations', {})
        
        if not tasks:
            return {}
        
        # Calculate total costs and time
        total_cost = sum(task.get('total_cost', 0) for task in tasks)
        total_time_minutes = sum(task.get('time_minutes', 0) for task in tasks)
        # Use the sum of individual task hours to ensure consistency with table display
        total_time_hours = sum(task.get('time_hours', 0) for task in tasks)
        
        # Debug: Print some task details to verify parsing
        print(f"DEBUG: Total tasks parsed: {len(tasks)}")
        print(f"DEBUG: Total cost calculated: ${total_cost:.2f}")
        print(f"DEBUG: Total time calculated: {total_time_hours:.2f} hours")
        print(f"DEBUG: Total time from minutes conversion: {total_time_minutes / 60:.2f} hours")
        print(f"DEBUG: Expected total time from manual analysis: ~119.75 hours")
        print(f"DEBUG: Expected total cost from manual analysis: ~$21,321.25")
        print(f"DEBUG: --- First 10 tasks details ---")
        for i, task in enumerate(tasks[:10]):  # Show first 10 tasks
            print(f"DEBUG: Task {i+1}: {task.get('name')}")
            print(f"  - Time HH:MM: '{task.get('time_hhmm')}'")
            print(f"  - Time Display: '{task.get('time_display')}'")
            print(f"  - Time minutes: {task.get('time_minutes')} min")
            print(f"  - Time hours: {task.get('time_hours'):.2f} hrs")
            print(f"  - Cost per hour: ${task.get('cost_per_hour', 0):.2f}")
            print(f"  - Total cost: ${task.get('total_cost', 0):.2f}")
            print(f"  - Currency: {task.get('currency', 'Unknown')}")
        print(f"DEBUG: --- End task details ---")
        
        # Group by swimlane (department)
        swimlane_analysis = {}
        for process_id, process_data in processes.items():
            swimlane_tasks = [t for t in tasks if t.get('swimlane') == process_data.get('swimlane')]
            swimlane_cost = sum(t.get('total_cost', 0) for t in swimlane_tasks)
            swimlane_time = sum(t.get('time_minutes', 0) for t in swimlane_tasks)
            
            swimlane_name = process_data.get('swimlane', 'Unknown')
            if swimlane_name not in swimlane_analysis:
                swimlane_analysis[swimlane_name] = {
                    'task_count': len(swimlane_tasks),
                    'total_cost': swimlane_cost,
                    'total_time_minutes': swimlane_time,
                    'total_time_hours': swimlane_time / 60,
                    'tasks': swimlane_tasks
                }
            else:
                # Add to existing swimlane if multiple processes share the same swimlane
                swimlane_analysis[swimlane_name]['task_count'] += len(swimlane_tasks)
                swimlane_analysis[swimlane_name]['total_cost'] += swimlane_cost
                swimlane_analysis[swimlane_name]['total_time_minutes'] += swimlane_time
                swimlane_analysis[swimlane_name]['total_time_hours'] += swimlane_time / 60
                swimlane_analysis[swimlane_name]['tasks'].extend(swimlane_tasks)
        
        # Group by task owner
        owner_analysis = {}
        for task in tasks:
            owner = task.get('task_owner', 'Unknown')
            if owner not in owner_analysis:
                owner_analysis[owner] = {
                    'task_count': 0,
                    'total_cost': 0,
                    'total_time_minutes': 0
                }
            
            owner_analysis[owner]['task_count'] += 1
            owner_analysis[owner]['total_cost'] += task.get('total_cost', 0)
            owner_analysis[owner]['total_time_minutes'] += task.get('time_minutes', 0)
        
        # Group by task status
        status_analysis = {}
        for task in tasks:
            status = task.get('task_status', 'Unknown')
            if status not in status_analysis:
                status_analysis[status] = {
                    'task_count': 0,
                    'total_cost': 0,
                    'total_time_minutes': 0
                }
            
            status_analysis[status]['task_count'] += 1
            status_analysis[status]['total_cost'] += task.get('total_cost', 0)
            status_analysis[status]['total_time_minutes'] += task.get('time_minutes', 0)
        
        # Group by issues priority
        priority_analysis = {}
        for task in tasks:
            priority = task.get('issues_priority', 'Unknown')
            if priority not in priority_analysis:
                priority_analysis[priority] = {
                    'task_count': 0,
                    'total_cost': 0,
                    'total_time_minutes': 0
                }
            
            priority_analysis[priority]['task_count'] += 1
            priority_analysis[priority]['total_cost'] += task.get('total_cost', 0)
            priority_analysis[priority]['total_time_minutes'] += task.get('time_minutes', 0)
        
        # Group by documentation status
        doc_status_analysis = {}
        for task in tasks:
            doc_status = task.get('doc_status', 'Unknown')
            if doc_status not in doc_status_analysis:
                doc_status_analysis[doc_status] = {
                    'task_count': 0,
                    'total_cost': 0,
                    'total_time_minutes': 0
                }
            
            doc_status_analysis[doc_status]['task_count'] += 1
            doc_status_analysis[doc_status]['total_cost'] += task.get('total_cost', 0)
            doc_status_analysis[doc_status]['total_time_minutes'] += task.get('time_minutes', 0)
        
        # Extract currencies
        currencies = set(task.get('currency', 'Unknown') for task in tasks if task.get('currency'))
        
        return {
            'summary': {
                'total_tasks': len(tasks),
                'total_processes': len(processes),
                'total_collaborations': len(collaborations),
                'total_cost': total_cost,
                'total_time_minutes': total_time_minutes,
                'total_time_hours': total_time_hours,
                'currencies': list(currencies)
            },
            'swimlane_analysis': swimlane_analysis,
            'owner_analysis': owner_analysis,
            'status_analysis': status_analysis,
            'priority_analysis': priority_analysis,
            'doc_status_analysis': doc_status_analysis,
            'tasks': tasks
        }
    
    def generate_excel_report(self, analysis_data: Dict[str, Any], filename: str = "bpmn_analysis_report.xlsx"):
        """
        Generate Excel report with detailed analysis.
        
        Args:
            analysis_data: Analysis results
            filename: Output filename
        """
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Summary sheet
                summary_data = analysis_data.get('summary', {})
                summary_df = pd.DataFrame([summary_data])
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Tasks sheet
                tasks_df = pd.DataFrame(analysis_data.get('tasks', []))
                if not tasks_df.empty:
                    tasks_df.to_excel(writer, sheet_name='Tasks', index=False)
                
                # Swimlane analysis sheet
                swimlane_data = analysis_data.get('swimlane_analysis', {})
                if swimlane_data:
                    swimlane_df = pd.DataFrame(swimlane_data).T.reset_index()
                    # Ensure all required columns exist
                    if 'total_time_minutes' in swimlane_df.columns:
                        swimlane_df['Total Time (hrs)'] = swimlane_df['total_time_minutes'] / 60
                    else:
                        swimlane_df['Total Time (hrs)'] = 0
                    
                    # Rename columns to match expected structure
                    column_mapping = {
                        'index': 'Swimlane/Department',
                        'task_count': 'Task Count',
                        'total_cost': 'Total Cost',
                        'total_time_minutes': 'Total Time (min)',
                        'total_time_hours': 'Total Time (hrs)'
                    }
                    
                    # Apply column mapping and add missing columns
                    for old_col, new_col in column_mapping.items():
                        if old_col in swimlane_df.columns:
                            swimlane_df[new_col] = swimlane_df[old_col]
                        else:
                            swimlane_df[new_col] = 0
                    
                    # Ensure all expected columns exist
                    expected_columns = ['Swimlane/Department', 'Task Count', 'Total Cost', 'Total Time (min)', 'Total Time (hrs)']
                    for col in expected_columns:
                        if col not in swimlane_df.columns:
                            swimlane_df[col] = 0
                    
                    # Select only the expected columns in the right order
                    swimlane_df = swimlane_df[expected_columns]
                    swimlane_df.to_excel(writer, sheet_name='Swimlane Analysis', index=False)
                
                # Owner analysis sheet
                owner_data = analysis_data.get('owner_analysis', {})
                if owner_data:
                    owner_df = pd.DataFrame(owner_data).T.reset_index()
                    # Ensure all required columns exist
                    if 'total_time_minutes' in owner_df.columns:
                        owner_df['Total Time (hrs)'] = owner_df['total_time_minutes'] / 60
                    else:
                        owner_df['Total Time (hrs)'] = 0
                    
                    # Rename columns to match expected structure
                    column_mapping = {
                        'index': 'Owner',
                        'task_count': 'Task Count',
                        'total_cost': 'Total Cost',
                        'total_time_minutes': 'Total Time (min)',
                        'total_time_hours': 'Total Time (hrs)'
                    }
                    
                    # Apply column mapping and add missing columns
                    for old_col, new_col in column_mapping.items():
                        if old_col in owner_df.columns:
                            owner_df[new_col] = owner_df[old_col]
                        else:
                            owner_df[new_col] = 0
                    
                    # Ensure all expected columns exist
                    expected_columns = ['Owner', 'Task Count', 'Total Cost', 'Total Time (min)', 'Total Time (hrs)']
                    for col in expected_columns:
                        if col not in owner_df.columns:
                            owner_df[col] = 0
                    
                    # Select only the expected columns in the right order
                    owner_df = owner_df[expected_columns]
                    owner_df.to_excel(writer, sheet_name='Owner Analysis', index=False)
                
                # Status analysis sheet
                status_data = analysis_data.get('status_analysis', {})
                if status_data:
                    status_df = pd.DataFrame(status_data).T.reset_index()
                    # Ensure all required columns exist
                    if 'total_time_minutes' in status_df.columns:
                        status_df['Total Time (hrs)'] = status_df['total_time_minutes'] / 60
                    else:
                        status_df['Total Time (hrs)'] = 0
                    
                    # Rename columns to match expected structure
                    column_mapping = {
                        'index': 'Status',
                        'task_count': 'Task Count',
                        'total_cost': 'Total Cost',
                        'total_time_minutes': 'Total Time (min)',
                        'total_time_hours': 'Total Time (hrs)'
                    }
                    
                    # Apply column mapping and add missing columns
                    for old_col, new_col in column_mapping.items():
                        if old_col in status_df.columns:
                            status_df[new_col] = status_df[old_col]
                        else:
                            status_df[new_col] = 0
                    
                    # Ensure all expected columns exist
                    expected_columns = ['Status', 'Task Count', 'Total Cost', 'Total Time (min)', 'Total Time (hrs)']
                    for col in expected_columns:
                        if col not in status_df.columns:
                            status_df[col] = 0
                    
                    # Select only the expected columns in the right order
                    status_df = status_df[expected_columns]
                    status_df.to_excel(writer, sheet_name='Status Analysis', index=False)
                
                # Priority analysis sheet
                priority_data = analysis_data.get('priority_analysis', {})
                if priority_data:
                    priority_df = pd.DataFrame(priority_data).T.reset_index()
                    # Ensure all required columns exist
                    if 'total_time_minutes' in priority_df.columns:
                        priority_df['Total Time (hrs)'] = priority_df['total_time_minutes'] / 60
                    else:
                        priority_df['Total Time (hrs)'] = 0
                    
                    # Rename columns to match expected structure
                    column_mapping = {
                        'index': 'Priority',
                        'task_count': 'Task Count',
                        'total_cost': 'Total Cost',
                        'total_time_minutes': 'Total Time (min)',
                        'total_time_hours': 'Total Time (hrs)'
                    }
                    
                    # Apply column mapping and add missing columns
                    for old_col, new_col in column_mapping.items():
                        if old_col in priority_df.columns:
                            priority_df[new_col] = priority_df[old_col]
                        else:
                            priority_df[new_col] = 0
                    
                    # Ensure all expected columns exist
                    expected_columns = ['Priority', 'Task Count', 'Total Cost', 'Total Time (min)', 'Total Time (hrs)']
                    for col in expected_columns:
                        if col not in priority_df.columns:
                            priority_df[col] = 0
                    
                    # Select only the expected columns in the right order
                    priority_df = priority_df[expected_columns]
                    priority_df.to_excel(writer, sheet_name='Priority Analysis', index=False)
                
                # Documentation status analysis sheet
                doc_status_data = analysis_data.get('doc_status_analysis', {})
                if doc_status_data:
                    doc_status_df = pd.DataFrame(doc_status_data).T.reset_index()
                    # Ensure all required columns exist
                    if 'total_time_minutes' in doc_status_df.columns:
                        doc_status_df['Total Time (hrs)'] = doc_status_df['total_time_minutes'] / 60
                    else:
                        doc_status_df['Total Time (hrs)'] = 0
                    
                    # Rename columns to match expected structure
                    column_mapping = {
                        'index': 'Documentation Status',
                        'task_count': 'Task Count',
                        'total_cost': 'Total Cost',
                        'total_time_minutes': 'Total Time (min)',
                        'total_time_hours': 'Total Time (hrs)'
                    }
                    
                    # Apply column mapping and add missing columns
                    for old_col, new_col in column_mapping.items():
                        if old_col in doc_status_df.columns:
                            doc_status_df[new_col] = doc_status_df[old_col]
                        else:
                            doc_status_df[new_col] = 0
                    
                    # Ensure all expected columns exist
                    expected_columns = ['Documentation Status', 'Task Count', 'Total Cost', 'Total Time (min)', 'Total Time (hrs)']
                    for col in expected_columns:
                        if col not in doc_status_df.columns:
                            doc_status_df[col] = 0
                    
                    # Select only the expected columns in the right order
                    doc_status_df = doc_status_df[expected_columns]
                    doc_status_df.to_excel(writer, sheet_name='Documentation Status', index=False)
                
                # Tools analysis sheet
                tools_data = analysis_data.get('tools_analysis', {})
                if tools_data:
                    tools_df = pd.DataFrame(tools_data).T.reset_index()
                    # Ensure all required columns exist
                    if 'total_time_minutes' in tools_df.columns:
                        tools_df['Total Time (hrs)'] = tools_df['total_time_minutes'] / 60
                    else:
                        tools_df['Total Time (hrs)'] = 0
                    
                    # Rename columns to match expected structure
                    column_mapping = {
                        'index': 'Tool',
                        'task_count': 'Task Count',
                        'total_cost': 'Total Cost',
                        'total_time_minutes': 'Total Time (min)',
                        'total_time_hours': 'Total Time (hrs)'
                    }
                    
                    # Apply column mapping and add missing columns
                    for old_col, new_col in column_mapping.items():
                        if old_col in tools_df.columns:
                            tools_df[new_col] = tools_df[old_col]
                        else:
                            tools_df[new_col] = 0
                    
                    # Ensure all expected columns exist
                    expected_columns = ['Tool', 'Task Count', 'Total Cost', 'Total Time (min)', 'Total Time (hrs)']
                    for col in expected_columns:
                        if col not in tools_df.columns:
                            tools_df[col] = 0
                    
                    # Select only the expected columns in the right order
                    tools_df = tools_df[expected_columns]
                    tools_df.to_excel(writer, sheet_name='Tools Analysis', index=False)
                
                # Tool combinations sheet
                tool_combinations_data = analysis_data.get('tool_combinations', {})
                if tool_combinations_data:
                    combo_df = pd.DataFrame(tool_combinations_data).T.reset_index()
                    # Ensure all required columns exist
                    if 'total_time_minutes' in combo_df.columns:
                        combo_df['Total Time (hrs)'] = combo_df['total_time_minutes'] / 60
                    else:
                        combo_df['Total Time (hrs)'] = 0
                    
                    # Rename columns to match expected structure
                    column_mapping = {
                        'index': 'Tool Combination',
                        'task_count': 'Task Count',
                        'total_cost': 'Total Cost',
                        'total_time_minutes': 'Total Time (min)',
                        'total_time_hours': 'Total Time (hrs)'
                    }
                    
                    # Apply column mapping and add missing columns
                    for old_col, new_col in column_mapping.items():
                        if old_col in combo_df.columns:
                            combo_df[new_col] = combo_df[old_col]
                        else:
                            combo_df[new_col] = 0
                    
                    # Ensure all expected columns exist
                    expected_columns = ['Tool Combination', 'Task Count', 'Total Cost', 'Total Time (min)', 'Total Time (hrs)']
                    for col in expected_columns:
                        if col not in combo_df.columns:
                            combo_df[col] = 0
                    
                    # Select only the expected columns in the right order
                    combo_df = combo_df[expected_columns]
                    combo_df.to_excel(writer, sheet_name='Tool Combinations', index=False)
                
                # Quality control sheet
                quality_data = analysis_data.get('quality_issues', [])
                if quality_data:
                    quality_df = pd.DataFrame(quality_data)
                    quality_df.to_excel(writer, sheet_name='Quality Control', index=False)
            
            return filename
            
        except Exception as e:
            st.error(f"Error generating Excel report: {str(e)}")
            return None

def setup_page():
    """Set up the page configuration and initial UI elements."""
    from utils.shared import render_sidebar_header
    
    st.set_page_config(
        page_title="Inocta BPM Analysis",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        }
    )
    
    # Render simple sidebar header
    render_sidebar_header()
    
    # Simple Streamlit-native page header (will be overridden by individual pages)
    from utils.shared import APP_VERSION
    st.title("📊 Inocta BPM Analysis")
    st.markdown(f"**Version:** {APP_VERSION}")
    
    # Minimal custom CSS - only essential styling
    st.markdown("""
    <style>
    /* Fix any URL display issues */
    .stApp > header {
        display: none;
    }
    /* Ensure clean display */
    .main .block-container {
        padding-top: 1rem;
    }
    /* Let Streamlit's native navigation display normally */
    </style>
    """, unsafe_allow_html=True)

# Removed: get_tab_names(), setup_navigation_menu(), add_tab_navigation_script()
# These functions are no longer needed with Streamlit's native multi-page navigation.
# Removed: process_uploaded_files() and display_summary_metrics()
# These functions have been moved to utils/shared.py for use across all pages.

def main():
    """
    Main Streamlit application for BPMN analysis.
    Handles file upload and stores data in session state for use by all pages.
    """
    # Set up page configuration and UI
    setup_page()
    
    # Initialize session state
    from utils.shared import init_session_state, get_analyzer, process_uploaded_files, update_analysis_data
    init_session_state()
    
    # Get analyzer instance
    analyzer = get_analyzer()
    
    # File upload is now on the main page content area
    from utils.shared import setup_file_upload_main
    setup_file_upload_main()
    
    # Check for auto-redirect flag (set after file upload)
    if st.session_state.get('auto_redirect_to_exec', False):
        st.session_state.auto_redirect_to_exec = False
        st.switch_page("pages/01_Executive_Summary.py")
    
    # Display content based on whether data is available
    from utils.shared import has_data, get_combined_tasks, get_analysis_data
    if has_data():
        # Show file info and basic stats when data is available
        combined_tasks = get_combined_tasks()
        analysis_data = get_analysis_data()
        
        st.success("✅ **Files loaded successfully!**")
        
        # Show uploaded files information
        if st.session_state.all_analysis_data:
            st.markdown("### 📄 Uploaded Files")
            for i, data in enumerate(st.session_state.all_analysis_data, 1):
                filename = data.get('filename', 'Unknown')
                task_count = len(data.get('tasks', []))
                st.markdown(f"{i}. **{filename}** - {task_count} task(s)")
        
        # Show basic statistics
        st.markdown("### 📊 Quick Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_tasks = len(combined_tasks)
            st.metric("Total Tasks", f"{total_tasks:,}")
        
        with col2:
            total_cost = sum(task.get('total_cost', 0) for task in combined_tasks)
            # Get currencies, filtering out empty/None/Unknown values
            currencies = set()
            for task in combined_tasks:
                currency = task.get('currency')
                if currency and isinstance(currency, str) and currency.strip() and currency != 'Unknown':
                    currencies.add(currency)
            # Use the currency if available, otherwise don't show prefix
            if currencies:
                currency_display = list(currencies)[0]
                cost_display = f"{currency_display} {total_cost:,.2f}"
            else:
                cost_display = f"{total_cost:,.2f}"
            st.metric("Total Cost", cost_display)
        
        with col3:
            total_time_hours = sum(task.get('time_minutes', 0) for task in combined_tasks) / 60
            st.metric("Total Time", f"{total_time_hours:.1f} hrs")
        
        with col4:
            unique_swimlanes = len(set(task.get('swimlane', 'Unknown') for task in combined_tasks))
            st.metric("Departments", unique_swimlanes)
        
        # Navigation prompt
        st.markdown("---")
        st.info("🧭 **Use the navigation menu in the sidebar to explore detailed analysis:**")
        st.markdown("""
        - **📊 Executive Summary**: High-level KPIs, charts, and health checks
        - **📋 Tasks Overview**: Detailed task filtering and display
        - **🏭 Swimlane Analysis**: Department-based analysis
        - **👥 Owner Analysis**: Task owner insights
        - **📊 Status Analysis**: Task status tracking
        - **📚 Documentation Status**: Documentation state analysis
        - **🔧 Tools Analysis**: Tool usage patterns
        - **💡 Opportunities**: Improvement opportunities
        - **⚠️ Issues & Risks**: Problem identification
        - **❓ FAQ Knowledge**: Knowledge capture
        - **✅ Quality Control**: Data quality assessment
        - **💾 Export Data**: Multi-format exports
        - **❓ Help & Guide**: Complete user guide
        """)
        
        # Quick action button to go to Executive Summary
        if st.button("📊 View Executive Summary", type="primary", use_container_width=True):
            st.switch_page("pages/01_Executive_Summary.py")
    else:
        # Show welcome message if no data
        st.info("👋 **Welcome to Inocta BPM Analysis!**")
        st.markdown("""
        ### Getting Started
        
        1. **Upload BPMN Files**: Upload one or more BPMN XML files above using the file upload section
        2. **Navigate Pages**: Once files are uploaded, use the navigation menu in the sidebar to explore different analysis views
        3. **Explore Insights**: Each page provides different perspectives on your process data
        
        ### Available Analysis Pages
        
        Once you upload files, you'll have access to:
        
        - **📊 Executive Summary**: High-level KPIs and insights
        - **📋 Tasks Overview**: Detailed task filtering and display
        - **🏭 Swimlane Analysis**: Department-based analysis
        - **👥 Owner Analysis**: Task owner insights
        - **📊 Status Analysis**: Task status tracking
        - **📚 Documentation Status**: Documentation state analysis
        - **🔧 Tools Analysis**: Tool usage patterns
        - **💡 Opportunities**: Improvement opportunities
        - **⚠️ Issues & Risks**: Problem identification
        - **❓ FAQ Knowledge**: Knowledge capture
        - **✅ Quality Control**: Data quality assessment
        - **💾 Export Data**: Multi-format exports
        - **❓ Help & Guide**: Complete user guide
        """)

# Markdown Report Generation Functions
def generate_markdown_report(analysis_data, combined_tasks):
    """Generate a comprehensive Markdown report with all analysis data."""
    
    # Header
    markdown = f"""# BPMN Analysis Report
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## 📊 Executive Summary

### Key Metrics
- **Total Tasks**: {len(combined_tasks)}
- **Total Cost**: {analysis_data.get('total_costs', 0):.2f}
- **Total Time**: {analysis_data.get('total_time', 0) / 60:.2f} hours
- **Departments**: {len(set(task.get('swimlane', 'Unknown') for task in combined_tasks))}
- **Task Owners**: {len(set(task.get('task_owner', 'Unknown') for task in combined_tasks))}

### Currency Distribution
"""
    
    # Currency analysis
    currency_analysis = {}
    for task in combined_tasks:
        currency = task.get('currency', 'Unknown')
        if currency not in currency_analysis:
            currency_analysis[currency] = {'total_cost': 0, 'task_count': 0}
        currency_analysis[currency]['total_cost'] += task.get('total_cost', 0)
        currency_analysis[currency]['task_count'] += 1
    
    for currency, data in currency_analysis.items():
        markdown += f"- **{currency}**: {data['total_cost']:.2f} ({data['task_count']} tasks)\n"
    
    markdown += "\n### Industry Distribution\n"
    
    # Industry analysis
    industry_analysis = {}
    for task in combined_tasks:
        industry = task.get('task_industry', 'Unknown')
        if industry not in industry_analysis:
            industry_analysis[industry] = {'task_count': 0, 'total_cost': 0}
        industry_analysis[industry]['task_count'] += 1
        industry_analysis[industry]['total_cost'] += task.get('total_cost', 0)
    
    for industry, data in industry_analysis.items():
        markdown += f"- **{industry}**: {data['task_count']} tasks (${data['total_cost']:.2f})\n"
    
    # Swimlane Analysis
    markdown += "\n## 🏭 Department (Swimlane) Analysis\n\n"
    markdown += "| Department | Task Count | Total Cost | Total Time (hrs) | Avg Cost per Task |\n"
    markdown += "|------------|------------|------------|------------------|-------------------|\n"
    
    if 'swimlane_analysis' in analysis_data:
        for swimlane, data in analysis_data['swimlane_analysis'].items():
            avg_cost = data['total_cost'] / data['task_count'] if data['task_count'] > 0 else 0
            markdown += f"| {swimlane} | {data['task_count']} | ${data['total_cost']:.2f} | {data['total_time_minutes'] / 60:.2f} | ${avg_cost:.2f} |\n"
    
    # Owner Analysis
    markdown += "\n## 👥 Task Owner Analysis\n\n"
    markdown += "| Owner | Task Count | Total Cost | Total Time (hrs) | Avg Cost per Task |\n"
    markdown += "|-------|------------|------------|------------------|-------------------|\n"
    
    if 'owner_analysis' in analysis_data:
        for owner, data in analysis_data['owner_analysis'].items():
            avg_cost = data['total_cost'] / data['task_count'] if data['task_count'] > 0 else 0
            markdown += f"| {owner} | {data['task_count']} | ${data['total_cost']:.2f} | {data['total_time_minutes'] / 60:.2f} | ${avg_cost:.2f} |\n"
    
    # Status Analysis
    markdown += "\n## 📊 Status & Priority Analysis\n\n"
    markdown += "| Status | Task Count | Total Cost | Total Time (hrs) |\n"
    markdown += "|--------|------------|------------|------------------|\n"
    
    if 'status_analysis' in analysis_data:
        for status, data in analysis_data['status_analysis'].items():
            markdown += f"| {status} | {data['task_count']} | ${data['total_cost']:.2f} | {data['total_time_minutes'] / 60:.2f} |\n"
    
    # Documentation Status
    markdown += "\n## 📚 Documentation Status Analysis\n\n"
    markdown += "| Status | Task Count | Total Cost | Total Time (hrs) |\n"
    markdown += "|--------|------------|------------|------------------|\n"
    
    if 'doc_status_analysis' in analysis_data:
        for doc_status, data in analysis_data['doc_status_analysis'].items():
            markdown += f"| {doc_status} | {data['task_count']} | ${data['total_cost']:.2f} | {data['total_time_minutes'] / 60:.2f} |\n"
    
    # Tools Analysis
    markdown += "\n## 🔧 Tools Analysis\n\n"
    markdown += "| Tool | Task Count | Total Cost | Total Time (hrs) | Departments |\n"
    markdown += "|------|------------|------------|------------------|-------------|\n"
    
    if 'tools_analysis' in analysis_data:
        for tool, data in analysis_data['tools_analysis'].items():
            dept_list = ', '.join(data.get('swimlanes', []))
            markdown += f"| {tool} | {data['task_count']} | ${data['total_cost']:.2f} | {data['total_time_minutes'] / 60:.2f} | {dept_list} |\n"
    
    # Opportunities
    markdown += "\n## 💡 Opportunities & Improvement Ideas\n\n"
    
    opportunities_found = False
    for task in combined_tasks:
        opportunities = task.get('opportunities', '')
        if opportunities and opportunities.strip():
            opportunities_found = True
            markdown += f"**Task**: {task.get('name', 'Unknown')} ({task.get('swimlane', 'Unknown')})\n"
            markdown += f"**Opportunity**: {opportunities}\n"
            markdown += f"**Owner**: {task.get('task_owner', 'Unknown')}\n"
            markdown += f"**Potential Impact**: ${task.get('total_cost', 0):.2f} + {task.get('time_minutes', 0) / 60:.2f} hours\n\n"
    
    if not opportunities_found:
        markdown += "*No opportunities captured in the current data.*\n"
    
    # Issues & Risks
    markdown += "\n## ⚠️ Issues & Risks Analysis\n\n"
    
    issues_found = False
    for task in combined_tasks:
        issues_text = task.get('issues_text', '')
        issues_priority = task.get('issues_priority', '')
        if issues_text and issues_text.strip():
            issues_found = True
            markdown += f"**Task**: {task.get('name', 'Unknown')} ({task.get('swimlane', 'Unknown')})\n"
            markdown += f"**Issue**: {issues_text}\n"
            markdown += f"**Priority**: {issues_priority}\n"
            markdown += f"**Owner**: {task.get('task_owner', 'Unknown')}\n"
            markdown += f"**Current Cost**: ${task.get('total_cost', 0):.2f}\n\n"
    
    if not issues_found:
        markdown += "*No issues captured in the current data.*\n"
    
    # FAQ Knowledge
    markdown += "\n## ❓ FAQ Knowledge Capture\n\n"
    
    faq_found = False
    for task in combined_tasks:
        for i in range(1, 4):
            question = task.get(f'faq_q{i}', '')
            answer = task.get(f'faq_a{i}', '')
            if question and answer and question.strip() and answer.strip():
                faq_found = True
                markdown += f"**Task**: {task.get('name', 'Unknown')} ({task.get('swimlane', 'Unknown')})\n"
                markdown += f"**Q{i}**: {question}\n"
                markdown += f"**A{i}**: {answer}\n"
                markdown += f"**Owner**: {task.get('task_owner', 'Unknown')}\n\n"
    
    if not faq_found:
        markdown += "*No FAQs captured in the current data.*\n"
    
    # Quality Control
    markdown += "\n## ✅ Quality Control Summary\n\n"
    
    if 'quality_issues' in analysis_data:
        markdown += f"**Total Quality Issues Found**: {len(analysis_data['quality_issues'])}\n\n"
        markdown += "| Task | Department | Owner | Issues | Issue Count |\n"
        markdown += "|------|------------|-------|--------|-------------|\n"
        
        for issue in analysis_data['quality_issues']:
            markdown += f"| {issue['Task Name']} | {issue['Swimlane']} | {issue['Owner']} | {issue['Issues']} | {issue['Issue Count']} |\n"
    else:
        markdown += "*No quality issues found - all tasks meet standards!*\n"
    
    # Detailed Task List
    markdown += "\n## 📋 Detailed Task List\n\n"
    markdown += "| Task Name | Department | Owner | Time | Cost | Status | Tools |\n"
    markdown += "|-----------|------------|-------|------|------|--------|-------|\n"
    
    for task in combined_tasks:
        markdown += f"| {task.get('name', 'Unknown')} | {task.get('swimlane', 'Unknown')} | {task.get('task_owner', 'Unknown')} | {task.get('time_hhmm', '00:00')} | ${task.get('total_cost', 0):.2f} | {task.get('task_status', 'Unknown')} | {task.get('tools_used', 'N/A')} |\n"
    
    # Footer
    markdown += f"\n---\n*Report generated by BPMN Analysis Tool*\n*Total tasks analyzed: {len(combined_tasks)}*\n"
    
    return markdown

def generate_tasks_markdown(combined_tasks):
    """Generate a Markdown report focused on task details."""
    
    markdown = f"""# BPMN Tasks Report
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## 📋 Task Summary
- **Total Tasks**: {len(combined_tasks)}
- **Departments**: {len(set(task.get('swimlane', 'Unknown') for task in combined_tasks))}
- **Task Owners**: {len(set(task.get('task_owner', 'Unknown') for task in combined_tasks))}

## 📊 Task Details

| Task Name | Department | Owner | Time | Cost | Currency | Status | Documentation | Tools | Opportunities | Issues |
|-----------|------------|-------|------|------|----------|--------|---------------|-------|---------------|--------|
"""
    
    for task in combined_tasks:
        markdown += f"| {task.get('name', 'Unknown')} | {task.get('swimlane', 'Unknown')} | {task.get('task_owner', 'Unknown')} | {task.get('time_hhmm', '00:00')} | ${task.get('total_cost', 0):.2f} | {task.get('currency', 'Unknown')} | {task.get('task_status', 'Unknown')} | {task.get('doc_status', 'Unknown')} | {task.get('tools_used', 'N/A')} | {task.get('opportunities', 'N/A')} | {task.get('issues_text', 'N/A')} |\n"
    
    markdown += f"\n---\n*Tasks report generated by BPMN Analysis Tool*\n*Total tasks: {len(combined_tasks)}*\n"
    
    return markdown

def generate_summary_markdown(analysis_data, combined_tasks):
    """Generate a summary Markdown report with key metrics."""
    
    markdown = f"""# BPMN Analysis Summary Report
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## 📊 Executive Summary

### Key Performance Indicators
- **Total Tasks**: {len(combined_tasks)}
- **Total Cost**: ${analysis_data.get('total_costs', 0):.2f}
- **Total Time**: {analysis_data.get('total_time', 0) / 60:.2f} hours
- **Departments**: {len(set(task.get('swimlane', 'Unknown') for task in combined_tasks))}
- **Task Owners**: {len(set(task.get('task_owner', 'Unknown') for task in combined_tasks))}

### Cost Distribution by Department
"""
    
    if 'swimlane_analysis' in analysis_data:
        for swimlane, data in analysis_data['swimlane_analysis'].items():
            markdown += f"- **{swimlane}**: ${data['total_cost']:.2f} ({data['task_count']} tasks)\n"
    
    markdown += "\n### Workload Distribution by Owner\n"
    
    if 'owner_analysis' in analysis_data:
        for owner, data in analysis_data['owner_analysis'].items():
            markdown += f"- **{owner}**: {data['task_count']} tasks (${data['total_cost']:.2f})\n"
    
    markdown += "\n### Status Overview\n"
    
    if 'status_analysis' in analysis_data:
        for status, data in analysis_data['status_analysis'].items():
            markdown += f"- **{status}**: {data['task_count']} tasks\n"
    
    markdown += f"\n---\n*Summary report generated by BPMN Analysis Tool*\n*Analysis completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
    
    return markdown

# Smart Categorization Functions for Better Data Visualization
def categorize_opportunity(opportunity_text):
    """Categorize opportunities based on keywords and content in both French and English."""
    text = opportunity_text.lower()
    
    # Process improvement categories with French and English keywords
    if any(word in text for word in ['automat', 'robot', 'script', 'api', 'integration', 'automatique', 'robotisation']):
        return "🔄 Process Automation"
    elif any(word in text for word in ['optim', 'efficien', 'streamlin', 'simplif', 'optimisation', 'efficacité', 'simplification']):
        return "⚡ Process Optimization"
    elif any(word in text for word in ['cost', 'reduc', 'sav', 'budget', 'coût', 'réduction', 'économie', 'budget']):
        return "💰 Cost Reduction"
    elif any(word in text for word in ['time', 'speed', 'fast', 'quick', 'temps', 'vitesse', 'rapide', 'accélération']):
        return "⏱️ Time Savings"
    elif any(word in text for word in ['qualit', 'accurac', 'error', 'mistake', 'qualité', 'précision', 'erreur']):
        return "🎯 Quality Improvement"
    elif any(word in text for word in ['communic', 'collabor', 'team', 'coordin', 'communication', 'collaboration', 'équipe', 'coordination']):
        return "🤝 Communication & Collaboration"
    elif any(word in text for word in ['tool', 'software', 'system', 'platform', 'outil', 'logiciel', 'système', 'plateforme']):
        return "🛠️ Tool & System Improvement"
    elif any(word in text for word in ['train', 'skill', 'knowledge', 'learn', 'formation', 'compétence', 'connaissance', 'apprentissage']):
        return "📚 Training & Knowledge"
    elif any(word in text for word in ['risk', 'safet', 'complian', 'govern', 'risque', 'sécurité', 'conformité', 'gouvernance']):
        return "🛡️ Risk & Compliance"
    elif any(word in text for word in ['template', 'modèle', 'standard', 'standardisation', 'standardization']):
        return "📋 Templates & Standards"
    elif any(word in text for word in ['product', 'produit', 'créateur', 'creator', 'configuration']):
        return "🏭 Product & Configuration"
    else:
        return "💡 Other Improvements"

def categorize_issue(issue_text):
    """Categorize issues based on keywords and content in both French and English."""
    text = issue_text.lower()
    
    # Issue categories with French and English keywords
    if any(word in text for word in ['error', 'bug', 'fail', 'break', 'crash', 'erreur', 'échec', 'panne']):
        return "🚨 System Errors"
    elif any(word in text for word in ['delay', 'slow', 'wait', 'bottleneck', 'queue', 'retard', 'lent', 'attendre', 'goulot']):
        return "⏳ Delays & Bottlenecks"
    elif any(word in text for word in ['miss', 'forget', 'overlook', 'lost', 'misplace', 'oublie', 'perdu', 'manque', 'oublié']):
        return "❌ Missing Information"
    elif any(word in text for word in ['confus', 'unclear', 'vague', 'ambiguous', 'confus', 'imprécis', 'vague']):
        return "❓ Unclear Processes"
    elif any(word in text for word in ['duplic', 'repeat', 'redundant', 'waste', 'duplication', 'répétition', 'redondant', 'gaspillage']):
        return "🔄 Duplication & Waste"
    elif any(word in text for word in ['communic', 'misunderstand', 'conflict', 'disagreement', 'communication', 'malentendu', 'conflit']):
        return "💬 Communication Issues"
    elif any(word in text for word in ['skill', 'train', 'knowledge', 'expertise', 'compétence', 'formation', 'connaissance']):
        return "🎓 Skill Gaps"
    elif any(word in text for word in ['tool', 'software', 'system', 'platform', 'outil', 'logiciel', 'système']):
        return "🛠️ Tool & System Issues"
    elif any(word in text for word in ['cost', 'expens', 'budget', 'overrun', 'coût', 'dépense', 'budget']):
        return "💰 Cost Issues"
    elif any(word in text for word in ['qualit', 'defect', 'inconsist', 'variance', 'qualité', 'défaut', 'incohérence']):
        return "📊 Quality Issues"
    elif any(word in text for word in ['manuel', 'manual', 'automat', 'automatique', 'automatization']):
        return "🤖 Manual vs Automation Issues"
    elif any(word in text for word in ['risque', 'risk', 'danger', 'dangerous', 'sécurité', 'security']):
        return "🛡️ Risk & Safety Issues"
    elif any(word in text for word in ['temps', 'time', 'perte', 'loss', 'waste', 'gaspillage']):
        return "⏱️ Time & Efficiency Issues"
    elif any(word in text for word in ['production', 'manufacturing', 'fabrication', 'planification', 'planning']):
        return "🏭 Production & Planning Issues"
    else:
        return "⚠️ Other Issues"

def generate_issues_opportunities_markdown(combined_tasks):
    """Generate a Markdown report focused on issues and opportunities."""
    
    markdown = f"""# Issues & Opportunities Report
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## 📋 Report Summary
- **Total Tasks Analyzed**: {len(combined_tasks)}
- **Focus**: Issues, Risks, and Improvement Opportunities

## 💡 Opportunities & Improvement Ideas

"""
    
    opportunities_found = False
    for task in combined_tasks:
        opportunities = task.get('opportunities', '')
        if opportunities and opportunities.strip():
            opportunities_found = True
            markdown += f"### 🚀 {task.get('name', 'Unknown')}\n"
            markdown += f"**Department**: {task.get('swimlane', 'Unknown')}\n"
            markdown += f"**Owner**: {task.get('task_owner', 'Unknown')}\n"
            markdown += f"**Current Cost**: ${task.get('total_cost', 0):.2f}\n"
            markdown += f"**Current Time**: {task.get('time_hours', 0):.2f} hours\n"
            markdown += f"**Status**: {task.get('task_status', 'Unknown')}\n"
            markdown += f"**Tools**: {task.get('tools_used', 'N/A')}\n\n"
            markdown += f"**Opportunity**: {opportunities}\n\n"
            markdown += "---\n\n"
    
    if not opportunities_found:
        markdown += "*No opportunities captured in the current data.*\n\n"
    
    markdown += "## ⚠️ Issues & Risks Analysis\n\n"
    
    issues_found = False
    for task in combined_tasks:
        issues_text = task.get('issues_text', '')
        issues_priority = task.get('issues_priority', '')
        if issues_text and issues_text.strip():
            issues_found = True
            markdown += f"### ⚠️ {task.get('name', 'Unknown')}\n"
            markdown += f"**Department**: {task.get('swimlane', 'Unknown')}\n"
            markdown += f"**Owner**: {task.get('task_owner', 'Unknown')}\n"
            markdown += f"**Priority**: {issues_priority}\n"
            markdown += f"**Current Cost**: ${task.get('total_cost', 0):.2f}\n"
            markdown += f"**Current Time**: {task.get('time_hours', 0):.2f} hours\n"
            markdown += f"**Status**: {task.get('task_status', 'Unknown')}\n"
            markdown += f"**Tools**: {task.get('tools_used', 'N/A')}\n\n"
            markdown += f"**Issue/Risk**: {issues_text}\n\n"
            markdown += "---\n\n"
    
    if not issues_found:
        markdown += "*No issues captured in the current data.*\n\n"
    
    # Summary table
    markdown += "## 📊 Summary Table\n\n"
    markdown += "| Type | Task Name | Department | Owner | Priority | Current Cost | Current Time |\n"
    markdown += "|------|-----------|------------|-------|----------|--------------|--------------|\n"
    
    for task in combined_tasks:
        # Add opportunities
        opportunities = task.get('opportunities', '')
        if opportunities and opportunities.strip():
            markdown += f"| 🚀 Opportunity | {task.get('name', 'Unknown')} | {task.get('swimlane', 'Unknown')} | {task.get('task_owner', 'Unknown')} | - | ${task.get('total_cost', 0):.2f} | {task.get('time_hours', 0):.2f}h |\n"
        
        # Add issues
        issues_text = task.get('issues_text', '')
        if issues_text and issues_text.strip():
            priority = task.get('issues_priority', 'Unknown')
            markdown += f"| ⚠️ Issue | {task.get('name', 'Unknown')} | {task.get('swimlane', 'Unknown')} | {task.get('task_owner', 'Unknown')} | {priority} | ${task.get('total_cost', 0):.2f} | {task.get('time_hours', 0):.2f}h |\n"
    
    markdown += f"\n---\n*Issues & Opportunities report generated by Inocta BPM Analysis*\n*Total tasks analyzed: {len(combined_tasks)}*\n"
    
    return markdown

def generate_faq_markdown(combined_tasks):
    """Generate a Markdown report focused on FAQ knowledge capture."""
    
    markdown = f"""# FAQ Knowledge Report
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## 📋 Report Summary
- **Total Tasks Analyzed**: {len(combined_tasks)}
- **Focus**: Frequently Asked Questions and Knowledge Capture

## ❓ FAQ Knowledge Base

"""
    
    faqs_found = False
    for task in combined_tasks:
        task_has_faqs = False
        
        for i in range(1, 4):
            q_key = f'faq_q{i}'
            a_key = f'faq_a{i}'
            question = task.get(q_key, '')
            answer = task.get(a_key, '')
            
            if question and question.strip() and answer and answer.strip():
                if not task_has_faqs:
                    markdown += f"### 📝 {task.get('name', 'Unknown')}\n"
                    markdown += f"**Department**: {task.get('swimlane', 'Unknown')}\n"
                    markdown += f"**Owner**: {task.get('task_owner', 'Unknown')}\n"
                    markdown += f"**Current Cost**: ${task.get('total_cost', 0):.2f}\n"
                    markdown += f"**Current Time**: {task.get('time_hours', 0):.2f} hours\n"
                    markdown += f"**Status**: {task.get('task_status', 'Unknown')}\n"
                    markdown += f"**Tools**: {task.get('tools_used', 'N/A')}\n\n"
                    task_has_faqs = True
                
                markdown += f"**Q{i}**: {question}\n"
                markdown += f"**A{i}**: {answer}\n\n"
                faqs_found = True
        
        if task_has_faqs:
            markdown += "---\n\n"
    
    if not faqs_found:
        markdown += "*No FAQs captured in the current data.*\n\n"
    
    # Summary table
    markdown += "## 📊 FAQ Summary Table\n\n"
    markdown += "| Task Name | Department | Owner | FAQ # | Question | Answer | Current Cost | Current Time |\n"
    markdown += "|-----------|------------|-------|-------|----------|---------|--------------|--------------|\n"
    
    for task in combined_tasks:
        for i in range(1, 4):
            q_key = f'faq_q{i}'
            a_key = f'faq_a{i}'
            question = task.get(q_key, '')
            answer = task.get(a_key, '')
            
            if question and question.strip() and answer and answer.strip():
                markdown += f"| {task.get('name', 'Unknown')} | {task.get('swimlane', 'Unknown')} | {task.get('task_owner', 'Unknown')} | {i} | {question[:50]}{'...' if len(question) > 50 else ''} | {answer[:50]}{'...' if len(answer) > 50 else ''} | ${task.get('total_cost', 0):.2f} | {task.get('time_hours', 0):.2f}h |\n"
    
    markdown += f"\n---\n*FAQ Knowledge report generated by Inocta BPM Analysis*\n*Total tasks analyzed: {len(combined_tasks)}*\n"
    
    return markdown

def generate_documentation_status_markdown(combined_tasks):
    """Generate a Markdown report focused on documentation status."""
    
    markdown = f"""# Documentation Status Report
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## 📋 Report Summary
- **Total Tasks Analyzed**: {len(combined_tasks)}
- **Focus**: Documentation Compliance and Status

## 📚 Documentation Status Analysis

"""
    
    # Group by documentation status
    doc_status_counts = {}
    for task in combined_tasks:
        doc_status = task.get('doc_status', 'Unknown')
        if doc_status not in doc_status_counts:
            doc_status_counts[doc_status] = 0
        doc_status_counts[doc_status] += 1
    
    markdown += "## 📊 Documentation Status Breakdown\n\n"
    markdown += "| Status | Count | Percentage |\n"
    markdown += "|--------|-------|------------|\n"
    
    total_tasks = len(combined_tasks)
    for status, count in doc_status_counts.items():
        percentage = (count / total_tasks * 100) if total_tasks > 0 else 0
        markdown += f"| {status} | {count} | {percentage:.1f}% |\n"
    
    markdown += "\n## 📝 Detailed Documentation Status\n\n"
    markdown += "| Task Name | Department | Owner | Doc Status | Doc URL | Current Cost | Current Time |\n"
    markdown += "|-----------|------------|-------|------------|---------|--------------|--------------|\n"
    
    for task in combined_tasks:
        markdown += f"| {task.get('name', 'Unknown')} | {task.get('swimlane', 'Unknown')} | {task.get('task_owner', 'Unknown')} | {task.get('doc_status', 'Unknown')} | {task.get('doc_url', 'N/A')} | ${task.get('total_cost', 0):.2f} | {task.get('time_hours', 0):.2f}h |\n"
    
    markdown += f"\n---\n*Documentation Status report generated by Inocta BPM Analysis*\n*Total tasks analyzed: {len(combined_tasks)}*\n"
    
    return markdown

def generate_tools_analysis_markdown(combined_tasks):
    """Generate a Markdown report focused on tools analysis."""
    
    markdown = f"""# Tools Analysis Report
*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## 📋 Report Summary
- **Total Tasks Analyzed**: {len(combined_tasks)}
- **Focus**: Tools Usage and Standardization Opportunities

## 🛠️ Tools Usage Analysis

"""
    
    # Group by tools
    tools_usage = {}
    for task in combined_tasks:
        tools = task.get('tools_used', '')
        if tools and tools.strip():
            tool_list = [tool.strip() for tool in tools.split(',') if tool.strip()]
            for tool in tool_list:
                if tool not in tools_usage:
                    tools_usage[tool] = {
                        'task_count': 0,
                        'total_cost': 0,
                        'total_time': 0,
                        'tasks': []
                    }
                
                tools_usage[tool]['task_count'] += 1
                tools_usage[tool]['total_cost'] += task.get('total_cost', 0)
                tools_usage[tool]['total_time'] += task.get('time_hours', 0)
                tools_usage[tool]['tasks'].append(task.get('name', 'Unknown'))
    
    markdown += "## 📊 Tools Usage Summary\n\n"
    markdown += "| Tool | Task Count | Total Cost | Total Time |\n"
    markdown += "|------|------------|------------|------------|\n"
    
    for tool, data in tools_usage.items():
        markdown += f"| {tool} | {data['task_count']} | ${data['total_cost']:.2f} | {data['total_time']:.2f}h |\n"
    
    markdown += "\n## 📝 Detailed Tools Usage\n\n"
    markdown += "| Task Name | Department | Owner | Tool Used | Original Tools Field | Current Cost | Current Time |\n"
    markdown += "|-----------|------------|-------|-----------|---------------------|--------------|--------------|\n"
    
    for task in combined_tasks:
        tools = task.get('tools_used', '')
        if tools and tools.strip():
            tool_list = [tool.strip() for tool in tools.split(',') if tool.strip()]
            for tool in tool_list:
                markdown += f"| {task.get('name', 'Unknown')} | {task.get('swimlane', 'Unknown')} | {task.get('task_owner', 'Unknown')} | {tool} | {tools} | ${task.get('total_cost', 0):.2f} | {task.get('time_hours', 0):.2f}h |\n"
        else:
            markdown += f"| {task.get('name', 'Unknown')} | {task.get('swimlane', 'Unknown')} | {task.get('task_owner', 'Unknown')} | No tools specified | N/A | ${task.get('total_cost', 0):.2f} | {task.get('time_hours', 0):.2f}h |\n"
    
    markdown += f"\n---\n*Tools Analysis report generated by Inocta BPM Analysis*\n*Total tasks analyzed: {len(combined_tasks)}*\n"
    
    return markdown

if __name__ == "__main__":
    main()
