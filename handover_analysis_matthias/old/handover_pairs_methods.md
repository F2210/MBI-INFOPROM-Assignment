# Methods Section: Handover Pairs Calculations

## Overview

This methods section describes the computational approach for analyzing handover pairs in process mining event logs, specifically focusing on role-to-role transitions within purchase-to-pay process categories. The methodology enables identification of frequent handover patterns, quantification of handover frequencies, and correlation analysis with process performance metrics.

## Data Source and Preprocessing

### Event Log Structure
The analysis utilizes XES (eXtensible Event Stream) format event logs containing process execution data. Each event in the log includes:
- **Case ID**: Unique identifier for process instances
- **Activity**: The specific task or action performed
- **Timestamp**: Temporal information for event ordering
- **Resource**: The organizational unit or system performing the activity
- **User Role**: The role attribute indicating the organizational role responsible for the activity

### Process Categories
The analysis covers four distinct purchase-to-pay process categories:
1. **3-Way Before GR**: Three-way matching with invoice received before goods receipt
2. **3-Way After GR**: Three-way matching with invoice received after goods receipt  
3. **2-Way**: Two-way matching processes
4. **Consignment**: Consignment-based procurement processes

### Data Filtering and Preprocessing
Event logs undergo preprocessing to ensure data quality:
- Removal of cases with single events (insufficient for handover analysis)
- Validation of timestamp consistency
- Role attribute standardization and mapping
- Filtering of incomplete or corrupted event records

## Handover Pair Identification Algorithm

### Core Handover Detection Logic

The handover pair identification follows a sequential event analysis approach:

```python
def analyze_handover_pairs(log, category_name):
    handover_counts = Counter()
    total_handovers = 0
    
    for case in log:
        events = list(case)
        
        # Compare consecutive events for role changes
        for i in range(len(events) - 1):
            current_event = events[i]
            next_event = events[i + 1]
            
            # Extract roles from events
            current_role = current_event.get("userRole", "UNKNOWN")
            next_role = next_event.get("userRole", "UNKNOWN")
            
            # Detect handover conditions
            if current_role != next_role or current_role == "unclear" or next_role == "unclear":
                handover_pair = (current_role, next_role)
                handover_counts[handover_pair] += 1
                total_handovers += 1
```

### Handover Detection Criteria

A handover is identified when **any** of the following conditions are met:

1. **Role Change**: The role attribute differs between consecutive events
2. **Unclear Role**: Either the current or next event has an "unclear" role designation
3. **System Handover**: Transitions involving system resources (e.g., batch processes)

### Handover Pair Representation

Each handover is represented as an ordered pair:
- **From Role**: The role responsible for the current event
- **To Role**: The role responsible for the subsequent event
- **Direction**: Handovers are directional, distinguishing A→B from B→A

## Statistical Analysis Framework

### Frequency Calculations

For each handover pair, the following metrics are computed:

1. **Absolute Count**: Total number of occurrences across all cases
2. **Relative Frequency**: Percentage of total handovers represented by each pair
3. **Case-Level Frequency**: Average handovers per case for each pair

### Correlation Analysis

The methodology includes correlation analysis between handover patterns and process performance:

```python
def analyze_correlation(df, category):
    correlation, p_value = stats.pearsonr(df['total_handovers'], df['duration'])
    return {
        'category': category,
        'correlation': correlation,
        'p_value': p_value,
        'mean_duration': df['duration'].mean(),
        'mean_handovers': df['total_handovers'].mean()
    }
```

### Statistical Significance Testing

- **Pearson Correlation**: Measures linear relationship between handover frequency and case duration
- **P-value Calculation**: Determines statistical significance of correlations
- **Effect Size**: Correlation coefficient interpretation (r < 0.1: negligible, 0.1-0.3: small, 0.3-0.5: medium, >0.5: large)

## Data Aggregation and Reporting

### Category-Level Aggregation

Results are aggregated at the process category level:
- **Total Handovers**: Sum of all handovers within each category
- **Unique Pairs**: Count of distinct role combinations
- **Top Handovers**: Most frequent handover pairs with percentages
- **Distribution Analysis**: Statistical distribution of handover frequencies

### Cross-Category Comparison

Comparative analysis across process categories includes:
- **Handover Density**: Handovers per case ratio
- **Role Diversity**: Number of unique role combinations
- **Pattern Similarity**: Overlap in frequent handover pairs
- **Performance Impact**: Correlation strength differences

## Validation and Quality Assurance

### Data Quality Checks

The methodology incorporates multiple validation steps:

1. **Completeness Check**: Verification that all required attributes are present
2. **Consistency Validation**: Ensuring role assignments are consistent within cases
3. **Outlier Detection**: Identification and handling of anomalous handover patterns
4. **Sample Size Validation**: Ensuring sufficient data for statistical analysis

### Algorithm Validation

The handover detection algorithm is validated through:
- **Manual Verification**: Random sampling and manual verification of detected handovers
- **Edge Case Testing**: Handling of special cases (single events, unclear roles)
- **Performance Testing**: Scalability testing with large event logs
- **Reproducibility**: Consistent results across multiple executions

## Output Generation

### Primary Outputs

The methodology generates the following outputs:

1. **Handover Pair Matrix**: Complete frequency matrix of all role combinations
2. **Statistical Summary**: Descriptive statistics for each process category
3. **Correlation Analysis**: Handover-duration correlation coefficients and significance
4. **Visualization**: Charts and graphs for pattern identification

### File Formats

Results are exported in structured formats:
- **CSV Files**: Tabular data for further analysis
- **JSON Files**: Structured data for programmatic access
- **Visualization Files**: PNG/PDF charts for reporting
- **Summary Reports**: Text-based summaries of key findings

## Computational Considerations

### Performance Optimization

The algorithm is optimized for large-scale event logs:
- **Incremental Processing**: Case-by-case processing to manage memory usage
- **Progress Tracking**: Real-time progress monitoring for long-running analyses
- **Parallel Processing**: Support for parallel execution where applicable
- **Memory Management**: Efficient data structures for large handover matrices

### Scalability

The methodology is designed to handle:
- **Large Event Logs**: Processing of millions of events
- **Multiple Categories**: Simultaneous analysis of multiple process variants
- **Real-time Analysis**: Support for streaming event data
- **Distributed Processing**: Capability for distributed computing environments

## Limitations and Assumptions

### Methodological Assumptions

1. **Role Completeness**: Assumes all events have valid role assignments
2. **Temporal Ordering**: Relies on correct timestamp ordering of events
3. **Case Independence**: Treats cases as independent process instances
4. **Role Consistency**: Assumes consistent role naming across the dataset

### Known Limitations

1. **Role Granularity**: Analysis depends on the granularity of role definitions
2. **Temporal Precision**: Limited by the precision of timestamp data
3. **Context Loss**: Does not capture the business context of handovers
4. **Causality**: Identifies correlations but does not establish causality

## Future Enhancements

### Planned Improvements

1. **Context-Aware Analysis**: Incorporation of business context in handover analysis
2. **Predictive Modeling**: Development of predictive models for handover impact
3. **Real-time Monitoring**: Implementation of real-time handover monitoring
4. **Advanced Visualization**: Enhanced visualization capabilities for complex patterns

This methodology provides a robust foundation for analyzing handover patterns in process mining contexts, enabling data-driven insights for process improvement and optimization. 