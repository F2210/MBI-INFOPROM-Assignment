#!/usr/bin/env python3
"""
XES Log Analysis Utilities

This file contains functions for analyzing XES logs:
- Counting events and cases
- Analyzing log attributes
- Verifying case attributes
- Analyzing case attribute values and distributions
"""

import logging
from pm4py.statistics.attributes.log import get as attributes_get

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def count_events(log):
    """Count events in a log in a memory-efficient way"""
    count = 0
    for case in log:
        count += len(case)
    return count

def analyze_log_attributes(log):
    """Analyze all attributes in the log (event-level and case-level)"""
    # Get event attributes
    event_attributes = set()
    for case in log:
        for event in case:
            event_attributes.update(event.keys())
    
    # Get trace/case attributes (using a more memory-efficient approach)
    trace_attributes = set()
    # Only check a sample of cases to save memory
    sample_size = min(100, len(log))
    for i, case in enumerate(log):
        if i >= sample_size:
            break
        trace_attributes.update(case.attributes.keys())
    
    logger.info(f"Event attributes ({len(event_attributes)}): {sorted(event_attributes)}")
    logger.info(f"Case attributes ({len(trace_attributes)}): {sorted(trace_attributes)}")
    
    # Count the number of distinct values for each event attribute
    for attr in event_attributes:
        try:
            values = attributes_get.get_attribute_values(log, attr)
            logger.info(f"  - {attr}: {len(values)} distinct values")
        except:
            logger.info(f"  - {attr}: Unable to count distinct values")
    
    return event_attributes, trace_attributes

def verify_case_attributes(log, attributes_to_check, case_id_attribute="concept:name"):
    """Verify presence of specific case attributes in a log"""
    sample_size = min(10, len(log))
    case_count = 0
    found_attributes = {attr: 0 for attr in attributes_to_check}
    
    # Check first few cases
    for case in log[:sample_size]:
        case_count += 1
        for attr in attributes_to_check:
            if attr in case.attributes:
                found_attributes[attr] += 1
    
    # Report results
    logger.info(f"Case attribute verification (checked {case_count} cases):")
    for attr, count in found_attributes.items():
        if count == 0:
            logger.warning(f"  - {attr}: Not found in any case")
        else:
            logger.info(f"  - {attr}: Found in {count}/{case_count} cases ({count/case_count*100:.1f}%)")
    
    return found_attributes

def analyze_case_attribute_values(log, attribute_name, max_sample=1000):
    """
    Analyze the distinct values of a case attribute in the log
    
    Args:
        log: PM4Py event log
        attribute_name: The attribute to analyze
        max_sample: Maximum number of cases to sample (for large logs)
        
    Returns:
        Dictionary with values as keys and counts as values
    """
    value_counts = {}
    
    # Use a sample of cases for very large logs
    sample = log
    if len(log) > max_sample:
        sample = log[:max_sample]
        logger.info(f"Using a sample of {max_sample} cases to analyze '{attribute_name}'")

    # Iterate through cases and count attribute values
    missing_count = 0
    for case in sample:
        try:
            value = case.attributes[attribute_name]
            value_counts[value] = value_counts.get(value, 0) + 1
        except KeyError:
            missing_count += 1
    
    logger.info(f"Analysis of '{attribute_name}':")
    logger.info(f"  - Found {len(value_counts)} distinct values")
    if missing_count > 0:
        logger.info(f"  - {missing_count} cases don't have this attribute")
    
    # Print the most common values
    if value_counts:
        sorted_values = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)
        top_n = min(10, len(sorted_values))
        logger.info(f"  - Top {top_n} most frequent values:")
        for value, count in sorted_values[:top_n]:
            logger.info(f"    - '{value}': {count} cases ({count/len(sample)*100:.1f}%)")
    
    return value_counts

def analyze_xes_file(file_path):
    """
    Analyze an XES file and output key information
    
    Args:
        file_path: Path to the XES file
    """
    import pm4py
    
    logger.info(f"Analyzing XES file: {file_path}")
    
    try:
        # Import the log
        log = pm4py.read_xes(file_path)
        
        # Basic statistics
        case_count = len(log)
        event_count = count_events(log)
        logger.info(f"Log contains {case_count} cases and {event_count} events")
        
        # Attribute analysis
        event_attrs, case_attrs = analyze_log_attributes(log)
        
        # Time range
        try:
            min_ts = min(pm4py.get_event_attribute_values(log, "time:timestamp"))
            max_ts = max(pm4py.get_event_attribute_values(log, "time:timestamp"))
            logger.info(f"Time range: {min_ts} to {max_ts}")
        except:
            logger.warning("Could not determine time range")
        
        # Analyze common case attributes
        for attr in case_attrs:
            if attr != "concept:name":  # Skip case ID
                try:
                    analyze_case_attribute_values(log, attr)
                except Exception as e:
                    logger.error(f"Error analyzing attribute {attr}: {str(e)}")
        
        return {
            "case_count": case_count,
            "event_count": event_count,
            "event_attributes": list(event_attrs),
            "case_attributes": list(case_attrs)
        }
    
    except Exception as e:
        logger.error(f"Error analyzing log: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    import sys
    import os
    
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Check if a file path was provided
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            logger.info(f"Starting analysis of file: {file_path}")
            results = analyze_xes_file(file_path)
            logger.info("Analysis complete!")
            logger.info("=" * 50)
            logger.info("SUMMARY")
            logger.info("=" * 50)
            logger.info(f"Total cases: {results['case_count']}")
            logger.info(f"Total events: {results['event_count']}")
            logger.info(f"Average events per case: {results['event_count']/results['case_count']:.2f}")
            logger.info(f"Time range: {results['time_range']['min']} to {results['time_range']['max']}")
            logger.info(f"Event attributes count: {len(results['event_attributes'])}")
            logger.info(f"Case attributes count: {len(results['case_attributes'])}")
            logger.info("=" * 50)
        else:
            logger.error(f"File not found: {file_path}")
    else:
        logger.info("Usage: python analyze_logs.py <xes_file_path>")
        logger.info("Example: python analyze_logs.py ./data/BPI_Challenge_2019.xes")
