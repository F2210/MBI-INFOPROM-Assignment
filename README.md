# Log Analysis and Filtering for Process Mining

This repository contains a Python notebook for analyzing and filtering XES event logs for process mining. The main purpose is to prepare and segment process data from a BPI Challenge 2019 dataset.

## Overview

The `Compliance.ipynb` notebook demonstrates how to:

1. Import XES event logs using PM4Py
2. Analyze event attributes and log statistics
3. Filter cases based on specific criteria:
    - Time frame (cases after January 1, 2018)
    - Start activities (cases starting with "Create Purchase Order Item")
4. Segment the filtered log into groups based on item categories:
    - 3-way matching after GR
    - 3-way matching before GR
    - 3-way matching
    - Consignment
    - Other cases

## Key Components

- **Data Import**: Uses PM4Py to import XES files
- **Log Analysis**: Extracts statistics about events, cases, and attributes
- **Filtering**: Implements multiple filtering strategies to focus on relevant subsets
- **Grouping**: Segments cases based on item categories
- **Data Export**: Saves filtered logs as separate XES files for further analysis

## Memory Usage Considerations

The notebook implements several strategies to manage memory efficiently:

1. **Selective Loading**: Only necessary attributes are loaded when importing logs
2. **Incremental Processing**: Filters are applied sequentially to reduce peak memory usage
3. **Variable Cleanup**: Temporary variables are explicitly deleted (using `del`) after use
4. **Group-by-Group Processing**: Instead of keeping all filtered logs in memory simultaneously, each group is processed and exported before moving to the next one
5. **Set-Based Tracking**: Uses sets to track case IDs efficiently when determining the "other" category

When working with large event logs (like the BPI Challenge dataset), memory consumption can be significant. Consider increasing available memory or working with smaller samples if you encounter memory errors.

## Usage

To use this notebook:
1. Ensure you have PM4Py and its dependencies installed
2. Place your XES file in the `./data/` directory
3. Run the notebook cells sequentially
4. Find the filtered XES files in the `./data/` directory

The resulting filtered logs can be used for more detailed process mining analysis.