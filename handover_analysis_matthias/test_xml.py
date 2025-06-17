#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test file path
xes_file = './data/filtered/preprocessed_handover/processed_group_2_way.xes'

logger.info(f"Attempting to read file: {xes_file}")

try:
    # Try to parse the XML file
    tree = ET.parse(xes_file)
    root = tree.getroot()
    
    # Print basic structure
    logger.info(f"Root tag: {root.tag}")
    logger.info(f"Number of direct children: {len(root)}")
    
    # Print first trace if available
    if len(root) > 0:
        first_trace = root[0]
        logger.info(f"First trace tag: {first_trace.tag}")
        logger.info(f"Number of events in first trace: {len(first_trace)}")
        
        # Print first event if available
        if len(first_trace) > 0:
            first_event = first_trace[0]
            logger.info(f"First event tag: {first_event.tag}")
            logger.info("First event attributes:")
            for child in first_event:
                logger.info(f"  {child.tag}: {child.text}")
                
except Exception as e:
    logger.error(f"Error reading file: {str(e)}")
    import traceback
    logger.error(traceback.format_exc()) 