
import os
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.objects.log.exporter.xes import exporter as xes_exporter
from collections import Counter

def describe_log(input_file):
    """
    Describe the log by printing key statistics.
    
    Args:
        input_file: Path to the XES file
    """
    log = xes_importer.apply(input_file)
    num_traces = len(log)
    num_events = sum(len(trace) for trace in log)
    
    print(f"Log: {os.path.basename(input_file)}")
    print(f"  - Number of traces: {num_traces}")
    print(f"  - Number of events: {num_events}")
    
    # Print unique resources and activities
    resources = set()
    activities = set()
    for trace in log:
        for event in trace:
            resources.add(event.get("org:resource", "NONE"))
            activities.add(event.get("concept:name", "UNKNOWN"))
    
    print(f"  - Unique resources: {len(resources)}")
    print(f"  - Unique activities: {len(activities)}")

def get_resource_type(resource):
    if resource == "NONE":
        return "NONE"
    elif resource.startswith("batch_"):
        return "Batch"
    elif resource.startswith("user_"):
        return "User"
    else:
        return "Other"

def compare_activities_in_folder(folder_path):
    """
    Compare activities in all XES logs in a folder and return, for each activity, the logs in which it occurs.

    Args:
        folder_path: Path to the folder containing XES files.

    Returns:
        List of tuples: (activity, [list of log filenames where it occurs])
    """
    xes_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".xes")]
    if len(xes_files) < 2:
        raise ValueError("At least two XES files must be present in the folder.")

    activity_logs = {}
    for file in xes_files:
        log = xes_importer.apply(file)
        activities = set()
        for trace in log:
            for event in trace:
                activities.add(event.get("concept:name", "UNKNOWN"))
        for activity in activities:
            if activity not in activity_logs:
                activity_logs[activity] = []
            activity_logs[activity].append(os.path.basename(file))

    output_file = os.path.join(folder_path, "resourceType_per_activity.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Activities found in the logs:\n")
        for activity, logs in activity_logs.items():
            short_logs = [log.split('_')[-1].split('.')[0] for log in logs]
            f.write(f"  - {activity}: {', '.join(short_logs)}\n")
    print(f"Activities per log exported to {output_file}")  

    return [(activity, logs) for activity, logs in activity_logs.items()]

def import_user_roles_from_txt(txt_file):
    """
    Reads user roles from a txt file exported by export_user_roles_to_txt.
    
    Args:
        txt_file: Path to the userRoles.txt file.
    
    Returns:
        List of roles (strings).
    """
    roles = []
    with open(txt_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines[1:]:  # Skip the first line (header)
            if line.startswith("Role: "):
                role = line[len("Role: "):].strip()
                roles.append(role)

    print(f"Imported {len(roles)} user roles from {txt_file}")
    return roles