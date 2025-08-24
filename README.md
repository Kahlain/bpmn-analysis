# 📊 Inocta BPM Analysis

A powerful, interactive web application for analyzing BPMN (Business Process Model and Notation) XML files to extract business insights, calculate costs, and provide comprehensive KPI analysis for process optimization.

> **🌐 Public Repository**: This project is now open source and available for the community!

## 🚀 Features

### 📈 **Core Analysis**
- **Process Cost Analysis**: Calculate total costs, time estimates, and resource allocation
- **Swimlane/Department Analysis**: Track workload distribution across organizational units
- **Task Owner Insights**: Analyze individual contributor workload and performance
- **Status Analysis**: Monitor task completion status with visual charts and attention task tracking
- **Documentation Compliance**: Track documentation status across all processes

### 🔧 **Advanced Analytics**
- **Tools Analysis**: Identify tool usage patterns and combinations
- **Quality Control**: Highlight missing data and quality issues with priority classification
- **Opportunities & Issues**: Smart categorization of improvement opportunities and risks
- **FAQ Knowledge Capture**: Extract and organize tribal knowledge
- **Multi-Currency Support**: Handle costs in different currencies
- **Industry Context**: Analyze tasks by industry classification

### 📊 **Visualization & Reporting**
- **Interactive Charts**: Pie charts, bar charts, scatter plots, and heatmaps
- **Executive Summary**: High-level KPIs and insights dashboard
- **Export Options**: Excel, CSV, JSON, and Markdown formats
- **Focused Exports**: Issues & Opportunities only, Tasks only, or Complete Analysis
- **Real-time Analysis**: Instant insights as you upload files

## 🛠️ Technology Stack

- **Frontend**: Streamlit (Python web framework)
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly (interactive charts)
- **XML Parsing**: xmltodict
- **Export**: OpenPyXL (Excel), built-in CSV/JSON
- **Deployment**: Local, Vercel, Replit, Streamlit Cloud

## 📋 Prerequisites

- **Python 3.8+**
- **pip** (Python package installer)
- **Git** (for version control)

## 🚀 Quick Start

### 1. **Clone the Repository**
```bash
git clone https://github.com/Kahlain/bpmn-analysis.git
cd bpmn-analysis
```

### 2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 3. **Run the Application**
```bash
# Option 1: Direct Streamlit
streamlit run bpmn_analyzer.py

# Option 2: Using the helper script
python run_app.py

# Option 3: Using shell script (Mac/Linux)
./run_app.sh

# Option 4: Using batch file (Windows)
run_app.bat
```

### 4. **Access the App**
Open your browser and navigate to: `http://localhost:8501`

## 🌐 Deployment Options

### **Local Development**
```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run bpmn_analyzer.py
```

### **Cloud Deployment**

#### **Vercel/Netlify**
1. **Fork this repository**
2. **Use `requirements-deploy.txt`** instead of `requirements.txt`
3. **Set Python version** to 3.11
4. **Build command**: `pip install -r requirements-deploy.txt`
5. **Deploy!**

#### **Heroku**
1. **Fork this repository**
2. **The `Procfile` will automatically configure the app**
3. **Use `requirements-deploy.txt`**
4. **Set Python version** via `runtime.txt`
5. **Deploy!**

#### **Replit**
1. **Fork this repository**
2. **Use `requirements-deploy.txt`**
3. **Set Python version** to 3.11
4. **The `setup.py` will help with dependencies**
5. **Deploy!**

#### **Streamlit Cloud**
1. **Connect your GitHub repository**
2. **Use `requirements-deploy.txt`**
3. **Set Python version** to 3.11
4. **Deploy automatically!**

### **Deployment Files**
- `requirements-deploy.txt` - Deployment-optimized dependencies
- `runtime.txt` - Python version specification
- `setup.py` - Package metadata and dependencies
- `Procfile` - Heroku deployment configuration
- `.streamlit/config.toml` - Streamlit deployment settings

## 🤝 Contributing

This is now a **public open-source project**! We welcome contributions from the community.

### **How to Contribute**
1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Commit your changes**: `git commit -m 'Add amazing feature'`
5. **Push to the branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**

### **What We're Looking For**
- 🐛 Bug fixes and improvements
- ✨ New features and enhancements
- 📚 Documentation improvements
- 🧪 Testing and quality assurance
- 🌍 Localization and internationalization

## 📁 Project Structure

```
bpmn-analysis/
├── bpmn_analyzer.py          # Main application file
├── requirements.txt           # Python dependencies
├── README.md                 # This file
├── run_app.py               # Helper script for easy startup
├── run_app.sh               # Shell script (Mac/Linux)
├── run_app.bat              # Batch script (Windows)
├── demo_analysis.py         # Demo script for programmatic use
├── example/                 # Example files and templates
│   ├── inocta-en.json      # Metadata template
│   └── *.bpmn             # Sample BPMN files
└── .gitignore              # Git ignore rules
```

## 📊 Expected BPMN Structure

Your BPMN files should include **Camunda Properties** with the following metadata:

### **Required Properties**
- `time_hhmm`: Time estimate (HH:MM format)
- `cost_per_hour`: Labor cost per hour
- `currency`: Currency for costs
- `task_owner`: Person responsible for the task
- `task_status`: Current status of the task

### **Optional Properties**
- `issues_priority`: Priority level for issues
- `opportunities`: Improvement opportunities
- `tools_used`: Tools and systems used
- `doc_status`: Documentation status
- `task_description`: Detailed task description
- `task_industry`: Industry classification
- `doc_url`: Link to documentation
- `faq_q1`, `faq_a1`: FAQ capture (up to 3 Q&A pairs)

## 🔍 Usage Guide

### **1. Upload BPMN Files**
- Use the sidebar to upload one or more BPMN XML files
- Supported formats: `.xml`, `.bpmn`
- Multiple files can be analyzed simultaneously

### **2. Navigate Analysis Tabs**
- **📊 Executive Summary**: High-level KPIs and insights
- **📋 Tasks Overview**: Detailed task filtering and display with documentation status and URLs
- **🏭 Swimlane Analysis**: Department-based analysis
- **👥 Owner Analysis**: Task owner insights
- **📊 Status Analysis**: Task status tracking with attention tasks
- **📚 Documentation Status**: Documentation compliance
- **🔧 Tools Analysis**: Tool usage patterns
- **💡 Opportunities**: Improvement opportunities
- **⚠️ Issues & Risks**: Problem identification
- **❓ FAQ Knowledge**: Knowledge capture
- **✅ Quality Control**: Data quality assessment
- **💾 Export Data**: Multi-format exports

### **3. Export Results**
- **Excel (.xlsx)**: Comprehensive analysis with multiple sheets
- **CSV (.csv)**: Tabular data for further analysis
- **JSON (.json)**: Structured data for API integration
- **Markdown (.md)**: Formatted reports for documentation

## 📋 **Enhanced Tasks Overview Table**

The Tasks Overview table now includes comprehensive documentation tracking with the following columns:

### **Core Task Information**
- **`name`**: Task name and description
- **`swimlane`**: Department or organizational unit
- **`task_owner`**: Person responsible for the task
- **`time_display`**: Estimated time in HH:MM format
- **`total_cost`**: Total cost calculation
- **`currency`**: Cost currency (CAD, USD, EUR, etc.)
- **`task_status`**: Current task completion status

### **Documentation Tracking** ✨ **NEW**
- **`doc_status`**: Documentation status with visual indicators:
  - ✅ **Complete**: Documentation is finished
  - 🔄 **In Progress**: Documentation is being worked on
  - ⏳ **Pending**: Documentation is waiting to start
  - 🚫 **Not Started**: Documentation hasn't begun
  - 📝 **Draft**: Documentation is in draft form
  - 📋 **Unknown**: Status not specified

- **`doc_url`**: Clickable documentation links:
  - URLs are truncated in the table for readability
  - Full clickable links are displayed below the table
  - Links open in new browser tabs

### **Enhanced Features**
- **Smart Filtering**: Filter by swimlane, owner, status, and documentation status
- **Documentation Summary**: Real-time statistics on documentation coverage
- **Visual Indicators**: Emoji-based status display for quick recognition
- **Clickable Links**: Direct access to task documentation
- **Coverage Metrics**: Percentage of tasks with complete documentation

## 🌟 Key Features Explained

### **Smart Categorization**
The tool automatically categorizes opportunities and issues using AI-powered keyword analysis, supporting both English and French content.

### **Quality Control**
Identifies missing or incomplete data with priority classification:
- 🚨 **Critical**: Missing essential information
- ⚠️ **Warning**: Missing important details
- ℹ️ **Info**: Missing optional information

### **Multi-Language Support**
Built-in support for English and French content analysis, making it suitable for international organizations.

### **Advanced Export Options**
- **Complete Analysis**: All data with comprehensive insights
- **Tasks Only**: Raw task data for detailed review
- **Summary Only**: Key metrics and high-level insights
- **Issues & Opportunities Only**: Focused export of improvement areas and risks

### **Real-time Analysis**
Instant insights as you upload files, with no need to wait for batch processing.

## 🔧 Configuration

### **Customization Options**
- Modify `categorize_opportunity()` and `categorize_issue()` functions for custom categorization
- Adjust chart colors and styles in the visualization sections
- Customize export formats and content in the export functions

### **Environment Variables**
- Set `STREAMLIT_SERVER_PORT` for custom port configuration
- Configure `STREAMLIT_SERVER_HEADLESS` for headless mode

## 🚀 Deployment Options

### **Local Development**
```bash
streamlit run bpmn_analyzer.py
```

### **Streamlit Cloud**
1. Push to GitHub
2. Connect repository to [Streamlit Cloud](https://streamlit.io/cloud)
3. Deploy automatically

### **Vercel**
1. Install Vercel CLI: `npm i -g vercel`
2. Deploy: `vercel --prod`

### **Replit**
1. Import from GitHub
2. Run: `streamlit run bpmn_analyzer.py`

## 🤝 Contributing

We welcome contributions! Please feel free to:

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** thoroughly
5. **Submit** a pull request

### **Development Setup**
```bash
git clone https://github.com/Kahlain/bpmn-analysis.git
cd bpmn-analysis
pip install -r requirements.txt
pip install -e .
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Streamlit** for the amazing web framework
- **Plotly** for interactive visualizations
- **Pandas** for data manipulation
- **Camunda** for BPMN standards

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Kahlain/bpmn-analysis/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Kahlain/bpmn-analysis/discussions)
- **Wiki**: [Project Wiki](https://github.com/Kahlain/bpmn-analysis/wiki)

## 🔄 Version History

- **v1.0.0** - Initial release with core BPMN analysis features
- **v1.1.0** - Added Quality Control and Tools Analysis
- **v1.2.0** - Enhanced with Opportunities, Issues, and FAQ analysis
- **v1.3.0** - Multi-format export and improved categorization
- **v1.4.0** - Multi-language support and enhanced quality control

---

**Made with ❤️ for Business Process Optimization**

*Transform your BPMN files into actionable business insights!*
