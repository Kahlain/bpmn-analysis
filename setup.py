from setuptools import setup, find_packages

setup(
    name="inocta-bpm-analysis",
    version="1.0.0",
    description="BPMN Business Process Analysis Tool",
    author="Inocta",
    packages=find_packages(),
    install_requires=[
        "streamlit>=1.28.0",
        "xmltodict>=0.13.0",
        "pandas>=2.0.0,<3.0.0",
        "plotly>=5.15.0",
        "numpy>=1.21.0,<2.0.0",
        "openpyxl>=3.1.0",
        "python-dateutil>=2.8.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Business/Process Analysts",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
