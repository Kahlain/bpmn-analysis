"""
📋 Data Normalization Guide page for BPMN Analysis app.
This page explains all normalization rules applied to the data.
"""
import streamlit as st
import pandas as pd
from utils.shared import setup_file_upload, get_combined_tasks, get_analysis_data, has_data, render_page_header, render_sidebar_header

# Render sidebar header
render_sidebar_header()

# Set up file upload in sidebar (visible on all pages)
setup_file_upload()

# Render page header
render_page_header("Data Normalization Guide", "📋")

# Check if data is available (optional for this informational page)
if has_data():
    combined_tasks = get_combined_tasks()
    st.info(f"📊 You have {len(combined_tasks)} tasks loaded. Normalization is applied to this data.")

st.markdown("---")

# Introduction
st.markdown("""
## 📋 What is Data Normalization?

Data normalization is the process of **standardizing and cleaning data values** to ensure consistency across the application. 
This helps provide accurate analysis, avoids duplicate categories, and improves data quality.

**Why Normalization?**
- ✅ **Consistency**: Same values are treated the same way
- ✅ **Accuracy**: Avoids duplicate categories (e.g., "Unknown" vs "unknown" vs empty)
- ✅ **User Experience**: Cleaner display and better understanding
- ✅ **Analysis**: More accurate statistics and reporting

---

## 🔍 Normalization Rules Applied

### 1️⃣ Document URL Normalization

**Purpose**: Clean up document URLs and handle "not available" cases.

**Normalization Rules**:
""")

# Create a table for document URL normalization
doc_url_rules = pd.DataFrame({
    'Input Value': ['NR', 'NO URL', 'No URL', 'nourl', 'unknown', '', 'None', None, 'Valid URL'],
    'Normalized To': ['Empty string', 'Empty string', 'Empty string', 'Empty string', 'Empty string', 'Empty string', 'Empty string', 'Empty string', 'Kept as-is'],
    'Case Sensitive?': ['No', 'No', 'No', 'No', 'No', 'N/A', 'N/A', 'N/A', 'N/A']
})

st.dataframe(doc_url_rules, use_container_width=True, hide_index=True)

st.markdown("""
**Where Applied**: 
- Task parsing (`bpmn_analyzer.py`)
- Document URL display (Tasks Overview, Documentation Status)
- Export functions (Excel, CSV, JSON, Markdown)

**Example**:
```python
# Input in BPMN file: doc_url = "NR"
# After normalization: doc_url = "" (empty string)
# Display shows: "(empty)" or "N/A"
```
""")

st.markdown("---")

### Document Status Normalization
st.markdown("""
### 2️⃣ Document Status Normalization

**Purpose**: Standardize document status values and handle missing/empty statuses.

**Normalization Rules**:
""")

doc_status_rules = pd.DataFrame({
    'Input Value': ['', 'None', None, 'unknown', 'Unknown', 'UNKNOWN', 'Valid Status'],
    'Normalized To': ["'Unknown'", "'Unknown'", "'Unknown'", "'Unknown'", "'Unknown'", "'Unknown'", 'Kept as-is'],
    'Case Sensitive?': ['N/A', 'N/A', 'N/A', 'No', 'No', 'No', 'Yes']
})

st.dataframe(doc_status_rules, use_container_width=True, hide_index=True)

st.markdown("""
**Valid Document Status Values**:
- ✅ **"Documented"**: Task has complete documentation
- ✅ **"Documentation Not Needed"**: Task doesn't require documentation
- ✅ **"In Process to be Documented"**: Documentation is being created
- ✅ **"Not Documented"**: Task lacks documentation
- ❓ **"Unknown"**: Status is missing, empty, or invalid

**Where Applied**:
- Executive Summary (Documentation Status table)
- Tasks Overview (Documentation Summary)
- Documentation Status page
- Quality Control (validation checks)

**Example**:
```python
# Input in BPMN file: doc_status = ""
# After normalization: doc_status = "Unknown"
# Display shows: "❓ Unknown"
```
""")

st.markdown("---")

### Task Status Normalization
st.markdown("""
### 3️⃣ Task Status Normalization

**Purpose**: Standardize task status values, especially handling empty/null/zero values.

**Normalization Rules**:
""")

task_status_rules = pd.DataFrame({
    'Input Value': ['', '0', 0, 'None', None, 'unknown', 'Unknown', 'Valid Status'],
    'Normalized To': ["'Unknown'", "'Unknown'", "'Unknown'", "'Unknown'", "'Unknown'", "'Unknown'", "'Unknown'", 'Kept as-is'],
    'Case Sensitive?': ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'No', 'No', 'Yes']
})

st.dataframe(task_status_rules, use_container_width=True, hide_index=True)

st.markdown("""
**Common Task Status Values**:
- ✅ **"OK"**: Task is in good standing
- ⚠️ **"Requires Attention"**: Task needs review or action
- 📋 **"Pending"**: Task is waiting for something
- 🚫 **"Blocked"**: Task cannot proceed
- ❗ **"Issue"**: Task has an identified problem
- ❓ **"Unknown"**: Status is missing, empty, zero, or invalid

**Where Applied**:
- Status Analysis page (Task Status Summary)
- Tasks Overview (status filtering)
- Executive Summary (Task Health table)
- Quality Control (validation checks)

**Example**:
```python
# Input in BPMN file: task_status = "0"
# After normalization: task_status = "Unknown"
# Display shows: "Unknown" (not "0")
```

**Why This Matters**: 
In your data, you may have **140 tasks with status "0"**. These will all be grouped under **"Unknown"** instead of showing as separate "0" entries, making the analysis cleaner and more meaningful.
""")

st.markdown("---")

### Additional Normalizations
st.markdown("""
### 4️⃣ Additional Data Cleaning

**Currency Normalization**:
- Empty or `None` → `'Unknown'`
- Used in cost calculations and displays

**Time Format Normalization**:
- Empty or invalid → `'00:00'`
- Parsed from HH:MM format
- Converted to minutes and hours for calculations

**Owner/Swimlane Normalization**:
- Empty or `None` → `'Unknown'`
- Used in analysis and grouping

**Process Reference**:
- Added to all tasks to track source process
- Empty → `'Unknown'`
""")

st.markdown("---")

### Impact Section
st.markdown("""
## 📊 Impact of Normalization

### Before Normalization:
""")

before_after_example = pd.DataFrame({
    'Metric': [
        'Status "0"',
        'Status "" (empty)',
        'Status "unknown"',
        'Status "Unknown"',
        'Document URL "NR"',
        'Document Status "" (empty)'
    ],
    'Before': [
        'Shown as "0" (separate category)',
        'Shown as "" (separate category)',
        'Shown as "unknown" (separate category)',
        'Shown as "Unknown"',
        'Shown as "NR" (valid URL?)',
        'Shown as "" (separate category)'
    ],
    'After': [
        'Grouped as "Unknown"',
        'Grouped as "Unknown"',
        'Grouped as "Unknown"',
        'Grouped as "Unknown"',
        'Treated as empty/N/A',
        'Grouped as "Unknown"'
    ],
    'Benefit': [
        'Consistent categorization',
        'Consistent categorization',
        'Consistent categorization',
        'Consistent categorization',
        'Clear indication of missing data',
        'Consistent categorization'
    ]
})

st.dataframe(before_after_example, use_container_width=True, hide_index=True)

st.markdown("""
### Benefits:
1. **🎯 Accurate Statistics**: No duplicate categories affecting counts
2. **📊 Clean Reports**: Consistent display across all pages
3. **🔍 Better Analysis**: Easier to identify data quality issues
4. **✅ Data Quality**: Clear indication of missing or invalid data

---

## 🔧 Technical Details

### Normalization Functions

**Document URL Normalization** (in `bpmn_analyzer.py`):
```python
def _normalize_doc_url(self, doc_url: str) -> str:
    # Normalizes "NR", "NO URL", "No URL", "unknown" → empty string
    # Returns empty string for invalid values
    # Returns original URL for valid values
```

**Document Status Normalization** (in multiple pages):
```python
def normalize_status(status):
    # Normalizes empty/None/'unknown' → 'Unknown'
    # Handles case-insensitive matching
    # Returns normalized status
```

**Task Status Normalization** (in `pages/05_Status_Analysis.py`):
```python
def normalize_task_status(status):
    # Normalizes empty/None/'0'/'unknown' → 'Unknown'
    # Handles both string and numeric zeros
    # Returns normalized status
```

---

## 📝 Best Practices

### When Uploading BPMN Files:

1. **✅ Use Standard Status Values**:
   - For task status: "OK", "Pending", "Requires Attention", etc.
   - For doc status: "Documented", "Not Documented", "In Process to be Documented", etc.

2. **✅ Avoid Empty Values**:
   - Use "Unknown" instead of leaving fields empty
   - This makes your data more explicit

3. **✅ Use Valid URLs**:
   - Use actual URLs for document links
   - Use empty string (or leave blank) if no URL exists
   - Avoid "NR", "NO URL", etc. (they'll be normalized anyway, but it's cleaner to use empty)

4. **✅ Be Consistent**:
   - Use the same status values across all tasks
   - Follow your organization's standards

---

## 🔍 Where to See Normalization in Action

**To verify normalization is working:**

1. **Status Analysis Page**: Check the "Task Status Summary" table - you should see "Unknown" instead of "0" or empty values.

2. **Tasks Overview Page**: Check the "Documentation Status Breakdown" - empty or invalid statuses should all be grouped as "Unknown".

3. **Documentation Status Page**: Check the status distribution - all normalized values should appear as "Unknown".

4. **Export Functions**: Exported data should show normalized values consistently.

---

## 💡 Questions?

If you notice inconsistencies in how data is displayed or normalized, please check:
- The normalization rules above
- Your BPMN file source data
- The specific page where you see the issue

**Remember**: Normalization happens **automatically** when data is loaded. You don't need to modify your BPMN files to match these rules - the app handles it for you!

---

*Last updated: 2025-01-28*
""")

# Footer
st.markdown("---")
st.markdown("""
**💡 Tip**: Use this page as a reference when analyzing your data or troubleshooting display issues. 
All normalization happens automatically to ensure data consistency across the entire application!
""")

