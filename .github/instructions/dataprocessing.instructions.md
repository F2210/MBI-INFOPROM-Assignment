---
applyTo: '**'
---
# GitHub Copilot Instructions - INFOMPROM Process Analytics

## Project Context
You are working on a **Process Mining** project analyzing the **BPI Challenge 2019** event log focused on purchase order handling processes. The project examines compliance analysis and handover patterns in a purchase-to-pay process.

## Business Questions
1. **BQ1**: In which category of items does non-compliance most severely disrupt the expected process flow?
2. **BQ2**: To what extent do specific handovers between user roles or systems correlate with increased case durations?

## Key Technologies & Libraries
- **PM4Py**: Primary process mining library for preprocessing, discovery, and compliance checking
- **Disco**: Process exploration and visualization
- **Pandas**: Data manipulation and analysis
- **NumPy**: Numerical computations
- **Matplotlib/Seaborn**: Data visualization
- **NetworkX**: Social network analysis for handover patterns

## Data Structure & Categories
### Item Categories (4 types):
1. **3-way match, invoice after GR** (75.45% of cases)
2. **3-way match, invoice before GR** (22.36% of cases)
3. **Consignment** (2.13% of cases)
4. **2-way match** (0.06% of cases)

### Key Attributes:
- Case ID, Activity, Timestamp, Resource, Item Category
- Resource types: "NONE", "Batch x", "User x"

## Compliance Rules by Category

### 3-way match, invoice after GR:
- Goods receipt must be recorded
- Invoice receipt must be recorded
- Goods receipt before invoice
- Values must match (item, goods receipt, invoice)

### 3-way match, invoice before GR:
- Goods receipt must be recorded
- Invoice receipt must be recorded
- Invoice may precede goods receipt
- Values must match (creation, invoice, goods-receipt)

### 2-way match:
- Only invoice receipt required
- No goods receipt
- Invoice value must match original item value

### Consignment:
- Goods receipt expected
- No invoice at purchase-order level
- Separate consignment invoicing process

## Code Generation Guidelines

### Data Preprocessing:
```python
# When generating preprocessing code, always include:
# 1. Filter cases starting after 01/01/2018 00:00
# 2. Include only cases starting with "Create Purchase Order Item"
# 3. Bucket by Item Category
# 4. Handle missing timestamps (epoch 0 removal)
```

### Compliance Analysis (BQ1):
```python
# Focus on:
# - Process model discovery using Inductive Miner
# - Model alignment for deviation detection
# - Impact scoring: occurrence_impact × throughput_impact
# - Throughput: mean + 95th percentile case duration
# - Root cause analysis for non-compliant cases
```

### Handover Analysis (BQ2):
```python
# Key patterns to implement:
# - Role standardization: NONE, Batch x, UserRole y
# - Behavioral clustering for user grouping
# - Handover detection between consecutive activities
# - Social network analysis for role transitions
# - Activity transition analysis (DFG)
```

## Specific Coding Patterns

### Resource Standardization:
```python
# Convert resources to standardized roles
# "NONE" → system/external actions
# "Batch x" → batch processing
# "User x" → behavioral clustering → "UserRole y"
```

### Impact Calculation:
```python
# Risk matrix approach
impact_score = occurrence_impact * throughput_impact
# Where:
# - occurrence_impact = non_compliant_cases / total_cases
# - throughput_impact = mean_duration or percentile_95_duration
```

### Handover Detection:
```python
# Handover occurs when role changes between consecutive activities
# Count handovers per case
# Analyze handover pairs (role A → role B)
# Identify key handover points (activity transitions)
```

## Visualization Requirements
- **Boxplots**: Handover frequency vs case duration per category
- **Social Network Graphs**: Role-to-role handover patterns
- **Process Models**: Compliant process flows per category
- **DFG (Directly-Follows Graph)**: Activity transitions with handovers
- **Heatmaps**: Handover frequency matrices

## Performance Considerations
- Use PM4Py for efficient event log processing
- Implement category-wise bucketing to reduce memory usage
- Cache intermediate results for repeated analyses
- Use vectorized operations for statistical calculations

## Error Handling Patterns
```python
# Always include validation for:
# - Missing timestamps
# - Invalid activity sequences
# - Empty case buckets
# - Resource attribute inconsistencies
# - Compliance rule violations
```

## Analysis Workflow
1. **Preprocessing**: Filter, clean, and bucket data
2. **Model Discovery**: Create compliant process models per category
3. **Compliance Check**: Use model alignment to detect deviations
4. **Impact Analysis**: Calculate combined impact scores
5. **Handover Analysis**: Role standardization and pattern detection
6. **Visualization**: Generate charts and network graphs
7. **Statistical Analysis**: Correlation and significance testing

## Output Format Expectations
- Quantitative results with statistical measures (mean, median, percentiles)
- Impact scores for ranking categories
- Handover frequency statistics per category
- Compliance percentages per item category
- Performance metrics (case duration, throughput)

## Code Quality Standards
- Use descriptive variable names related to process mining terminology
- Include docstrings explaining process mining concepts
- Add comments for compliance rules and business logic
- Implement proper exception handling for event log operations
- Follow PM4Py best practices and naming conventions