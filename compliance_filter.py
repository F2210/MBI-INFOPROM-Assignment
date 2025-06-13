#!/usr/bin/env python3
"""
BPI Challenge 2019 Compliance Filtering Script

This script filters event logs to identify compliant and non-compliant cases based on
the specific business rules for the BPI Challenge 2019 purchase order handling process.

The script implements compliance rules for four types of procurement flows:
1. 3-way match, invoice after goods receipt
2. 3-way match, invoice before goods receipt  
3. 2-way match (no goods receipt needed)
4. Consignment

For each category, specific compliance rules are applied based on:
- Required activities (goods receipt, invoice receipt)
- Sequence constraints (invoice before/after goods receipt) 
- Value matching requirements
- Attribute-based flow validation
"""

import os
import sys
import logging
import traceback
from datetime import datetime
from collections import defaultdict, Counter
import pm4py
from pm4py.objects.log.obj import EventLog, Trace
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.exporter.xes import exporter as xes_exporter
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------
# CONFIGURATION SETTINGS
# ---------------------------

# Input/Output settings
INPUT_DIR = './data/filtered'
OUTPUT_DIR = './data/filtered'
COMPLIANT_DIR = os.path.join(OUTPUT_DIR, 'compliant')
NON_COMPLIANT_DIR = os.path.join(OUTPUT_DIR, 'non_compliant')

# Item categories and their compliance rules
ITEM_CATEGORIES = {
    "3_way_after": ["3-way match, invoice after GR"],
    "3_way_before": ["3-way match, invoice before GR"], 
    "2_way": ["2-way match"],
    "consignment": ["Consignment"]
}

# Activity patterns for compliance checking
ACTIVITY_PATTERNS = {
    # Core activities that indicate goods receipt
    "goods_receipt": [
        "Record Goods Receipt",
    ],
    
    # Core activities that indicate invoice receipt
    "invoice_receipt": [
        "Record Invoice Receipt", 
    ],
    
    # Payment activities
    "payment": [
        "Clear Invoice",
    ],
    
    # Creation activities
    "creation": [
        "Create Purchase Order Item",
    ],

    "set_payment_block": [
        "Set Payment Block",
    ],

    "payment_block_removed": [
        "Remove Payment Block",
    ]
}

# ---------------------------
# HELPER FUNCTIONS
# ---------------------------

def load_log(log_file_path):
    """Load an XES log file with error handling"""
    try:
        logger.info(f"Loading log: {log_file_path}")
        log = xes_importer.apply(log_file_path)
        logger.info(f"Log loaded with {len(log)} cases and {sum(len(case) for case in log)} events")
        return log
    except Exception as e:
        logger.error(f"Error loading log {log_file_path}: {str(e)}")
        raise

def save_log(log, output_path):
    """Save an XES log file with error handling"""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        xes_exporter.apply(log, output_path)
        logger.info(f"Saved {len(log)} cases to {output_path}")
    except Exception as e:
        logger.error(f"Error saving log {output_path}: {str(e)}")
        raise

def get_activity_names(case):
    """Extract activity names from a case"""
    return [event["concept:name"] for event in case if "concept:name" in event]

def get_activity_timestamps(case):
    """Extract activity timestamps from a case"""
    timestamps = []
    for event in case:
        if "time:timestamp" in event:
            timestamps.append(event["time:timestamp"])
    return timestamps

def has_activity_pattern(activities, patterns):
    """Check if any activity matches the given patterns"""
    for activity in activities:
        for pattern in patterns:
            if pattern.lower() in activity.lower():
                return True
    return False

def get_matching_activities(activities, patterns):
    """Get all activities that match the given patterns"""
    matching = []
    for activity in activities:
        for pattern in patterns:
            if pattern.lower() in activity.lower():
                matching.append(activity)
                break
    return matching

def get_activity_positions(activities, patterns):
    """Get positions of activities that match the given patterns"""
    positions = []
    for i, activity in enumerate(activities):
        for pattern in patterns:
            if pattern.lower() in activity.lower():
                positions.append(i)
                break
    return positions

def check_sequence_constraint(activities, first_patterns, second_patterns):
    """Check if activities matching first_patterns occur before activities matching second_patterns"""
    first_positions = get_activity_positions(activities, first_patterns)
    second_positions = get_activity_positions(activities, second_patterns)
    
    if not first_positions or not second_positions:
        return True  # Cannot violate constraint if one of the activity types is missing
    
    # Check if all first activities occur before all second activities
    max_first = max(first_positions)
    min_second = min(second_positions)
    
    return max_first < min_second

def get_case_attributes(case):
    """Extract case-level attributes"""
    attributes = {}
    if hasattr(case, 'attributes'):
        attributes = dict(case.attributes)
    return attributes

def get_cumulative_values(case):
    """Extract cumulative net worth values from events"""
    values = []
    for event in case:
        if "Cumulative net worth (EUR)" in event:
            values.append(event["Cumulative net worth (EUR)"])
    return values

def get_po_item_value(case):
    """Extract PO item value from case attributes or first event"""
    # Try to get from case attributes first
    attributes = get_case_attributes(case)
    if "PO item value" in attributes:
        return attributes["PO item value"]
    
    # If not in attributes, get from first event with cumulative value
    values = get_cumulative_values(case)
    if values:
        return values[0]
    return 0

def count_activity_occurrences(activities, patterns):
    """Count how many times activities matching patterns occur"""
    count = 0
    for activity in activities:
        for pattern in patterns:
            if pattern.lower() in activity.lower():
                count += 1
                break
    return count

def check_3way_value_compliance(case):
    """
    Check value compliance for 3-way match cases
    Rules:
    - PO item value = Cumulated value of invoice receipts ÷ number of invoice receipts
    - Cumulated value of GRs = Cumulated value of invoice receipts  
    - Number of GRs = Number of invoice receipts
    """
    activities = get_activity_names(case)
    po_item_value = get_po_item_value(case)
    
    # Count invoice receipts and goods receipts
    invoice_count = count_activity_occurrences(activities, ACTIVITY_PATTERNS["invoice_receipt"])
    gr_count = count_activity_occurrences(activities, ACTIVITY_PATTERNS["goods_receipt"])
    
    violations = []
    
    # Check if we have the required activities to validate
    if invoice_count == 0:
        violations.append("No invoice receipts found for value validation")
        return violations
    
    if gr_count == 0:
        violations.append("No goods receipts found for value validation")
        return violations
    
    # Rule: Number of GRs = Number of invoice receipts
    if gr_count != invoice_count:
        violations.append(f"Number of goods receipts does not equal number of invoice receipts")
    
    # Get cumulative values for validation
    cumulative_values = get_cumulative_values(case)
    if not cumulative_values:
        violations.append("No cumulative values found for validation")
        return violations
    
    # Use the final cumulative value as the total
    final_cumulative_value = cumulative_values[-1]
    
    # Rule: PO item value = Cumulated value of invoice receipts ÷ number of invoice receipts
    if invoice_count > 0:
        expected_po_value = final_cumulative_value / invoice_count
        if abs(po_item_value - expected_po_value) > 0.01:  # Allow small floating point differences
            violations.append(f"PO item value does not match expected value from invoice receipts")
    
    # Check for zero values which typically indicate non-compliance
    if po_item_value == 0:
        violations.append("PO item value is zero, which may indicate invalid data")
    
    if final_cumulative_value == 0 and po_item_value != 0:
        violations.append("Cumulative value is zero but PO item value is non-zero")
    
    return violations

def check_2way_value_compliance(case):
    """
    Check value compliance for 2-way match cases
    Rules:
    - Invoice value must match original PO item value
    """
    po_item_value = get_po_item_value(case)
    cumulative_values = get_cumulative_values(case)
    
    violations = []
    
    if not cumulative_values:
        violations.append("No cumulative values found for validation")
        return violations
    
    final_cumulative_value = cumulative_values[-1]
    
    # Rule: Invoice value must match PO item value
    if abs(po_item_value - final_cumulative_value) > 0.01:  # Allow small floating point differences
        violations.append(f"Invoice value does not match PO item value")
    
    # Check for zero values
    if po_item_value == 0:
        violations.append("PO item value is zero, which may indicate invalid data")
    
    if final_cumulative_value == 0 and po_item_value != 0:
        violations.append("Invoice value is zero but PO item value is non-zero")
    
    return violations

# ---------------------------
# COMPLIANCE CHECKING FUNCTIONS
# ---------------------------

def check_3way_after_compliance(case):
    """
    Check compliance for 3-way match, invoice after GR cases
    
    Rules:
    1. Goods receipt must be recorded
    2. Invoice receipt must be recorded  
    3. Goods receipt must occur before invoice
    4. GR-based invoice verification flag must be true
    5. Goods receipt flag must be true
    6. Values must match (item, goods receipt, invoice)
    """
    activities = get_activity_names(case)
    attributes = get_case_attributes(case)
    violations = []
    
    # Rule 1: Check for goods receipt
    has_goods_receipt = has_activity_pattern(activities, ACTIVITY_PATTERNS["goods_receipt"])
    if not has_goods_receipt:
        violations.append("Missing goods receipt activity")
    
    # Rule 2: Check for invoice receipt
    has_invoice_receipt = has_activity_pattern(activities, ACTIVITY_PATTERNS["invoice_receipt"])
    if not has_invoice_receipt:
        violations.append("Missing invoice receipt activity")
    
    # Rule 3: Check sequence - goods receipt before invoice
    sequence_ok = check_sequence_constraint(
        activities, 
        ACTIVITY_PATTERNS["goods_receipt"],
        ACTIVITY_PATTERNS["invoice_receipt"]
    )
    if not sequence_ok:
        violations.append("Invoice received before goods receipt")

    # Rule 4: GR-based flag check
    has_gr_flag = str(attributes.get("GR-Based Inv. Verif.", "true")).lower() == "true"
    if not has_gr_flag:
        violations.append("GR-based invoice verification flag is not set to true")
    
    # Rule 5: check goods receipt flag is true
    has_gr_flag = str(attributes.get("Goods Receipt", "true")).lower() == "true"
    if not has_gr_flag:
        violations.append("Goods receipt flag is not set to true")

    # Rule 6: Value matching using 3-way specific rules
    value_violations = check_3way_value_compliance(case)
    violations.extend(value_violations)
        
    if violations:
        return False, violations
    return True, ["Compliant"]

def check_3way_before_compliance(case):
    """
    Check compliance for 3-way match, invoice before GR cases
    
    Rules:
    1. Goods receipt must be recorded
    2. Invoice receipt must be recorded
    3. GR-based invoice verification flag must be false
    4. Goods receipt flag must be true
    5. Payment block must be set 
    6. Payment block must be removed
    7. Payment block must be set before it is removed
    8. Payment block must be removed after Record Goods Receipt
    9. Values must match (creation, invoice, goods-receipt)
    """
    activities = get_activity_names(case)
    attributes = get_case_attributes(case)
    violations = []
    
    # Rule 1: Check for goods receipt
    has_goods_receipt = has_activity_pattern(activities, ACTIVITY_PATTERNS["goods_receipt"])
    if not has_goods_receipt:
        violations.append("Missing goods receipt activity")
    
    # Rule 2: Check for invoice receipt
    has_invoice_receipt = has_activity_pattern(activities, ACTIVITY_PATTERNS["invoice_receipt"])
    if not has_invoice_receipt:
        violations.append("Missing invoice receipt activity")
    
    # Rule 3: GR-based flag check
    has_gr_flag = str(attributes.get("GR-based Inv. Verif.", "false")).lower() == "false"
    if not has_gr_flag:
        violations.append("GR-based invoice verification flag is not set to false")
    
    # Rule 4: check goods receipt flag is true
    has_gr_flag = str(attributes.get("Goods Receipt", "true")).lower() == "true"
    if not has_gr_flag:
        violations.append("Goods receipt flag is not set to true")

    # # Rule 5: Check if the payment block is present
    # has_payment = has_activity_pattern(activities, ACTIVITY_PATTERNS["set_payment_block"])
    # if not has_payment:
    #     violations.append("Missing payment block activity")
    
    # Rule 6: Check if the payment block was removed
    has_payment_removed = has_activity_pattern(activities, ACTIVITY_PATTERNS["payment_block_removed"])
    if not has_payment_removed:
        violations.append("Payment block was not removed, which is not allowed")
    
    # # Rule 7: Check sequence - payment block must be set before it is removed
    # sequence_ok = check_sequence_constraint(
    #     activities, 
    #     ACTIVITY_PATTERNS["set_payment_block"],
    #     ACTIVITY_PATTERNS["payment_block_removed"]
    # )
    # if not sequence_ok:
    #     violations.append("Payment block was removed before it was set")

    # Rule 8: Check sequence - payment block must be removed after goods receipt
    sequence_ok = check_sequence_constraint(
        activities, 
        ACTIVITY_PATTERNS["goods_receipt"],
        ACTIVITY_PATTERNS["payment_block_removed"]
    )
    if not sequence_ok:
        violations.append("Payment block was removed before goods receipt")

    # Rule 9: Value matching using 3-way specific rules
    value_violations = check_3way_value_compliance(case)
    violations.extend(value_violations)
    
    if violations:
        return False, violations
    return True, ["Compliant"]

def check_2way_compliance(case):
    """
    Check compliance for 2-way match cases
    
    Rules:
    1. Only invoice receipt required
    2. GR based invoice verification flag must be false
    3. Goods receipt should be set to false
    4. Invoice value must match original item value
    """
    activities = get_activity_names(case)
    attributes = get_case_attributes(case)
    violations = []
    
    # Rule 1: Check for invoice receipt
    has_invoice_receipt = has_activity_pattern(activities, ACTIVITY_PATTERNS["invoice_receipt"])
    if not has_invoice_receipt:
        violations.append("Missing invoice receipt activity")

    # Rule 2: GR-based flag check
    has_gr_flag = str(attributes.get("GR-based Inv. Verif.", "false")).lower() == "false"
    if not has_gr_flag:
        violations.append("GR-based invoice verification flag is not set to false")

    # Rule 3: check goods receipt flag is false
    has_gr_flag = str(attributes.get("Goods Receipt", "false")).lower() == "false"
    if not has_gr_flag:
        violations.append("Goods receipt flag is not set to false")
    
    # Rule 4: Invoice value must match original item value using 2-way specific rules
    value_violations = check_2way_value_compliance(case)
    violations.extend(value_violations)
    
    if violations:
        return False, violations
    return True, ["Compliant"]

def check_consignment_compliance(case):
    """
    Check compliance for consignment cases
    
    Rules:
    1. Goods receipt expected
    2. GR based flag must be false
    3. Goods receipt flag must be true
    2. No invoice at purchase-order level
    3. Separate consignment invoicing process
    """
    activities = get_activity_names(case)
    attributes = get_case_attributes(case)
    violations = []
    
    # Rule 1: Check for goods receipt
    has_goods_receipt = has_activity_pattern(activities, ACTIVITY_PATTERNS["goods_receipt"])
    if not has_goods_receipt:
        violations.append("Missing goods receipt activity")
    
    # Rule 2: GR-based flag check
    has_gr_flag = str(attributes.get("GR-based Inv. Verif.", "false")).lower() == "false"
    if not has_gr_flag:
        violations.append("GR-based invoice verification flag is not set to false")
    
    # Rule 3: check goods receipt flag is true
    has_gr_flag = str(attributes.get("Goods Receipt", "true")).lower() == "true"
    if not has_gr_flag:
        violations.append("Goods receipt flag is not set to true")

    # Rule 4: No invoice at PO level (this is more complex to validate)
    has_invoice_receipt = has_activity_pattern(activities, ACTIVITY_PATTERNS["invoice_receipt"])
    if has_invoice_receipt:
        violations.append("Invoice receipt activity found at purchase order level, which is not allowed for consignment")
    
    if violations:
        return False, violations
    return True, ["Compliant"]

# ---------------------------
# MAIN COMPLIANCE FILTERING FUNCTION
# ---------------------------

def filter_compliance_by_category(log, category_name):
    """
    Filter a log into compliant and non-compliant cases based on category
    
    Args:
        log: PM4Py event log
        category_name: Category identifier (3_way_after, 3_way_before, 2_way, consignment)
    
    Returns:
        Tuple of (compliant_log, non_compliant_log, compliance_stats)
    """
    compliant_cases = []
    non_compliant_cases = []
    compliance_stats = {
        'total_cases': len(log),
        'compliant_cases': 0,
        'non_compliant_cases': 0,
        'compliance_reasons': Counter(),
        'non_compliance_reasons': Counter()
    }
    
    # Select appropriate compliance checker
    compliance_checkers = {
        '3_way_after': check_3way_after_compliance,
        '3_way_before': check_3way_before_compliance,
        '2_way': check_2way_compliance,
        'consignment': check_consignment_compliance
    }
    
    checker = compliance_checkers.get(category_name)
    if not checker:
        logger.error(f"No compliance checker found for category: {category_name}")
        return log, EventLog(), compliance_stats
    
    logger.info(f"Checking compliance for category: {category_name}")
    
    # Process each case
    for case in log:
        is_compliant, reasons = checker(case)
        
        if is_compliant:
            compliant_cases.append(case)
            compliance_stats['compliant_cases'] += 1
            for reason in reasons:
                compliance_stats['compliance_reasons'][reason] += 1
        else:
            non_compliant_cases.append(case)
            compliance_stats['non_compliant_cases'] += 1
            for reason in reasons:
                compliance_stats['non_compliance_reasons'][reason] += 1

    # Create filtered logs
    compliant_log = EventLog(compliant_cases, attributes=log.attributes, extensions=log.extensions)
    non_compliant_log = EventLog(non_compliant_cases, attributes=log.attributes, extensions=log.extensions)
    
    # Calculate compliance percentage
    if compliance_stats['total_cases'] > 0:
        compliance_rate = (compliance_stats['compliant_cases'] / compliance_stats['total_cases']) * 100
        logger.info(f"Category {category_name}: {compliance_rate:.2f}% compliant ({compliance_stats['compliant_cases']}/{compliance_stats['total_cases']})")
    
    return compliant_log, non_compliant_log, compliance_stats

def process_all_categories():
    """Process all item categories for compliance filtering"""
    
    # Create output directories
    os.makedirs(COMPLIANT_DIR, exist_ok=True)
    os.makedirs(NON_COMPLIANT_DIR, exist_ok=True)
    
    # Find all XES files in the filtered data folder
    xes_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.xes')]
    
    if not xes_files:
        logger.error("No XES files found in input directory")
        return
    
    logger.info(f"Found {len(xes_files)} XES files: {xes_files}")
    
    overall_stats = {}
    
    for xes_file in xes_files:
        # Determine category from filename
        category_name = None
        for cat in ITEM_CATEGORIES.keys():
            if cat in xes_file.lower() or xes_file.lower().startswith(f"group_{cat}"):
                category_name = cat
                break
        
        if not category_name:
            logger.warning(f"Could not determine category for file: {xes_file}")
            continue
        
        # Load the log
        log_path = os.path.join(INPUT_DIR, xes_file)
        try:
            log = load_log(log_path)
        except Exception as e:
            logger.error(f"Failed to load {xes_file}: {str(e)}")
            continue
        
        # Filter for compliance
        try:
            compliant_log, non_compliant_log, stats = filter_compliance_by_category(log, category_name)
            overall_stats[category_name] = stats
            
            # Save compliant cases
            if len(compliant_log) > 0:
                compliant_filename = f"compliant_{xes_file}"
                compliant_path = os.path.join(COMPLIANT_DIR, compliant_filename)
                save_log(compliant_log, compliant_path)
            
            # Save non-compliant cases
            if len(non_compliant_log) > 0:
                non_compliant_filename = f"non_compliant_{xes_file}"
                non_compliant_path = os.path.join(NON_COMPLIANT_DIR, non_compliant_filename)
                save_log(non_compliant_log, non_compliant_path)
                
        except Exception as e:
            logger.error(f"Error processing {xes_file}: {str(e)}")
            traceback.print_exc()
            continue
    
    # Print overall statistics
    print("\n" + "="*60)
    print("COMPLIANCE FILTERING SUMMARY")
    print("="*60)
    
    # Create a directory for statistics
    STATS_DIR = os.path.join(OUTPUT_DIR, 'stats')
    os.makedirs(STATS_DIR, exist_ok=True)
    
    
    for category, stats in overall_stats.items():
        total = stats['total_cases']
        compliant = stats['compliant_cases']
        non_compliant = stats['non_compliant_cases']
        compliance_rate = (compliant / total * 100) if total > 0 else 0
        
        print(f"\n{category.upper().replace('_', '-')} CATEGORY:")
        print(f"  Total cases: {total}")
        print(f"  Compliant: {compliant} ({compliance_rate:.2f}%)")
        print(f"  Non-compliant: {non_compliant} ({100-compliance_rate:.2f}%)")
        
        if stats['non_compliance_reasons']:
            print("  Top non-compliance reasons:")
            for reason, count in stats['non_compliance_reasons'].most_common(3):
                print(f"    - {reason}: {count} cases")
        
        # Save non-compliance reasons to JSON
        non_compliance_data = {
            'category': category,
            'total_cases': total,
            'non_compliant_cases': non_compliant,
            'reasons': dict(stats['non_compliance_reasons'])
        }
        
        # Save to JSON file
        json_filename = f"{category}_non_compliance.json"
        json_path = os.path.join(STATS_DIR, json_filename)
        with open(json_path, 'w') as f:
            json.dump(non_compliance_data, f, indent=4)
        logger.info(f"Saved non-compliance statistics to {json_path}")

if __name__ == "__main__":
    try:
        logger.info("Starting BPI Challenge 2019 compliance filtering")
        process_all_categories()
        logger.info("Compliance filtering completed successfully")
    except Exception as e:
        logger.error(f"Compliance filtering failed: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
