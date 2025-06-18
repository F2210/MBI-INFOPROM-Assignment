# Methods Section: Handover Key Pairs Analysis

## Overview

This methods section describes the computational approach for analyzing handover key pairs in process mining event logs, specifically focusing on activity transitions where role handovers occur. The methodology identifies critical handover points in business processes, quantifies their frequency, and analyzes their impact on process performance and duration.

## Conceptual Framework

### Handover Key Pairs Definition

A **handover key pair** is defined as an activity transition (from_activity → to_activity) where a role handover occurs between consecutive events. Unlike general handover pairs that focus solely on role transitions, handover key pairs capture the specific business activities where work transfers between different organizational roles.

### Key Components

1. **Activity Transition**: The sequence of two consecutive activities in a process
2. **Role Handover**: The change in responsible role between the two activities
3. **Key Point**: A critical juncture in the process where work transfers between roles
4. **Frequency Analysis**: Quantification of how often specific activity transitions involve handovers

## Data Source and Preprocessing

### Event Log Structure

The analysis utilizes XES (eXtensible Event Stream) format event logs containing:
- **Case ID**: Unique identifier for process instances
- **Activity**: The specific business task or action performed
- **Timestamp**: Temporal information for event ordering
- **Resource**: The organizational unit or system performing the activity
- **User Role**: The role attribute indicating the organizational role responsible

### Process Categories

The analysis covers four distinct purchase-to-pay process categories:
1. **3-Way Before GR**: Three-way matching with invoice received before goods receipt
2. **3-Way After GR**: Three-way matching with invoice received after goods receipt
3. **2-Way**: Two-way matching processes
4. **Consignment**: Consignment-based procurement processes

### Role Extraction and Standardization

```python
def get_role(resource):
    """Extract role from resource identifier."""
    if resource == "NONE" or not resource:
        return "NONE"
    if resource.startswith("batch"):
        return "BATCH"
    if resource.startswith("user"):
        try:
            role_num = resource.split('_')[1][:2]  # Take first two digits
            return f"ROLE_{role_num}"
        except:
            return "UNKNOWN"
    return resource
```

## Handover Key Pairs Identification Algorithm

### Core Detection Logic

The handover key pairs identification follows a sequential event analysis approach:

```python
def analyze_handover_keypoints(log, category_name):
    handover_transitions = []
    handover_details = defaultdict(lambda: {'total': 0, 'roles': defaultdict(int)})
    
    for case in log:
        events = list(case)
        for i in range(len(events) - 1):
            current_event = events[i]
            next_event = events[i + 1]
            
            # Get activities and roles
            current_activity = current_event["concept:name"]
            next_activity = next_event["concept:name"]
            current_role = get_role(current_event.get("org:resource", "NONE"))
            next_role = get_role(next_event.get("org:resource", "NONE"))
            
            # Record transition if there's a role handover
            if current_role != next_role:
                transition = (current_activity, next_activity)
                handover_transitions.append({
                    'from_activity': current_activity,
                    'to_activity': next_activity,
                    'from_role': current_role,
                    'to_role': next_role
                })
                
                # Store detailed information
                key = f"{current_activity} → {next_activity}"
                role_key = f"{current_role} → {next_role}"
                handover_details[key]['total'] += 1
                handover_details[key]['roles'][role_key] += 1
```

### Handover Detection Criteria

A handover key pair is identified when **all** of the following conditions are met:

1. **Activity Transition**: Two consecutive events with different activity names
2. **Role Change**: The role attribute differs between consecutive events
3. **Valid Activities**: Both activities are valid business process activities
4. **Valid Roles**: Both roles are properly defined and not "NONE" or "UNKNOWN"

### Key Pair Representation

Each handover key pair is represented as:
- **From Activity**: The business activity where the handover originates
- **To Activity**: The business activity where the handover completes
- **From Role**: The role responsible for the originating activity
- **To Role**: The role responsible for the destination activity
- **Frequency**: Number of occurrences across all cases
- **Percentage**: Relative frequency within the process category

## Statistical Analysis Framework

### Frequency Calculations

For each handover key pair, the following metrics are computed:

1. **Absolute Frequency**: Total number of occurrences across all cases
2. **Relative Frequency**: Percentage of total handovers represented by each key pair
3. **Role Combination Frequency**: Frequency of specific role combinations for each activity transition
4. **Case-Level Distribution**: Distribution of key pairs across individual cases

### Correlation Analysis

The methodology includes correlation analysis between handover key points and process performance:

```python
def analyze_handover_duration_correlation(log, category_name):
    case_stats = []
    
    for case in log:
        # Calculate number of handovers
        handovers = 0
        events = list(case)
        for i in range(len(events) - 1):
            current_role = events[i].get("userRole", "UNKNOWN")
            next_role = events[i + 1].get("userRole", "UNKNOWN")
            if current_role != next_role:
                handovers += 1
        
        # Calculate case duration
        duration = calculate_case_duration(case)
        
        if duration is not None and handovers > 0:
            case_stats.append({
                'handovers': handovers,
                'duration': duration
            })
    
    # Calculate correlation and p-value
    df = pd.DataFrame(case_stats)
    correlation, p_value = stats.pearsonr(df['handovers'], df['duration'])
    return correlation, p_value, len(df)
```

### Statistical Significance Testing

- **Pearson Correlation**: Measures linear relationship between handover frequency and case duration
- **P-value Calculation**: Determines statistical significance of correlations
- **Effect Size**: Correlation coefficient interpretation (r < 0.1: negligible, 0.1-0.3: small, 0.3-0.5: medium, >0.5: large)

## Data Aggregation and Reporting

### Activity Transition Analysis

Results are aggregated at the activity transition level:
- **Transition Frequencies**: Count of handovers for each activity pair
- **Role Combinations**: Detailed breakdown of role transitions for each activity pair
- **Percentage Distribution**: Relative importance of each transition within the process

### Cross-Category Comparison

Comparative analysis across process categories includes:
- **Key Point Density**: Number of handover key points per process category
- **Transition Patterns**: Similarity and differences in handover patterns
- **Role Involvement**: Distribution of roles across different activity transitions
- **Performance Impact**: Correlation strength differences between categories

## Visualization and Network Analysis

### Directly-Follows Graph (DFG) Generation

The methodology creates network visualizations to represent handover key points:

```python
def create_dfg(transition_counts, handover_details, category_name, threshold=5.0):
    G = nx.DiGraph()
    
    # Add nodes and edges
    for _, row in transition_counts.iterrows():
        from_activity = row['from_activity']
        to_activity = row['to_activity']
        frequency = row['frequency']
        
        # Add nodes if they don't exist
        if from_activity not in G:
            G.add_node(from_activity)
        if to_activity not in G:
            G.add_node(to_activity)
        
        # Add edge with frequency as weight
        G.add_edge(from_activity, to_activity, weight=frequency)
    
    # Highlight handover transitions
    for edge in G.edges():
        from_activity, to_activity = edge
        key = f"{from_activity} → {to_activity}"
        if key in handover_details and handover_details[key]['total'] > 0:
            G[from_activity][to_activity]['handover'] = True
```

### Visualization Types

1. **Bar Charts**: Top handover key points by frequency
2. **Network Graphs**: Activity transition networks with handover highlighting
3. **Heatmaps**: Role transition matrices for activity pairs
4. **Scatter Plots**: Handover-duration correlation analysis

## Validation and Quality Assurance

### Data Quality Checks

The methodology incorporates multiple validation steps:

1. **Activity Completeness**: Verification that all events have valid activity names
2. **Role Consistency**: Ensuring role assignments are consistent within activity transitions
3. **Transition Validation**: Confirming that activity transitions are logically valid
4. **Frequency Thresholds**: Filtering out low-frequency transitions for analysis focus

### Algorithm Validation

The handover key pairs detection algorithm is validated through:
- **Manual Verification**: Random sampling and manual verification of detected key pairs
- **Business Logic Validation**: Ensuring detected transitions align with business process logic
- **Performance Testing**: Scalability testing with large event logs
- **Reproducibility**: Consistent results across multiple executions

## Output Generation

### Primary Outputs

The methodology generates the following outputs:

1. **Transition Frequency Matrix**: Complete frequency matrix of activity transitions with handovers
2. **Role Combination Analysis**: Detailed breakdown of role transitions for each activity pair
3. **Correlation Analysis**: Handover-duration correlation coefficients and significance
4. **Network Visualizations**: DFG representations with handover highlighting

### File Formats

Results are exported in structured formats:
- **CSV Files**: Tabular data for transition frequencies and role combinations
- **PNG Files**: Network visualizations and charts
- **JSON Files**: Structured data for programmatic access
- **Summary Reports**: Text-based summaries of key findings

## Computational Considerations

### Performance Optimization

The algorithm is optimized for large-scale event logs:
- **Incremental Processing**: Case-by-case processing to manage memory usage
- **Progress Tracking**: Real-time progress monitoring for long-running analyses
- **Memory Management**: Efficient data structures for large transition matrices
- **Threshold Filtering**: Automatic filtering of low-frequency transitions

### Scalability

The methodology is designed to handle:
- **Large Event Logs**: Processing of millions of events
- **Multiple Categories**: Simultaneous analysis of multiple process variants
- **Complex Networks**: Generation of large activity transition networks
- **Real-time Analysis**: Support for streaming event data

## Limitations and Assumptions

### Methodological Assumptions

1. **Activity Completeness**: Assumes all events have valid activity assignments
2. **Role Consistency**: Assumes consistent role naming across the dataset
3. **Temporal Ordering**: Relies on correct timestamp ordering of events
4. **Business Logic**: Assumes activity transitions follow logical business process flow

### Known Limitations

1. **Activity Granularity**: Analysis depends on the granularity of activity definitions
2. **Context Loss**: Does not capture the business context of activity transitions
3. **Causality**: Identifies correlations but does not establish causality
4. **Process Variants**: May not capture all process variants within categories

## Business Applications

### Process Optimization

1. **Bottleneck Identification**: High-frequency handover key points may indicate process bottlenecks
2. **Workflow Design**: Activity transition patterns guide workflow optimization
3. **Resource Allocation**: Role involvement in key points supports resource planning
4. **Automation Opportunities**: System handovers show successful automation patterns

### Performance Monitoring

1. **Key Performance Indicators**: Handover key points serve as process KPIs
2. **Trend Analysis**: Monitoring changes in key point frequencies over time
3. **Comparative Analysis**: Benchmarking key points across process variants
4. **Predictive Modeling**: Using key point patterns for performance prediction

## Future Enhancements

### Planned Improvements

1. **Context-Aware Analysis**: Incorporation of business context in key point analysis
2. **Predictive Modeling**: Development of predictive models for key point impact
3. **Real-time Monitoring**: Implementation of real-time key point monitoring
4. **Advanced Network Analysis**: Enhanced network analysis capabilities

### Research Directions

1. **Temporal Analysis**: Investigation of key point patterns over time
2. **Causal Analysis**: Development of causal inference methods for key points
3. **Multi-level Analysis**: Integration of organizational hierarchy in key point analysis
4. **Cross-process Analysis**: Comparative analysis across different business processes

This methodology provides a robust foundation for analyzing handover key pairs in process mining contexts, enabling data-driven insights for process improvement and optimization through activity-level handover analysis. 