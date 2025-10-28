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
                                parsed_task = self._parse_task(task, swimlane_name, task_type)
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
    
    def _parse_task(self, task: Dict, swimlane_name: str, task_type: str) -> Dict[str, Any]:
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
                'doc_url': camunda_properties.get('doc_url', '')
            }
            
        except Exception as e:
            # Log error but don't show it to user to avoid cluttering the interface
            print(f"Warning: Error parsing task {task.get('@id', 'Unknown')}: {str(e)}")
            # Return a minimal task object instead of None to avoid breaking the analysis
            return self._create_default_task(swimlane_name, task_type)
    
    def _create_default_task(self, swimlane_name: str, task_type: str) -> Dict[str, Any]:
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
            'doc_url': ''
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

def main():
    """
    Main Streamlit application for BPMN analysis.
    """
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
    

    
    st.title("📊 Inocta BPM Analysis")
    
    # Custom CSS to fix any display issues
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
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    This tool analyzes BPMN XML files to extract business insights, calculate costs, 
    and provide KPI analysis for process optimization.
    """)
    
    # Initialize analyzer
    analyzer = BPMNAnalyzer()
    
    # Sidebar for file upload
    st.sidebar.header("📁 File Upload")
    uploaded_files = st.sidebar.file_uploader(
        "Upload BPMN XML files",
        type=['xml', 'bpmn'],
        accept_multiple_files=True,
        help="Upload one or more BPMN XML files for analysis"
    )
    
    if uploaded_files:
        st.sidebar.success(f"✅ {len(uploaded_files)} file(s) uploaded")
        
        # Process each file
        all_analysis_data = []
        
        for uploaded_file in uploaded_files:
            st.sidebar.write(f"📄 {uploaded_file.name}")
            
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
        
        if all_analysis_data:
            # Display analysis results
            st.header("📈 Analysis Results")
            
            # Combine all data for overall analysis
            combined_tasks = []
            for data in all_analysis_data:
                combined_tasks.extend(data.get('tasks', []))
            
            if combined_tasks:
                # Overall summary
                total_cost = sum(task.get('total_cost', 0) for task in combined_tasks)
                total_time = sum(task.get('time_minutes', 0) for task in combined_tasks)
                total_tasks = len(combined_tasks)
                
                # Create summary metrics
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
                
                # Detailed analysis tabs
                tab_names = [
                    "📊 Executive Summary", 
                    "📋 Tasks Overview", 
                    "🏭 Swimlane Analysis", 
                    "👥 Owner Analysis", 
                    "📊 Status Analysis", 
                    "📚 Documentation Status", 
                    "🔧 Tools Analysis", 
                    "💡 Opportunities", 
                    "⚠️ Issues & Risks", 
                    "❓ FAQ Knowledge", 
                    "✅ Quality Control",
                    "💾 Export Data",
                    "❓ Help & Guide"
                ]
                
                tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13 = st.tabs(tab_names)
                
                with tab1:
                    st.subheader("📊 Executive Summary")
                    
                    # High-level KPIs
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Total Tasks", 
                            f"{len(combined_tasks):,}",
                            help="Total number of tasks across all processes"
                        )
                    
                    with col2:
                        total_cost = sum(task.get('total_cost', 0) for task in combined_tasks)
                        currencies = set(task.get('currency', 'Unknown') for task in combined_tasks if task.get('currency'))
                        currency_display = list(currencies)[0] if currencies else 'Unknown'
                        st.metric(
                            "Total Cost", 
                            f"{currency_display} {total_cost:,.2f}",
                            help="Total cost across all tasks"
                        )
                    
                    with col3:
                        total_time_hours = sum(task.get('time_minutes', 0) for task in combined_tasks) / 60
                        st.metric(
                            "Total Time", 
                            f"{total_time_hours:.1f} hrs",
                            help="Total estimated time across all tasks"
                        )
                    
                    with col4:
                        unique_swimlanes = len(set(task.get('swimlane', 'Unknown') for task in combined_tasks))
                        st.metric(
                            "Departments", 
                            f"{unique_swimlanes}",
                            help="Number of departments/swimlanes involved"
                        )
                    
                    # Summary charts row 1
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Cost distribution by department
                        swimlane_costs = {}
                        for task in combined_tasks:
                            swimlane = task.get('swimlane', 'Unknown')
                            if swimlane not in swimlane_costs:
                                swimlane_costs[swimlane] = 0
                            swimlane_costs[swimlane] += task.get('total_cost', 0)
                        
                        if swimlane_costs:
                            fig = px.pie(
                                values=list(swimlane_costs.values()),
                                names=list(swimlane_costs.keys()),
                                title="Cost Distribution by Department",
                                color_discrete_sequence=px.colors.qualitative.Set3
                            )
                            fig.update_traces(textposition='inside', textinfo='percent+label')
                            st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # Time distribution by department
                        swimlane_times = {}
                        for task in combined_tasks:
                            swimlane = task.get('swimlane', 'Unknown')
                            if swimlane not in swimlane_times:
                                swimlane_times[swimlane] = 0
                            swimlane_times[swimlane] += task.get('time_minutes', 0)
                        
                        if swimlane_times:
                            # Convert to hours for better readability
                            swimlane_hours = {k: v/60 for k, v in swimlane_times.items()}
                            fig = px.bar(
                                x=list(swimlane_hours.keys()),
                                y=list(swimlane_hours.values()),
                                title="Time Distribution by Department (Hours)",
                                color=list(swimlane_hours.values()),
                                color_continuous_scale='viridis'
                            )
                            fig.update_layout(xaxis_title="Department", yaxis_title="Hours")
                            st.plotly_chart(fig, use_container_width=True)
                    
                    # Summary charts row 2
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Task status overview
                        status_counts = {}
                        for task in combined_tasks:
                            status = task.get('task_status', 'Unknown')
                            if status not in status_counts:
                                status_counts[status] = 0
                            status_counts[status] += 1
                        
                        if status_counts:
                            fig = px.pie(
                                values=list(status_counts.values()),
                                names=list(status_counts.keys()),
                                title="Task Status Overview",
                                color_discrete_sequence=px.colors.qualitative.Pastel
                            )
                            fig.update_traces(textposition='inside', textinfo='percent+label')
                            st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # Documentation status overview
                        doc_status_counts = {}
                        for task in combined_tasks:
                            doc_status = task.get('doc_status', 'Unknown')
                            if doc_status not in doc_status_counts:
                                doc_status_counts[doc_status] = 0
                            doc_status_counts[doc_status] += 1
                        
                        if doc_status_counts:
                            fig = px.pie(
                                values=list(doc_status_counts.values()),
                                names=list(doc_status_counts.keys()),
                                title="Documentation Status Overview",
                                color_discrete_sequence=px.colors.qualitative.Set2
                            )
                            fig.update_traces(textposition='inside', textinfo='percent+label')
                            st.plotly_chart(fig, use_container_width=True)
                    
                    # Data Audit Results
                    st.markdown("### 🔍 Data Audit Results")
                    
                    # Calculate audit metrics
                    audit_results = {
                        'total_tasks': len(combined_tasks),
                        'tasks_with_missing_data': 0,
                        'missing_swimlanes': 0,
                        'missing_owners': 0,
                        'missing_time': 0,
                        'missing_cost': 0,
                        'calculation_errors': 0
                    }
                    
                    for task in combined_tasks:
                        if not task.get('swimlane') or task.get('swimlane') == 'Unknown':
                            audit_results['missing_swimlanes'] += 1
                            audit_results['tasks_with_missing_data'] += 1
                        if not task.get('task_owner'):
                            audit_results['missing_owners'] += 1
                            audit_results['tasks_with_missing_data'] += 1
                        if not task.get('time_hhmm'):
                            audit_results['missing_time'] += 1
                            audit_results['tasks_with_missing_data'] += 1
                        # Check if cost_per_hour is missing (not just 0)
                        cost_per_hour = task.get('cost_per_hour')
                        if cost_per_hour is None or cost_per_hour == '':
                            audit_results['missing_cost'] += 1
                            audit_results['tasks_with_missing_data'] += 1
                        
                        # Verify cost calculations
                        time_minutes = task.get('time_minutes', 0)
                        cost_per_hour = task.get('cost_per_hour', 0)
                        calculated_cost = (time_minutes / 60) * cost_per_hour
                        actual_cost = task.get('total_cost', 0)
                        if abs(calculated_cost - actual_cost) > 0.01:
                            audit_results['calculation_errors'] += 1
                    
                    # Health check calculations
                    def calculate_documentation_health(combined_tasks):
                        """Calculate documentation health metrics"""
                        total_tasks = len(combined_tasks)
                        tasks_needing_docs = [task for task in combined_tasks 
                                             if task.get('doc_status') in ['Not Documented', 
                                                                          'In Process to be Documented']]
                        tasks_requiring_count = len(tasks_needing_docs)
                        tasks_documented = [task for task in combined_tasks 
                                          if task.get('doc_status') == 'Documented']
                        tasks_documented_count = len(tasks_documented)
                        
                        if total_tasks > 0:
                            health_percentage = (tasks_documented_count / total_tasks) * 100
                        else:
                            health_percentage = 0
                        
                        return {
                            'total_tasks': total_tasks,
                            'tasks_requiring_documentation': tasks_requiring_count,
                            'tasks_documented': tasks_documented_count,
                            'health_percentage': health_percentage,
                            'health_status': 'Excellent' if health_percentage >= 90 
                                           else 'Good' if health_percentage >= 75 
                                           else 'Fair' if health_percentage >= 50 
                                           else 'Poor'
                        }
                    
                    def calculate_attention_health(combined_tasks):
                        """Calculate attention tasks health metrics"""
                        total_tasks = len(combined_tasks)
                        attention_count = 0
                        
                        for task in combined_tasks:
                            needs_attention = False
                            if not task.get('swimlane') or task.get('swimlane') == 'Unknown':
                                needs_attention = True
                            if not task.get('task_owner'):
                                needs_attention = True
                            if not task.get('time_hhmm'):
                                needs_attention = True
                            if task.get('doc_status') in ['Not Documented', 'In Process to be Documented']:
                                needs_attention = True
                            
                            if needs_attention:
                                attention_count += 1
                        
                        if total_tasks > 0:
                            health_percentage = ((total_tasks - attention_count) / total_tasks) * 100
                        else:
                            health_percentage = 0
                        
                        return {
                            'total_tasks': total_tasks,
                            'tasks_requiring_attention': attention_count,
                            'health_percentage': health_percentage,
                            'health_status': 'Excellent' if health_percentage >= 90 
                                           else 'Good' if health_percentage >= 75 
                                           else 'Fair' if health_percentage >= 50 
                                           else 'Poor'
                        }
                    
                    # Calculate health scores
                    doc_health = calculate_documentation_health(combined_tasks)
                    attention_health = calculate_attention_health(combined_tasks)
                    
                    # Store in session state for later use
                    st.session_state['audit_results'] = audit_results
                    st.session_state['doc_health'] = doc_health
                    st.session_state['attention_health'] = attention_health
                    
                    # Display audit results
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if audit_results['tasks_with_missing_data'] == 0:
                            st.success(f"✅ Data Quality: {100 - (audit_results['tasks_with_missing_data']/audit_results['total_tasks']*100):.1f}%")
                        else:
                            st.warning(f"⚠️ Data Quality: {100 - (audit_results['tasks_with_missing_data']/audit_results['total_tasks']*100):.1f}%")
                        
                        if audit_results['missing_swimlanes'] > 0:
                            st.metric("Missing Swimlanes", audit_results['missing_swimlanes'])
                        if audit_results['missing_owners'] > 0:
                            st.metric("Missing Owners", audit_results['missing_owners'])
                    
                    with col2:
                        if audit_results['missing_time'] > 0:
                            st.metric("Missing Time Estimates", audit_results['missing_time'])
                        if audit_results['missing_cost'] > 0:
                            st.metric("Missing Cost Data", audit_results['missing_cost'])
                    
                    with col3:
                        if audit_results['calculation_errors'] > 0:
                            st.error(f"❌ Calculation Errors: {audit_results['calculation_errors']}")
                        else:
                            st.success("✅ All Calculations Correct")
                    
                    # Health check metrics
                    st.markdown("### 🏥 Process Health Checks")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if doc_health['health_status'] == 'Excellent':
                            st.success(f"📚 Documentation Health: {doc_health['health_percentage']:.1f}%")
                        elif doc_health['health_status'] == 'Good':
                            st.warning(f"📚 Documentation Health: {doc_health['health_percentage']:.1f}%")
                        else:
                            st.error(f"📚 Documentation Health: {doc_health['health_percentage']:.1f}%")
                        
                        st.metric(
                            "Tasks Requiring Documentation",
                            f"{doc_health['tasks_requiring_documentation']}/{doc_health['total_tasks']}"
                        )
                    
                    with col2:
                        if attention_health['health_status'] == 'Excellent':
                            st.success(f"⚠️ Attention Health: {attention_health['health_percentage']:.1f}%")
                        elif attention_health['health_status'] == 'Good':
                            st.warning(f"⚠️ Attention Health: {attention_health['health_percentage']:.1f}%")
                        else:
                            st.error(f"⚠️ Attention Health: {attention_health['health_percentage']:.1f}%")
                        
                        st.metric(
                            "Tasks Requiring Attention",
                            f"{attention_health['tasks_requiring_attention']}/{attention_health['total_tasks']}"
                        )
                    
                    st.markdown("---")
                    
                    # Key insights and recommendations
                    st.subheader("🔍 Key Insights & Recommendations")
                    
                    # Calculate insights
                    total_tasks = len(combined_tasks)
                    tasks_with_issues = sum(1 for task in combined_tasks if not task.get('doc_status') or not task.get('task_status') or not task.get('time_hhmm'))
                    completion_rate = ((total_tasks - tasks_with_issues) / total_tasks * 100) if total_tasks > 0 else 0
                    
                    # Top cost centers
                    swimlane_costs_sorted = sorted(swimlane_costs.items(), key=lambda x: x[1], reverse=True)
                    top_cost_center = swimlane_costs_sorted[0] if swimlane_costs_sorted else ('Unknown', 0)
                    
                    # Top time consumers
                    swimlane_times_sorted = sorted(swimlane_times.items(), key=lambda x: x[1], reverse=True)
                    top_time_consumer = swimlane_times_sorted[0] if swimlane_times_sorted else ('Unknown', 0)
                    
                    # Display insights
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.info(f"**Data Quality Score: {completion_rate:.1f}%**")
                        if completion_rate < 80:
                            st.warning("⚠️ Consider improving data completeness for better analysis")
                        else:
                            st.success("✅ Good data quality for analysis")
                        
                        st.info(f"**Top Cost Center: {top_cost_center[0]}**")
                        st.write(f"*{currency_display} {top_cost_center[1]:,.2f}*")
                        
                        if top_cost_center[1] > total_cost * 0.3:
                            st.warning("⚠️ This department represents over 30% of total costs")
                    
                    with col2:
                        st.info(f"**Top Time Consumer: {top_time_consumer[0]}**")
                        st.write(f"*{top_time_consumer[1]/60:.1f} hours*")
                        
                        if top_time_consumer[1] > sum(swimlane_times.values()) * 0.3:
                            st.warning("⚠️ This department represents over 30% of total time")
                        
                        # Resource efficiency
                        avg_cost_per_hour = total_cost / (total_time_hours) if total_time_hours > 0 else 0
                        st.info(f"**Average Cost per Hour: {currency_display} {avg_cost_per_hour:.2f}**")
                    

                
                with tab2:
                    st.subheader("Tasks Overview")
                    
                    # Create tasks dataframe
                    tasks_df = pd.DataFrame(combined_tasks)
                    
                    # Filter options
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        swimlane_filter = st.selectbox(
                            "Filter by Swimlane/Department",
                            ["All"] + list(tasks_df['swimlane'].unique())
                        )
                    
                    with col2:
                        owner_filter = st.selectbox(
                            "Filter by Owner",
                            ["All"] + list(tasks_df['task_owner'].unique())
                        )
                    
                    with col3:
                        status_filter = st.selectbox(
                            "Filter by Status",
                            ["All"] + list(tasks_df['task_status'].unique())
                        )
                    
                    # Apply filters
                    filtered_df = tasks_df.copy()
                    
                    if swimlane_filter != "All":
                        filtered_df = filtered_df[filtered_df['swimlane'] == swimlane_filter]
                    
                    if owner_filter != "All":
                        filtered_df = filtered_df[filtered_df['task_owner'] == owner_filter]
                    
                    if status_filter != "All":
                        filtered_df = filtered_df[filtered_df['task_status'] == status_filter]
                    
                    # Create a copy of filtered_df for display formatting
                    display_df = filtered_df.copy()
                    
                    # Format doc_url for better display - show clickable links
                    def format_doc_url(url):
                        if pd.isna(url) or url == '' or url == 'Unknown':
                            return 'No URL'
                        # Truncate long URLs for display
                        if len(str(url)) > 50:
                            return f"{str(url)[:47]}..."
                        return str(url)
                    
                    # Format doc_status for better display with emojis
                    def format_doc_status(status):
                        if pd.isna(status) or status == '' or status == 'Unknown':
                            return '📋 Unknown'
                        status_lower = str(status).lower()
                        if 'complete' in status_lower or 'done' in status_lower or 'finished' in status_lower:
                            return '✅ Complete'
                        elif 'in progress' in status_lower or 'progress' in status_lower:
                            return '🔄 In Progress'
                        elif 'pending' in status_lower or 'waiting' in status_lower:
                            return '⏳ Pending'
                        elif 'not started' in status_lower or 'not started' in status_lower:
                            return '🚫 Not Started'
                        elif 'draft' in status_lower:
                            return '📝 Draft'
                        else:
                            return f'📋 {status}'
                    
                    # Apply formatting to columns
                    display_df['doc_url_display'] = display_df['doc_url'].apply(format_doc_url)
                    display_df['doc_status_display'] = display_df['doc_status'].apply(format_doc_status)
                    
                    # Display filtered data with formatted columns
                    st.dataframe(
                        display_df[['name', 'task_description', 'swimlane', 'task_owner', 'time_display', 'total_cost', 'currency', 'task_status', 'doc_status_display', 'doc_url_display']],
                        use_container_width=True,
                        column_config={
                            "task_description": st.column_config.TextColumn(
                                "Task Description",
                                help="Description of what the task involves",
                                max_chars=60
                            ),
                            "doc_status_display": st.column_config.TextColumn(
                                "Documentation Status",
                                help="Current status of task documentation",
                                max_chars=20
                            ),
                            "doc_url_display": st.column_config.LinkColumn(
                                "Documentation URL",
                                help="Click to open documentation link",
                                max_chars=50
                            )
                        }
                    )
                    
                    # Add clickable links below the table for better user experience
                    st.markdown("**📚 Documentation Links:**")
                    for idx, row in display_df.iterrows():
                        if pd.notna(row['doc_url']) and row['doc_url'] != '' and row['doc_url'] != 'Unknown':
                            st.markdown(f"- **{row['name']}**: [Open Documentation]({row['doc_url']})")
                    
                    # Add summary totals row
                    if not filtered_df.empty:
                        total_tasks = len(filtered_df)
                        total_time_hours = filtered_df['time_hours'].sum()
                        total_cost = filtered_df['total_cost'].sum()
                        
                        # Format time display for summary
                        total_hours_int = int(total_time_hours)
                        total_minutes = int((total_time_hours - total_hours_int) * 60)
                        time_display = f"{total_hours_int:02d}:{total_minutes:02d}"
                        
                        st.markdown("---")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Tasks", total_tasks)
                        with col2:
                            st.metric("Total Time", f"{time_display} ({total_time_hours:.2f} hrs)")
                        with col3:
                            st.metric("Total Cost", f"${total_cost:,.2f}")
                        with col4:
                            st.metric("Avg Cost/Task", f"${total_cost/total_tasks:,.2f}" if total_tasks > 0 else "$0.00")
                        
                        # Validation message - compare with grand total from combined_tasks
                        grand_total_time = sum(task.get('time_hours', 0) for task in combined_tasks)
                        if abs(total_time_hours - grand_total_time) < 0.01:
                            st.success("✅ Table totals match grand total")
                        else:
                            st.warning(f"⚠️ Table total ({total_time_hours:.2f} hrs) differs from grand total ({grand_total_time:.2f} hrs)")
                        
                        # Documentation summary
                        st.markdown("---")
                        st.markdown("**📚 Documentation Summary:**")
                        
                        # Count documentation statuses
                        doc_status_counts = display_df['doc_status'].value_counts()
                        total_tasks_with_docs = len(display_df[display_df['doc_status'] != 'Unknown'])
                        total_tasks_with_urls = len(display_df[display_df['doc_url'].notna() & (display_df['doc_url'] != '') & (display_df['doc_url'] != 'Unknown')])
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Tasks with Documentation", f"{total_tasks_with_docs}/{total_tasks}")
                        with col2:
                            st.metric("Tasks with URLs", f"{total_tasks_with_urls}/{total_tasks}")
                        with col3:
                            completion_rate = (total_tasks_with_docs / total_tasks * 100) if total_tasks > 0 else 0
                            st.metric("Documentation Coverage", f"{completion_rate:.1f}%")
                        
                        # Show documentation status breakdown
                        if not doc_status_counts.empty:
                            st.markdown("**Documentation Status Breakdown:**")
                            for status, count in doc_status_counts.items():
                                if status != 'Unknown':
                                    percentage = (count / total_tasks * 100) if total_tasks > 0 else 0
                                    st.markdown(f"- **{status}**: {count} tasks ({percentage:.1f}%)")
                
                with tab3:
                    st.subheader("Swimlane/Department Analysis")
                    
                    # Group by swimlane
                    swimlane_analysis = {}
                    for task in combined_tasks:
                        swimlane = task.get('swimlane', 'Unknown')
                        if swimlane not in swimlane_analysis:
                            swimlane_analysis[swimlane] = {
                                'task_count': 0,
                                'total_cost': 0,
                                'total_time_minutes': 0
                            }
                        
                        swimlane_analysis[swimlane]['task_count'] += 1
                        swimlane_analysis[swimlane]['total_cost'] += task.get('total_cost', 0)
                        swimlane_analysis[swimlane]['total_time_minutes'] += task.get('time_minutes', 0)
                    
                    # Create swimlane analysis dataframe
                    swimlane_df = pd.DataFrame(swimlane_analysis).T.reset_index()
                    # Rename columns to match expected structure
                    swimlane_df.columns = ['Swimlane/Department', 'Task Count', 'Total Cost', 'total_time_minutes']
                    # Calculate hours from minutes
                    swimlane_df['Total Time (hrs)'] = swimlane_df['total_time_minutes'] / 60
                    # Rename the minutes column for display
                    swimlane_df = swimlane_df.rename(columns={'total_time_minutes': 'Total Time (min)'})
                    
                    st.dataframe(swimlane_df, use_container_width=True)
                    
                    # Swimlane cost chart
                    fig = px.bar(
                        swimlane_df,
                        x='Swimlane/Department',
                        y='Total Cost',
                        title='Total Cost by Swimlane/Department',
                        color='Task Count',
                        color_continuous_scale='viridis'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab4:
                    st.subheader("Owner Analysis")
                    
                    # Group by owner
                    owner_analysis = {}
                    for task in combined_tasks:
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
                    
                    # Create owner analysis dataframe
                    owner_df = pd.DataFrame(owner_analysis).T.reset_index()
                    # Rename columns to match expected structure
                    owner_df.columns = ['Owner', 'Task Count', 'Total Cost', 'total_time_minutes']
                    # Calculate hours from minutes
                    owner_df['Total Time (hrs)'] = owner_df['total_time_minutes'] / 60
                    # Rename the minutes column for display
                    owner_df = owner_df.rename(columns={'total_time_minutes': 'Total Time (min)'})
                    
                    st.dataframe(owner_df, use_container_width=True)
                    
                    # Owner workload chart
                    fig = px.pie(
                        owner_df,
                        values='Task Count',
                        names='Owner',
                        title='Task Distribution by Owner'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab5:
                    st.subheader("📊 Status Analysis")
                    
                    # Status analysis
                    status_analysis = {}
                    for task in combined_tasks:
                        status = task.get('task_status', 'Unknown')
                        if status not in status_analysis:
                            status_analysis[status] = {
                                'task_count': 0,
                                'total_cost': 0
                            }
                        
                        status_analysis[status]['task_count'] += 1
                        status_analysis[status]['total_cost'] += task.get('total_cost', 0)
                    
                    status_df = pd.DataFrame(status_analysis).T.reset_index()
                    status_df.columns = ['Status', 'Task Count', 'Total Cost']
                    
                    # Display status summary
                    st.write("**Task Status Summary**")
                    st.dataframe(status_df, use_container_width=True)
                    
                    # Create two columns for charts
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Bar chart for task status
                        fig = px.bar(
                            status_df,
                            x='Status',
                            y='Task Count',
                            title='Tasks by Status',
                            color='Task Count',
                            color_continuous_scale='viridis'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # Pie chart for task status
                        fig = px.pie(
                            status_df,
                            values='Task Count',
                            names='Status',
                            title='Task Status Distribution',
                            color_discrete_sequence=px.colors.qualitative.Set3
                        )
                        fig.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Tasks requiring attention table
                    st.markdown("---")
                    st.write("**⚠️ Tasks Requiring Attention**")
                    
                    # Filter tasks that require attention
                    attention_tasks = [task for task in combined_tasks if task.get('task_status', '').lower() in ['requires attention', 'pending', 'blocked', 'issue']]
                    
                    if attention_tasks:
                        attention_df = pd.DataFrame(attention_tasks)
                        # Select relevant columns for display
                        display_columns = ['name', 'swimlane', 'task_owner', 'time_display', 'total_cost', 'currency', 'task_status']
                        available_columns = [col for col in display_columns if col in attention_df.columns]
                        
                        st.dataframe(
                            attention_df[available_columns],
                            use_container_width=True,
                            column_config={
                                "task_status": st.column_config.TextColumn(
                                    "Status",
                                    help="Current status of the task",
                                    max_chars=20
                                )
                            }
                        )
                        
                        # Summary of attention tasks
                        total_attention_cost = sum(task.get('total_cost', 0) for task in attention_tasks)
                        total_attention_time = sum(task.get('time_hours', 0) for task in attention_tasks)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Tasks Requiring Attention", len(attention_tasks))
                        with col2:
                            st.metric("Total Cost at Risk", f"${total_attention_cost:,.2f}")
                        with col3:
                            st.metric("Total Time at Risk", f"{total_attention_time:.1f} hrs")
                    else:
                        st.success("🎉 All tasks are in good status! No tasks require attention.")
                
                with tab6:
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
                        if task.get('doc_url') and task.get('doc_url') != '' and task.get('doc_url') != 'NR':
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
                    
                    # Display high-level documentation metrics
                    st.markdown("**🎯 Documentation State of the Nation**")
                    
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
                        total_in_process = doc_status_analysis.get('In Process to be Documented', {}).get('task_count', 0)
                        st.metric(
                            "🔄 In Process", 
                            f"{total_in_process}/{total_tasks}",
                            f"{total_in_process/total_tasks*100:.1f}%" if total_tasks > 0 else "0%"
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
                        # Add filter by documentation status
                        unique_statuses = list(set(task.get('doc_status', 'Unknown') for task in tasks_needing_docs))
                        unique_statuses.sort()
                        
                        filter_col1, filter_col2 = st.columns([1, 3])
                        with filter_col1:
                            selected_status = st.selectbox(
                                "🔍 Filter by Documentation Status:",
                                options=['All Statuses'] + unique_statuses,
                                key='doc_attention_filter'
                            )
                        
                        # Apply filter if status is selected
                        if selected_status == 'All Statuses':
                            filtered_tasks = tasks_needing_docs
                        else:
                            filtered_tasks = [task for task in tasks_needing_docs 
                                            if task.get('doc_status') == selected_status]
                        
                        if filtered_tasks:
                            attention_df = pd.DataFrame(filtered_tasks)
                            display_columns = ['name', 'swimlane', 'task_owner', 'doc_status', 'doc_url', 'time_display', 'total_cost']
                            available_columns = [col for col in display_columns if col in attention_df.columns]
                            
                            st.dataframe(
                                attention_df[available_columns],
                                use_container_width=True,
                                column_config={
                                    "doc_status": st.column_config.TextColumn(
                                        "Documentation Status",
                                        help="Current documentation status",
                                        max_chars=30
                                    ),
                                    "doc_url": st.column_config.LinkColumn(
                                        "Documentation URL",
                                        help="Click to open documentation link",
                                        max_chars=50
                                    )
                                }
                            )
                        else:
                            st.info(f"No tasks found with status: '{selected_status}'")
                        
                        # Update summary metrics based on filtered results
                        
                        # Summary of documentation attention needed (showing filtered results)
                        total_attention_cost = sum(task.get('total_cost', 0) for task in filtered_tasks)
                        total_attention_time = sum(task.get('time_hours', 0) for task in filtered_tasks)
                        
                        st.markdown(f"**Showing: {len(filtered_tasks)} of {len(tasks_needing_docs)} tasks requiring documentation**")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Tasks Needing Docs", len(filtered_tasks))
                        with col2:
                            st.metric("Total Cost at Risk", f"${total_attention_cost:,.2f}")
                        with col3:
                            st.metric("Total Time at Risk", f"{total_attention_time:.1f} hrs")
                    else:
                        st.success("🎉 All tasks are properly documented! No documentation attention needed.")
                
                with tab7:
                    st.subheader("Tools Analysis")
                    
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
                        
                        # Display enhanced tools analysis
                        st.subheader("📊 Individual Tools Analysis")
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
                
                with tab8:
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
                        
                        # Display categorized opportunities
                        st.subheader("📊 Opportunities by Category")
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
                
                with tab9:
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
                        
                        # Display categorized issues
                        st.subheader("📊 Issues by Category")
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
                
                with tab10:
                    st.subheader("❓ FAQ Knowledge Analysis")
                    
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
                
                with tab11:
                    st.subheader("✅ Quality Control")
                    
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
                            if not doc_url or doc_url == '' or doc_url == 'NR':
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
                
                with tab12:
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
                                        return
                                
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
                                        return
                                
                                elif export_scope == "Documentation Status Only":
                                    # Export only documentation status data
                                    doc_status_data = []
                                    for task in combined_tasks:
                                        doc_status_data.append({
                                            'Task Name': task.get('name', 'Unknown'),
                                            'Department': task.get('swimlane', 'Unknown'),
                                            'Owner': task.get('task_owner', 'Unknown'),
                                            'Documentation Status': task.get('doc_status', 'Unknown'),
                                            'Documentation URL': task.get('doc_url', 'N/A'),
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
                                        return
                                
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
                                        return
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
                                        return
                                
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
                                        return
                                
                                elif export_scope == "Documentation Status Only":
                                    # Export only documentation status data
                                    doc_status_data = []
                                    for task in combined_tasks:
                                        doc_status_data.append({
                                            'Task Name': task.get('name', 'Unknown'),
                                            'Department': task.get('swimlane', 'Unknown'),
                                            'Owner': task.get('task_owner', 'Unknown'),
                                            'Documentation Status': task.get('doc_status', 'Unknown'),
                                            'Documentation URL': task.get('doc_url', 'N/A'),
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
                                        return
                                
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
                                        return
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
                                        return
                                
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
                                        return
                                
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
                                            'documentation_url': task.get('doc_url', 'N/A'),
                                            'current_cost': task.get('total_cost', 0),
                                            'current_time_hours': task.get('time_hours', 0),
                                            'status': task.get('task_status', 'Unknown'),
                                            'tools_used': task.get('tools_used', 'N/A')
                                        })
                                    
                                    if doc_status_data:
                                        json_data = json.dumps(doc_status_data, indent=2, default=str)
                                    else:
                                        st.warning("⚠️ No documentation status data found")
                                        return
                                
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
                                        return
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
                            st.info("📝 **Markdown Export**: Professional report with tables, sections, and formatted data - perfect for documentation and sharing!")
                        
                    elif export_scope == "Tasks Only":
                        st.write("**Tasks Export includes:**")
                        st.write("• Raw task data with all metadata fields")
                        st.write("• Time, cost, and currency information")
                        st.write("• Owner, status, and documentation details")
                        st.write("• Tools, opportunities, and issues")
                        st.write("• FAQ questions and answers")
                        
                        if export_format == "Markdown (.md)":
                            st.info("📝 **Markdown Export**: Clean table format with all task details - ideal for task management and review!")
                        
                    elif export_scope == "Issues & Opportunities Only":
                        st.write("**Issues & Opportunities Export includes:**")
                        st.write("• All captured opportunities and improvement ideas")
                        st.write("• All identified issues and risks")
                        st.write("• Task context (name, department, owner)")
                        st.write("• Current cost and time impact")
                        st.write("• Priority levels for issues")
                        st.write("• Status and tools information")
                        
                        if export_format == "Markdown (.md)":
                            st.info("📝 **Markdown Export**: Focused report on improvement areas and risks - perfect for action planning and stakeholder communication!")
                    
                    elif export_scope == "FAQ Knowledge Only":
                        st.write("**FAQ Knowledge Export includes:**")
                        st.write("• All captured FAQ questions and answers")
                        st.write("• Task context (name, department, owner)")
                        st.write("• FAQ numbering and organization")
                        st.write("• Current cost and time impact")
                        st.write("• Status and tools information")
                        st.write("• Placeholder rows for tasks without FAQs")
                        
                        if export_format == "Markdown (.md)":
                            st.info("📝 **Markdown Export**: Knowledge base format with Q&A pairs - perfect for training and documentation!")
                    
                    elif export_scope == "Documentation Status Only":
                        st.write("**Documentation Status Export includes:**")
                        st.write("• Documentation status for all tasks")
                        st.write("• Documentation URLs and links")
                        st.write("• Task context (name, department, owner)")
                        st.write("• Current cost and time impact")
                        st.write("• Status and tools information")
                        st.write("• Complete documentation audit trail")
                        
                        if export_format == "Markdown (.md)":
                            st.info("📝 **Markdown Export**: Documentation compliance report - perfect for governance and audit purposes!")
                    
                    elif export_scope == "Tools Analysis Only":
                        st.write("**Tools Analysis Export includes:**")
                        st.write("• Individual tools used across all tasks")
                        st.write("• Original tools field for cleanup reference")
                        st.write("• Task context (name, department, owner)")
                        st.write("• Current cost and time impact")
                        st.write("• Status information")
                        st.write("• Tools standardization opportunities")
                        
                        if export_format == "Markdown (.md)":
                            st.info("📝 **Markdown Export**: Tools usage analysis - perfect for IT planning and tool standardization!")
                    
                    else:  # Summary Only
                        st.write("**Summary Export includes:**")
                        st.write("• Key performance indicators")
                        st.write("• Total counts and metrics")
                        st.write("• High-level insights")
                        st.write("• Executive summary data")
                        
                        if export_format == "Markdown (.md)":
                            st.info("📝 **Markdown Export**: Executive summary with key metrics and insights - perfect for presentations and reports!")
                    
                    # Show sample data structure
                    if combined_tasks:
                        st.subheader("📋 Sample Data Structure")
                        
                        # Create an ideal, fictional example that showcases all features
                        ideal_sample_task = {
                            "id": "Activity_ideal_001",
                            "name": "Strategic Planning Workshop",
                            "swimlane": "Business Development",
                            "type": "task",
                            "time_hhmm": "8:00",
                            "time_display": "08:00",
                            "time_minutes": 480,
                            "time_hours": 8.0,
                            "cost_per_hour": 200,
                            "currency": "USD",
                            "other_costs": 500,
                            "labor_cost": 1600,
                            "total_cost": 2100,
                            "task_owner": "Sarah Johnson",
                            "task_description": "Facilitate strategic planning session with key stakeholders to define company roadmap and growth objectives for the next fiscal year",
                            "task_status": "In Progress",
                            "doc_status": "Documentation In Progress",
                            "tools_used": "Miro, Zoom, Google Workspace, Strategy Canvas",
                            "opportunities": "Potential to standardize planning methodology across departments and create reusable templates for future planning cycles",
                            "issues_text": "Stakeholder availability conflicts may delay workshop completion",
                            "issues_priority": "Medium",
                            "faq_q1": "What is the expected outcome of this workshop?",
                            "faq_a1": "A comprehensive strategic roadmap with clear objectives, timelines, and success metrics for the upcoming fiscal year",
                            "faq_q2": "How often should strategic planning sessions be conducted?",
                            "faq_a2": "Annually with quarterly review sessions to ensure alignment and adjust priorities as needed",
                            "faq_q3": "Who should participate in strategic planning?",
                            "faq_a3": "C-level executives, department heads, and key stakeholders from all business units",
                            "task_industry": "Strategic Management",
                            "doc_url": "https://company-wiki.com/strategic-planning/workshop-2024"
                        }
                        
                        st.json(ideal_sample_task)
                        
                        st.info("💡 **This is an ideal example showing all available features. Your actual data may have different values and field completeness.**")
                
                with tab13:
                    st.subheader("❓ Help & Guide")
                    
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
    
    else:
        st.info("👆 Please upload BPMN XML files using the sidebar to begin analysis.")
        
        # Show example structure
        st.header("📋 Expected BPMN Structure")
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

# Main function ends here
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
