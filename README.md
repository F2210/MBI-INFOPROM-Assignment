# Log Analysis and Filtering for Process Mining

This repository contains tools for analyzing and filtering XES event logs for process mining. The main purpose is to prepare and segment process data from a BPI Challenge 2019 dataset.

## Overview

### Jupyter Notebook (`Compliance.ipynb`)

The notebook demonstrates how to:

1. Import XES event logs using PM4Py
2. Analyze event attributes and log statistics
3. Filter cases based on specific criteria:
    - Time frame (cases after January 1, 2018)
    - Start activities (cases starting with "Create Purchase Order Item")
4. Segment the filtered log into groups based on item categories

### Memory-Efficient Processing Script (`process_logs.py`)

The Python script provides a memory-efficient implementation that focuses exclusively on processing:

1. Process large XES files with minimal memory usage
2. Filter cases by start activity and time range
3. Group cases based on the "Item Category" attribute
4. Export each group to a separate XES file

### Analysis Utilities (`analyze_logs.py`)

A separate utility script for analyzing XES logs that provides:

1. Functions for counting events and cases
2. Analyzing log attributes (event-level and case-level)
3. Verifying case attributes
4. Analyzing case attribute values and distributions

## Key Components

- **Data Import**: Uses PM4Py to import XES files with memory-efficient parameters
- **Log Analysis**: Extracts statistics about events, cases, and attributes (via `analyze_logs.py`)
- **Filtering**: Implements multiple filtering strategies to focus on relevant subsets
- **Grouping**: Segments cases based on item categories 
- **Data Export**: Saves filtered logs as separate XES files for further analysis
- **Memory Management**: Implements advanced techniques to handle large datasets

## Memory Usage Considerations

The implementation uses several strategies to manage memory efficiently:

1. **Selective Loading**: Only necessary attributes are loaded when importing logs
2. **Incremental Processing**: Filters are applied sequentially to reduce peak memory usage
3. **Variable Cleanup**: Temporary variables are explicitly deleted (using `del`) after use
4. **Group-by-Group Processing**: Each group is processed and exported before moving to the next one
5. **Set-Based Tracking**: Uses sets to track case IDs efficiently
6. **Batch Processing**: Processes "other" cases in batches with explicit garbage collection
7. **Sampling**: Uses sampled data for analysis when appropriate

## Using the Scripts

### Processing XES Logs (`process_logs.py`)

This script is focused solely on processing XES logs, filtering them, and grouping them into separate files. It can be customized using the configuration section at the top of the file.

#### Configuration Options

```python
# Input/Output settings
INPUT_FILE = './data/BPI_Challenge_2019_Time_Filtered.xes'
OUTPUT_DIR = './data'
ANALYZE_ONLY = False
DEBUG_MODE = False

# Filter settings
START_ACTIVITY_FILTER = ["Create Purchase Order Item"]
TIME_RANGE_FILTER = {
    "start_date": "2018-01-01 00:00:00",
    "end_date": "2025-05-15 00:00:00",
    "mode": "traces_contained",
    "case_id_key": "concept:name",
    "timestamp_key": "time:timestamp"
}

# Custom groups - can be modified directly here
CUSTOM_GROUPS = {
    "group_3_way_before": ["3-way match, invoice before GR"],
    "group_3_way_after": ["3-way match, invoice after GR"],
    "group_2_way": ["2-way match"],
    "group_consignment": ["Consignment"]
}
```

To run the processing script:

```bash
python process_logs.py
```

### Analyzing XES Logs (`analyze_logs.py`)

This script is designed for independently analyzing XES logs without performing any filtering or grouping. It provides various functions for examining the log structure, attributes, and statistics.

To run the analysis script on any XES file:

```bash
python analyze_logs.py path/to/your/log.xes
```

You can also import and use its functions in your own scripts:

```python
from analyze_logs import analyze_xes_file

# Analyze the log and get results
results = analyze_xes_file("path/to/log.xes")
```

## Custom Grouping Format

Custom groups can be defined directly in the script by modifying the `CUSTOM_GROUPS` variable. The format is a dictionary where:
- Keys are the group names (will be used for the output filenames)
- Values are lists of category values to include in that group

Example:

```python
CUSTOM_GROUPS = {
    "group_invoiced_before": ["3-way match, invoice before GR"],
    "group_invoiced_after": ["3-way match, invoice after GR"],
    "group_consignment": ["Consignment"],
    "group_two_way": ["2-way match"]
}
```

## Usage

### Using the Notebook
1. Ensure you have PM4Py and its dependencies installed
2. Place your XES file in the `./data/` directory
3. Run the notebook cells sequentially

### Using the Processing Script
1. Ensure you have PM4Py and its dependencies installed
2. Modify the configuration settings at the top of `process_logs.py` if needed
3. Run the script: `python process_logs.py`
4. Find the filtered XES files in the output directory

### Using the Analysis Script
1. Ensure you have PM4Py installed
2. Run the script with your XES file: `python analyze_logs.py ./data/your_log.xes`
3. View the analysis output in the terminal

### Using Both Scripts Together
For a complete workflow:
1. First analyze your XES file: `python analyze_logs.py ./data/your_log.xes`
2. Configure the processing script based on analysis insights
3. Run the processing script: `python process_logs.py`
4. The resulting filtered logs can be used for more detailed process mining analysis

This separation of concerns allows you to:
- Use analysis functions independently when you just need log information
- Process logs efficiently without loading analysis components
- Create custom workflows that combine both as needed