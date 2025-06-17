import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Set style
plt.style.use('default')
sns.set_theme(style="whitegrid")

# Data for correlation analysis
correlation_data = {
    'Process Variant': ['3-way After GR', '3-way Before GR', '2-way'],
    'Correlation': [0.403, 0.240, -0.073],
    'P-value': [3.97e-308, 0.0, 7.81e-1],
    'Number of Cases': [7931, 147240, 17]
}

# Create correlation plot
plt.figure(figsize=(10, 6))
bars = plt.bar(correlation_data['Process Variant'], correlation_data['Correlation'], color='#00838f')
plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
plt.title('Correlation between Number of Handovers and Case Duration')
plt.ylabel('Correlation Coefficient')
plt.xticks(rotation=45)

# Add value labels
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:.3f}',
             ha='center', va='bottom')

plt.tight_layout()
plt.savefig('handover_keypoints_visualisations/correlation_analysis.png')
plt.close()

# Data for top handovers in 3-way After GR
three_way_after_data = {
    'Handover': [
        'GR → SES',
        'IR → Clear',
        'SES → GR',
        'Vendor → GR',
        'Vendor → IR'
    ],
    'Percentage': [14.98, 14.34, 10.56, 9.14, 8.72]
}

# Create bar plot for 3-way After GR
plt.figure(figsize=(12, 6))
bars = plt.bar(three_way_after_data['Handover'], three_way_after_data['Percentage'], color='#00838f')
plt.title('Top 5 Handover Points in 3-way After GR Process')
plt.ylabel('Percentage of Total Handovers')
plt.xticks(rotation=45)

# Add value labels
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:.2f}%',
             ha='center', va='bottom')

plt.tight_layout()
plt.savefig('handover_keypoints_visualisations/three_way_after_handovers.png')
plt.close()

# Data for top handovers in 3-way Before GR
three_way_before_data = {
    'Handover': [
        'IR → Clear',
        'GR → IR',
        'Vendor → GR',
        'PO → Vendor',
        'Vendor → IR'
    ],
    'Percentage': [16.0, 11.51, 11.45, 11.27, 10.29]
}

# Create bar plot for 3-way Before GR
plt.figure(figsize=(12, 6))
bars = plt.bar(three_way_before_data['Handover'], three_way_before_data['Percentage'], color='#00838f')
plt.title('Top 5 Handover Points in 3-way Before GR Process')
plt.ylabel('Percentage of Total Handovers')
plt.xticks(rotation=45)

# Add value labels
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:.2f}%',
             ha='center', va='bottom')

plt.tight_layout()
plt.savefig('handover_keypoints_visualisations/three_way_before_handovers.png')
plt.close()

# Create case volume comparison
plt.figure(figsize=(10, 6))
bars = plt.bar(correlation_data['Process Variant'], correlation_data['Number of Cases'], color='#00838f')
plt.title('Number of Cases by Process Variant')
plt.ylabel('Number of Cases (log scale)')
plt.yscale('log')
plt.xticks(rotation=45)

# Add value labels
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height,
             f'{int(height):,}',
             ha='center', va='bottom')

plt.tight_layout()
plt.savefig('handover_keypoints_visualisations/case_volume_comparison.png')
plt.close()

# Role distribution data for 3-way After GR top handover
role_distribution_after = {
    'Role': ['BATCH', 'Role_8', 'Role_7', 'Others'],
    'Percentage': [46.76, 40.82, 4.7, 7.72]
}

# Create pie chart for role distribution
plt.figure(figsize=(10, 8))
plt.pie(role_distribution_after['Percentage'], labels=role_distribution_after['Role'], autopct='%1.1f%%')
plt.title('Role Distribution for Top Handover in 3-way After GR\n(Record Goods Receipt → Record Service Entry Sheet)')
plt.savefig('handover_keypoints_visualisations/role_distribution_after.png')
plt.close()

# Role distribution data for 3-way Before GR top handover
role_distribution_before = {
    'Role': ['Role_16 → Role_15', 'BATCH → Role_15', 'Role_16 → NONE', 'Others'],
    'Percentage': [89.67, 3.91, 2.35, 4.07]
}

# Create pie chart for role distribution
plt.figure(figsize=(10, 8))
plt.pie(role_distribution_before['Percentage'], labels=role_distribution_before['Role'], autopct='%1.1f%%')
plt.title('Role Distribution for Top Handover in 3-way Before GR\n(Record Invoice Receipt → Clear Invoice)')
plt.savefig('handover_keypoints_visualisations/role_distribution_before.png')
plt.close() 