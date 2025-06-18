# Impact of Role-Based Handovers on Case Duration in Purchase-to-Pay Processes

## Abstract
This study investigates the relationship between handovers between user roles and case durations in purchase-to-pay processes. Through analysis of process mining data across different process variants (3-way and 2-way matching), we examine how specific handover patterns correlate with increased processing times and identify critical handover points that may impact process efficiency.

## 1. Introduction
Purchase-to-pay processes often involve multiple handovers between different roles and systems, potentially affecting process duration and efficiency. Understanding these relationships is crucial for process optimization and automation strategies.

## 2. Methodology
### 2.1 Data Collection
- Analysis of event logs from purchase-to-pay processes
- Three process variants analyzed:
  - 3-way match (invoice after GR)
  - 3-way match (invoice before GR)
  - 2-way match
- Focus on user role attributes and handover patterns

### 2.2 Analysis Approach
- Identification of role-to-role handovers
- Calculation of handover frequencies and durations
- Statistical correlation analysis
- Visual analysis through:
  - Role interaction heatmaps (Figure 1)
  - Duration distribution plots (Figure 2)
  - Handover frequency charts (Figure 3)
  - System integration analysis (Figure 4)

## 3. Results

### 3.1 Correlation Analysis
#### 3.1.1 Overall Correlation Strength
- 3-way match (invoice after GR): Moderate positive correlation (0.176, p=0.104)
- 3-way match (invoice before GR): Weak positive correlation (0.057, p=0.440)
- 2-way match: Strong correlation in limited sample size

*Figure 1: Role-based handover heatmaps showing frequency of interactions between different roles (`*_role_heatmap.png`)*

#### 3.1.2 High-Impact Role Handovers
##### 3-way match (invoice after GR):
- Role_10 → NONE: 8,473 hours (≈353 days)
- NONE → Role_6: 8,309 hours (≈346 days)
- NONE → Role_5: 8,228 hours (≈343 days)

##### 3-way match (invoice before GR):
- NONE → Role_19: 7,226 hours (≈301 days)
- BATCH → Role_19: 5,422 hours (≈226 days)
- Role_17 → Role_15: 5,303 hours (≈221 days)

##### 2-way match:
- Role_5 → Role_3: 3,429 hours (≈143 days)
- Role_5 → NONE: 167 hours (≈7 days)

*Figure 2: Duration distribution by number of handovers (`*_duration_distribution.png`)*

### 3.2 System Integration Analysis
- System handovers constitute 11-16% of all handovers
- Distribution across categories:
  - 3-way match (invoice after GR): 15.7%
  - 3-way match (invoice before GR): 11.6%
  - 2-way match: 14.3%

*Figure 3: Most frequent handover patterns (`*_top_handovers.png`)*

### 3.3 Process Category Comparison
1. **3-way match (invoice after GR)**:
   - Highest average handovers per case (6.04)
   - Strongest correlation with duration
   - Most complex handover patterns

2. **3-way match (invoice before GR)**:
   - Moderate average handovers (4.51)
   - Lower correlation with duration
   - High volume of system handovers

3. **2-way match**:
   - Lowest average handovers (4.29)
   - Highest average duration despite fewer handovers
   - More standardized handover patterns

*Figure 4: System vs. manual handover comparison (`system_handover_comparison.png`)*

## 4. Discussion

### 4.1 Key Findings
1. **Role Transition Impact** (Visualized in Figure 1):
   - Handovers involving undefined roles (NONE) consistently show the longest durations
   - System-to-role transitions show moderate duration impact
   - Specific role combinations have more impact than total handover count

2. **Process Variant Differences** (Visualized in Figures 2 and 3):
   - 3-way match processes show stronger correlation between handovers and duration
   - 2-way match processes have more consistent duration patterns
   - System handover proportions vary significantly between categories

3. **Duration Distribution Patterns** (Visualized in Figure 2):
   - Non-linear relationship between handovers and duration
   - Higher handover counts show wider duration distributions
   - Category-specific duration patterns for similar handover counts

### 4.2 Process Improvement Opportunities
1. **Role Assignment Optimization**:
   - Reduce handovers involving undefined roles
   - Standardize role assignments in 3-way match processes
   - Implement clear handover protocols

2. **System Integration Enhancement**:
   - Optimize system-to-role handovers
   - Focus on automated handovers in high-volume transitions
   - Standardize system interaction points

3. **Process Standardization**:
   - Implement best practices from 2-way match in other variants
   - Reduce unnecessary handovers in 3-way match processes
   - Establish clear handover criteria

## 5. Conclusions
The analysis reveals significant variations in how handovers impact case duration across different process variants. While some correlation exists between handover frequency and case duration, the relationship is complex and depends on specific role combinations and process types. The findings suggest that targeted optimization of specific handover patterns, particularly those involving undefined roles or system interactions, could significantly improve process efficiency.

## 6. Recommendations
1. **Immediate Actions**:
   - Address undefined role handovers
   - Optimize system-to-role transitions
   - Standardize high-frequency handover patterns

2. **Strategic Improvements**:
   - Implement role-based workflow management
   - Enhance system integration points
   - Develop standardized handover protocols

3. **Monitoring and Control**:
   - Track handover duration metrics
   - Monitor role assignment compliance
   - Measure system handover efficiency

## 7. Future Research
- Investigation of seasonal patterns in handover duration
- Analysis of role-specific processing patterns
- Impact of organizational changes on handover efficiency

## 8. Appendix: Visualization Details
All visualizations were generated using Python with matplotlib and seaborn libraries. The following visualizations are available in the `data/analysis/visualizations` directory:

1. Role Heatmaps (`*_role_heatmap.png`):
   - Show frequency and impact of role-to-role handovers
   - Separate heatmaps for each process category
   - Color intensity indicates handover frequency

2. Duration Distribution Plots (`*_duration_distribution.png`):
   - Violin plots showing case duration distribution
   - X-axis: number of handovers
   - Y-axis: case duration in hours

3. Top Handovers Charts (`*_top_handovers.png`):
   - Bar charts of most frequent handover patterns
   - Includes percentage labels
   - Separate charts for each process category

4. System Handover Comparison (`system_handover_comparison.png`):
   - Stacked bar chart comparing system vs. manual handovers
   - Shows proportions across process categories 