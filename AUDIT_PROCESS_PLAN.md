# 🔍 BPM Analysis - Audit Process Plan

## 📋 Objective

Implement a comprehensive auditing process to ensure:
1. ✅ **Data Parsing Accuracy** - Verify all BPMN data is parsed correctly
2. ✅ **Data Integrity Checks** - Validate data completeness and consistency
3. ✅ **Health Check Integration** - Add health checks to Executive Summary
4. ✅ **Audit Trail** - Track all parsing activities and issues

---

## 🎯 Audit Requirements

### **1. Data Parsing Audit**

**Purpose**: Verify that all BPMN XML data is being parsed correctly

**What to Check**:
- ✅ All tasks are extracted from XML
- ✅ All Camunda properties are captured
- ✅ Swimlane mapping is correct
- ✅ Process-to-task relationships are maintained
- ✅ No data loss during parsing

**Implementation**:
```python
def audit_parsing_results(xml_dict, parsed_data):
    """
    Audit the parsing results to ensure data integrity
    """
    audit_results = {
        'total_processes_in_xml': 0,
        'total_tasks_in_xml': 0,
        'total_processes_parsed': 0,
        'total_tasks_parsed': 0,
        'missing_swimlanes': 0,
        'tasks_without_owner': 0,
        'tasks_without_time': 0,
        'parsing_warnings': [],
        'parsing_errors': []
    }
    
    # Count processes and tasks in XML
    definitions = xml_dict.get('bpmn:definitions', {})
    processes = definitions.get('bpmn:process', [])
    if not isinstance(processes, list):
        processes = [processes] if processes else []
    
    audit_results['total_processes_in_xml'] = len(processes)
    
    # Count tasks in XML
    for process in processes:
        task_types = ['bpmn:task', 'bpmn:sendTask', 'bpmn:manualTask']
        for task_type in task_types:
            tasks = process.get(task_type, [])
            if not isinstance(tasks, list):
                tasks = [tasks] if tasks else []
            audit_results['total_tasks_in_xml'] += len(tasks)
    
    # Count parsed processes and tasks
    audit_results['total_processes_parsed'] = len(parsed_data.get('processes', []))
    audit_results['total_tasks_parsed'] = len(parsed_data.get('tasks', []))
    
    # Check for common issues
    for task in parsed_data.get('tasks', []):
        if not task.get('swimlane') or task.get('swimlane') == 'Unknown':
            audit_results['missing_swimlanes'] += 1
        if not task.get('task_owner'):
            audit_results['tasks_without_owner'] += 1
        if not task.get('time_hhmm'):
            audit_results['tasks_without_time'] += 1
    
    # Verify no data loss
    if audit_results['total_tasks_in_xml'] != audit_results['total_tasks_parsed']:
        audit_results['parsing_warnings'].append(
            f"Task count mismatch: {audit_results['total_tasks_in_xml']} in XML vs "
            f"{audit_results['total_tasks_parsed']} parsed"
        )
    
    return audit_results
```

---

### **2. Data Integrity Audit**

**Purpose**: Validate data completeness and consistency

**What to Check**:
- ✅ Required fields are present
- ✅ Data formats are correct
- ✅ Calculations are accurate
- ✅ No duplicate tasks
- ✅ Relationships are maintained

**Implementation**:
```python
def audit_data_integrity(combined_tasks):
    """
    Audit data integrity and completeness
    """
    integrity_results = {
        'total_tasks': len(combined_tasks),
        'tasks_with_complete_data': 0,
        'tasks_with_missing_data': 0,
        'required_fields_status': {},
        'calculation_errors': [],
        'duplicate_tasks': []
    }
    
    required_fields = ['swimlane', 'task_owner', 'time_hhmm', 'cost_per_hour']
    
    for task in combined_tasks:
        complete = True
        for field in required_fields:
            if field not in task or not task[field]:
                complete = False
                if field not in integrity_results['required_fields_status']:
                    integrity_results['required_fields_status'][field] = 0
                integrity_results['required_fields_status'][field] += 1
        
        if complete:
            integrity_results['tasks_with_complete_data'] += 1
        else:
            integrity_results['tasks_with_missing_data'] += 1
        
        # Verify calculations
        time_minutes = task.get('time_minutes', 0)
        cost_per_hour = task.get('cost_per_hour', 0)
        calculated_cost = (time_minutes / 60) * cost_per_hour
        actual_cost = task.get('total_cost', 0)
        
        if abs(calculated_cost - actual_cost) > 0.01:  # Allow for floating point errors
            integrity_results['calculation_errors'].append({
                'task': task.get('name'),
                'calculated': calculated_cost,
                'actual': actual_cost,
                'difference': abs(calculated_cost - actual_cost)
            })
    
    return integrity_results
```

---

### **3. Health Check Integration**

**Purpose**: Add health checks to Executive Summary

**Implementation**:
```python
def calculate_documentation_health(combined_tasks):
    """
    Calculate documentation health metrics
    Returns: Total tasks vs Tasks requiring documentation
    """
    total_tasks = len(combined_tasks)
    
    # Tasks requiring documentation (Not Documented + In Process)
    tasks_needing_docs = [task for task in combined_tasks 
                         if task.get('doc_status') in ['Not Documented', 
                                                        'In Process to be Documented']]
    tasks_requiring_count = len(tasks_needing_docs)
    
    # Tasks with proper documentation
    tasks_documented = [task for task in combined_tasks 
                       if task.get('doc_status') == 'Documented']
    tasks_documented_count = len(tasks_documented)
    
    # Health Score
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
    """
    Calculate attention tasks health metrics
    Returns: Total tasks vs Tasks requiring attention
    """
    total_tasks = len(combined_tasks)
    attention_tasks = []
    
    for task in combined_tasks:
        needs_attention = False
        reasons = []
        
        # Check for critical issues
        if not task.get('swimlane') or task.get('swimlane') == 'Unknown':
            needs_attention = True
            reasons.append('Missing Swimlane')
        
        if not task.get('task_owner'):
            needs_attention = True
            reasons.append('Missing Owner')
        
        if not task.get('time_hhmm'):
            needs_attention = True
            reasons.append('Missing Time')
        
        # Check documentation needs
        doc_status = task.get('doc_status', '')
        if doc_status in ['Not Documented', 'In Process to be Documented']:
            needs_attention = True
            reasons.append('Needs Documentation')
        
        if needs_attention:
            attention_tasks.append({'task': task, 'reasons': reasons})
    
    attention_count = len(attention_tasks)
    
    # Health Score
    if total_tasks > 0:
        health_percentage = ((total_tasks - attention_count) / total_tasks) * 100
    else:
        health_percentage = 0
    
    return {
        'total_tasks': total_tasks,
        'tasks_requiring_attention': attention_count,
        'health_percentage': health_percentage,
        'attention_tasks': attention_tasks,
        'health_status': 'Excellent' if health_percentage >= 90 
                       else 'Good' if health_percentage >= 75 
                       else 'Fair' if health_percentage >= 50 
                       else 'Poor'
    }
```

---

## 📊 Audit Process Flow

### **Step 1: During File Upload**
1. Parse BPMN XML file
2. Run parsing audit
3. Display parsing results in sidebar
4. Show warnings if any

### **Step 2: After Analysis**
1. Run data integrity audit
2. Store audit results in session state
3. Display audit summary in Executive Summary

### **Step 3: Health Check Display**
1. Calculate documentation health
2. Calculate attention health
3. Display metrics in Executive Summary with visual indicators

---

## 🔍 Audit Display Strategy

### **Option 1: In Executive Summary Tab (Recommended)**

Add audit section at the top of Executive Summary:

```python
# In tab1 - Executive Summary

# Audit Results Section
st.subheader("🔍 Data Audit Results")

# Parsing Audit
if 'parsing_audit' in st.session_state:
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Tasks in XML", st.session_state['parsing_audit']['total_tasks_in_xml'])
    with col2:
        st.metric("Tasks Parsed", st.session_state['parsing_audit']['total_tasks_parsed'])
    
    if st.session_state['parsing_audit']['parsing_warnings']:
        st.warning(f"⚠️ Parsing Warnings: {len(st.session_state['parsing_audit']['parsing_warnings'])}")

# Health Checks Section
st.subheader("🏥 Process Health Checks")

col1, col2, col3, col4 = st.columns(4)

# Documentation Health
doc_health = calculate_documentation_health(combined_tasks)
with col1:
    if doc_health['health_status'] == 'Excellent':
        st.success(f"📚 Documentation: {doc_health['health_percentage']:.1f}%")
    elif doc_health['health_status'] == 'Good':
        st.warning(f"📚 Documentation: {doc_health['health_percentage']:.1f}%")
    else:
        st.error(f"📚 Documentation: {doc_health['health_percentage']:.1f}%")
    
    st.metric(
        "Tasks Requiring Docs",
        f"{doc_health['tasks_requiring_documentation']}/{doc_health['total_tasks']}"
    )

# Attention Health
attention_health = calculate_attention_health(combined_tasks)
with col2:
    if attention_health['health_status'] == 'Excellent':
        st.success(f"⚠️ Attention: {attention_health['health_percentage']:.1f}%")
    elif attention_health['health_status'] == 'Good':
        st.warning(f"⚠️ Attention: {attention_health['health_percentage']:.1f}%")
    else:
        st.error(f"⚠️ Attention: {attention_health['health_percentage']:.1f}%")
    
    st.metric(
        "Tasks Requiring Attention",
        f"{attention_health['tasks_requiring_attention']}/{attention_health['total_tasks']}"
    )
```

---

## 🧪 Testing Strategy

### **1. Test with Known Data**
- Use example BPMN files from `example/` folder
- Verify parsing results match expected values
- Check health calculations manually

### **2. Test with Various Scenarios**
- Empty files
- Missing data
- Invalid data
- Large files (>1000 tasks)

### **3. Edge Cases**
- Tasks with no swimlane
- Tasks with no owner
- Tasks with no time estimate
- Mixed documentation statuses

---

## 📝 Implementation Plan

### **Phase 1: Audit Functions (Day 1-2)**
1. ✅ Implement `audit_parsing_results()`
2. ✅ Implement `audit_data_integrity()`
3. ✅ Test audit functions with sample data

### **Phase 2: Health Check Functions (Day 2-3)**
1. ✅ Implement `calculate_documentation_health()`
2. ✅ Implement `calculate_attention_health()`
3. ✅ Test health calculations

### **Phase 3: Integration (Day 3-4)**
1. ✅ Integrate audit into file upload process
2. ✅ Add health checks to Executive Summary
3. ✅ Add visual indicators
4. ✅ Test thoroughly

---

## ✅ Acceptance Criteria

### **Audit Process**
- ✅ All BPMN data is audited after parsing
- ✅ Parsing warnings are displayed
- ✅ Data integrity checks run automatically
- ✅ Audit results are stored in session state

### **Health Checks in Executive Summary**
- ✅ Documentation Health metric displayed
- ✅ Attention Health metric displayed
- ✅ Visual indicators (success/warning/error) work correctly
- ✅ Metrics show "X/Y" format as requested
- ✅ Health percentages are calculated accurately

---

*Last Updated: 2025-08-26*  
*Status: Planning Phase*
