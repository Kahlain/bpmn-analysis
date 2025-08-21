#!/usr/bin/env python3
"""
Demo script showing how to use the BPMN Analyzer programmatically.
This script demonstrates the core functionality without the Streamlit UI.
"""

import os
from bpmn_analyzer import BPMNAnalyzer

def demo_analysis():
    """Demonstrate BPMN analysis functionality."""
    print("🚀 BPMN Business Analysis Tool - Demo Mode")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = BPMNAnalyzer()
    
    # Check if we have any BPMN files in the current directory
    bpmn_files = [f for f in os.listdir('.') if f.endswith(('.xml', '.bpmn'))]
    
    if not bpmn_files:
        print("❌ No BPMN files found in current directory.")
        print("Please place some .xml or .bpmn files in this folder.")
        return
    
    print(f"📁 Found {len(bpmn_files)} BPMN file(s):")
    for file in bpmn_files:
        print(f"   - {file}")
    
    print("\n🔍 Analyzing files...")
    
    # Analyze each file
    all_analysis_data = []
    
    for filename in bpmn_files:
        print(f"\n📄 Analyzing {filename}...")
        
        try:
            # Read file content
            with open(filename, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Parse BPMN file
            parsed_data = analyzer.parse_bpmn_file(file_content)
            
            if parsed_data:
                # Analyze business insights
                analysis_data = analyzer.analyze_business_insights(parsed_data)
                analysis_data['filename'] = filename
                all_analysis_data.append(analysis_data)
                
                print(f"   ✅ Successfully analyzed {filename}")
                
                # Show summary
                summary = analysis_data.get('summary', {})
                if summary:
                    print(f"   📊 Summary:")
                    print(f"      - Total Tasks: {summary.get('total_tasks', 0)}")
                    print(f"      - Total Cost: ${summary.get('total_cost', 0):,.2f}")
                    print(f"      - Total Time: {summary.get('total_time_hours', 0):.1f} hours")
                    print(f"      - Currencies: {', '.join(summary.get('currencies', []))}")
            else:
                print(f"   ❌ Failed to analyze {filename}")
                
        except Exception as e:
            print(f"   ❌ Error analyzing {filename}: {str(e)}")
    
    if all_analysis_data:
        print("\n🎯 Overall Analysis Summary")
        print("=" * 50)
        
        # Combine all data
        combined_tasks = []
        for data in all_analysis_data:
            combined_tasks.extend(data.get('tasks', []))
        
        if combined_tasks:
            total_cost = sum(task.get('total_cost', 0) for task in combined_tasks)
            total_time = sum(task.get('time_minutes', 0) for task in combined_tasks)
            total_tasks = len(combined_tasks)
            
            print(f"📋 Total Tasks: {total_tasks}")
            print(f"💰 Total Cost: ${total_cost:,.2f}")
            print(f"⏱️  Total Time: {total_time/60:.1f} hours")
            
            # Show process breakdown
            print("\n🏭 Process Breakdown:")
            process_analysis = {}
            for task in combined_tasks:
                process = task.get('process', 'Unknown')
                if process not in process_analysis:
                    process_analysis[process] = {'count': 0, 'cost': 0}
                
                process_analysis[process]['count'] += 1
                process_analysis[process]['cost'] += task.get('total_cost', 0)
            
            for process, data in process_analysis.items():
                print(f"   - {process}: {data['count']} tasks, ${data['cost']:,.2f}")
            
            # Show owner breakdown
            print("\n👥 Owner Breakdown:")
            owner_analysis = {}
            for task in combined_tasks:
                owner = task.get('task_owner', 'Unknown')
                if owner not in owner_analysis:
                    owner_analysis[owner] = {'count': 0, 'cost': 0}
                
                owner_analysis[owner]['count'] += 1
                owner_analysis[owner]['cost'] += task.get('total_cost', 0)
            
            for owner, data in owner_analysis.items():
                print(f"   - {owner}: {data['count']} tasks, ${data['cost']:,.2f}")
            
            # Generate Excel report
            print("\n💾 Generating Excel Report...")
            combined_analysis = {
                'summary': {
                    'total_tasks': total_tasks,
                    'total_cost': total_cost,
                    'total_time_minutes': total_time,
                    'total_time_hours': total_time / 60,
                    'files_analyzed': len(all_analysis_data)
                },
                'tasks': combined_tasks,
                'process_analysis': process_analysis,
                'owner_analysis': owner_analysis
            }
            
            filename = analyzer.generate_excel_report(combined_analysis)
            if filename:
                print(f"   ✅ Excel report generated: {filename}")
            else:
                print("   ❌ Failed to generate Excel report")
        
        print("\n🎉 Demo completed successfully!")
        print("To use the full interactive interface, run:")
        print("   streamlit run bpmn_analyzer.py")
        print("   or")
        print("   python run_app.py")
    
    else:
        print("\n❌ No files were successfully analyzed.")

if __name__ == "__main__":
    demo_analysis()
