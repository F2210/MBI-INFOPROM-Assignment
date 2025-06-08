
import os
import gc
import logging
import traceback
from datetime import datetime
import json
import pm4py
from pm4py.objects.log.obj import EventLog
from analyze_logs import count_events
from resources_handover_preprocessing import get_resource_type, describe_log, compare_activities_in_folder, import_user_roles_from_txt
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.exporter.xes import exporter as xes_exporter
from pm4py.algo.organizational_mining.roles import algorithm as roles_algo
from pm4py.objects.org.roles.obj import Role

import re


INPUT_FILE = './data/BPI_Challenge_2019.xes'
INPUT_DIR = './data/filtered'
OUTPUT_DIR = './data/filtered/preprocessed_handover'

COMPLETE_FILTERED_LOG = 'complete_filtered_log.xes'
SPLITTED_LOG_PREFIX = 'filtered_log_'

RESOURCE_TYPES = ["NONE", "Batch", "User"]

# Case attribute settings
CATEGORY_ATTRIBUTE = "Item Category" # for some reason: do not include "case:" in the name
CASE_ID_ATTRIBUTE = "concept:name"

# Item categories for grouping - modify these as needed
ITEM_CATEGORIES = {
    "group_3_way_before": ["3-way match, invoice before GR"],
    "group_3_way_after": ["3-way match, invoice after GR"],
    "group_2_way": ["2-way match"],
    "group_consignment": ["Consignment"]
}


# Merge all XES logs in OUTPUT_DIR into a single EventLog
def merge_xes_logs(input_dir, output_file=COMPLETE_FILTERED_LOG):
    merged_log = EventLog()
    for filename in os.listdir(input_dir):
        if filename.endswith('.xes'):
            file_path = os.path.join(input_dir, filename)
            try:
                log = xes_importer.apply(file_path)
                for trace in log:
                    merged_log.append(trace)
            except Exception as e:
                logging.error(f"Error reading {file_path}: {e}\n{traceback.format_exc()}")
    output_path = os.path.join(input_dir, output_file)
    pm4py.write_xes(merged_log, output_path)
    return merged_log

def split_on_resource_type(output_dir, input_log_name, output_log_name=COMPLETE_FILTERED_LOG):
    # Prepare sublogs for each resource type
    sublogs = {"NONE": [], "Batch": [], "User": []}

    # Import the log using pm4py
    log = xes_importer.apply(input_log_name)

    # Prepare sublogs for each resource type
    sublogs = {"NONE": EventLog(), "Batch": EventLog(), "User": EventLog()}
    other_count = 0

    for trace in log:
        # Collect events by resource type for this trace
        events_by_type = {"NONE": [], "Batch": [], "User": [] , "Other": []}
        for event in trace:
            resource = event.get("org:resource", "NONE")
            rtype = get_resource_type(resource)
            if rtype in events_by_type:
                events_by_type[rtype].append(event)
            else:
                events_by_type["Other"].append(event)
                other_count += 1
        # For each resource type, if there are events, create a trace
        for rtype, events in events_by_type.items():
            if events:
                # Copy trace attributes
                new_trace = trace.__class__()
                for attr in trace.attributes:
                    new_trace.attributes[attr] = trace.attributes[attr]
                for event in events:
                    new_event = dict(event)
                    new_trace.append(new_event)
                sublogs[rtype].append(new_trace)
        
    print(f"Processed {len(log)} traces, found {other_count} events with unknown resource type.")

    # Export sublogs to XES
    for rtype, sublog in sublogs.items():
        if len(sublog) > 0:
            output_file = os.path.join(output_dir, f"{output_log_name}{rtype}.xes")
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True) 
            xes_exporter.apply(sublog, output_file)
            print(f"Exported {len(sublog)} traces with {sum(len(trace) for trace in sublog)} events to {output_file}")

def describe_logs():
    for rtype in RESOURCE_TYPES:
        input_file = os.path.join(OUTPUT_DIR, f"{SPLITTED_LOG_PREFIX}{rtype}.xes")
        if os.path.exists(input_file):
            print(f"Describing log for resource type: {rtype}")
            describe_log(input_file)
        else:
            print(f"Log file for resource type {rtype} does not exist. Skipping description.")

def apply_organizational_roles(xes_log_path):
    """
    Applies pm4py's organizational_mining.roles function to the given XES log file.
    Returns the roles dictionary.
    """

    log = xes_importer.apply(xes_log_path)
    roles = roles_algo.apply(log)
    print(f"Extracted {len(roles)} roles from {xes_log_path}")
    return roles

def add_user_roles_to_log(log_path, resource_roles_list):
    """
    Adds a 'userRole' attribute to each event in the log based on the provided resource_roles_list.
    resource_roles_list: List of tuples/lists [(resource, role), ...]
    """

    user_to_role = {}

    for role_index, user_list in enumerate(resource_roles_list):
        for user in user_list:
            # Optionally prevent overwriting if a user appears in multiple roles
            user_to_role[user] = role_index


    # Load the log
    log = xes_importer.apply(log_path)

    # Add 'userRole' attribute to each event
    for trace in log:
        for event in trace:
            resource = event.get("org:resource")
            if resource and resource in user_to_role:
                event["userRole"] = f"role_{user_to_role[resource]}"
            else:
                event["userRole"] = "Unknown"

    # Export the modified log
    output_file = os.path.splitext(log_path)[0] + "_with_UserRole.xes"
    xes_exporter.apply(log, output_file)
    print(f"Added userRole attribute to events and exported to {output_file}")

def create_resource_lists(roles):
    role_resources = []
    for role in roles:
        if not isinstance(role, str):
            role = str(role)
        match = re.search(r"Originators importance\s*{([^}]*)}", role)
        if match:
            users_str = match.group(1)
            user_ids = [user.split(":")[0].strip().strip("'\"") for user in users_str.split(",")]
        else:
            user_ids = []
        role_resources.append(user_ids)

    return role_resources

def copy_resource_to_userrole(xes_file_path):
    """
    Imports a log from the given XES file, copies the value of the 'org:resource' attribute
    to a new attribute 'userRole' for each event, and exports the modified log to a new XES file.
    """
    log = xes_importer.apply(xes_file_path)
    for trace in log:
        for event in trace:
            resource = event.get("org:resource", "Unknown")
            event["userRole"] = resource
    output_file = os.path.splitext(xes_file_path)[0] + "_with_UserRole.xes"
    xes_exporter.apply(log, output_file)
    print(f"Copied 'org:resource' to 'userRole' and exported to {output_file}")

def combine_logs():
    combined_log = EventLog()
    for rtype in RESOURCE_TYPES:
        log_path = os.path.join(OUTPUT_DIR, f"{SPLITTED_LOG_PREFIX}{rtype}_with_UserRole.xes")
        if os.path.exists(log_path):
            log = xes_importer.apply(log_path)
            for trace in log:
                combined_log.append(trace)
        else:
            print(f"Log file {log_path} does not exist. Skipping.")

    # Export the combined log
    combined_output_path = os.path.join(OUTPUT_DIR, "combined_with_roles.xes")
    xes_exporter.apply(combined_log, combined_output_path)
    print(f"Combined log with roles exported to {combined_output_path}")
    return combined_log

def devide_on_category_item(filtered_log, category_values, output_dir):
    item_categories = ITEM_CATEGORIES
    for group_name, category_values in item_categories.items():
        # Use case filtering since category is a case attribute
        group_categorized = pm4py.filter_trace_attribute_values(
            filtered_log,
            CATEGORY_ATTRIBUTE, 
            category_values, 
            retain=True,
            case_id_key=CASE_ID_ATTRIBUTE
        )
        output_path = os.path.join(output_dir, f"{group_name}.xes")
        pm4py.write_xes(group_categorized, output_path)

if __name__ == "__main__":
    # Example usage:
    # MERGE CATEGORIZED LOGS FROM
    merged_log = merge_xes_logs(INPUT_DIR)
    print(f"Merged log contains {len(merged_log)} traces.")

    # 1. SPLIT ON RESOURCE TYPE
    split_on_resource_type(OUTPUT_DIR, os.path.join(INPUT_DIR, COMPLETE_FILTERED_LOG), SPLITTED_LOG_PREFIX)
    # describe_logs()

    # 2. CLUSTER ON USER ROLES
    user_log_path = os.path.join(OUTPUT_DIR, "userRoles.txt")
    if os.path.exists(user_log_path):
        roles = import_user_roles_from_txt(user_log_path)
    else:
        roles = apply_organizational_roles(user_log_path)

    # export_user_roles_to_txt(roles)

    # 3. ADD USER ROLES TO LOGS
    role_resources = create_resource_lists(roles)
    add_user_roles_to_log(os.path.join(OUTPUT_DIR, f"{SPLITTED_LOG_PREFIX}User.xes"), role_resources)


    # 4. COPY RESOURCE TO USERROLE
    for path in [
        os.path.join(OUTPUT_DIR, f"{SPLITTED_LOG_PREFIX}Batch.xes"),
        os.path.join(OUTPUT_DIR, f"{SPLITTED_LOG_PREFIX}NONE.xes")
    ]:
        if os.path.exists(path):
            copy_resource_to_userrole(path)

    # 5. COMBINE LOGS
    combined_logs_with_userrole = combine_logs()
    print("Processing complete.")

    if(combined_logs_with_userrole is None):
        combined_logs_with_userrole = xes_importer.apply(os.path.join(OUTPUT_DIR, "combined_with_roles.xes"))

    categorized_items_dir = os.path.join(OUTPUT_DIR, "categorized_items")
    if not os.path.exists(categorized_items_dir):
        os.makedirs(categorized_items_dir)

    # 6. DIVIDE ON ITEM CATEGORIES
    devide_on_category_item(combined_logs_with_userrole, ITEM_CATEGORIES, categorized_items_dir)
    
    # compare_activities_in_folder(OUTPUT_DIR)