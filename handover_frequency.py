import os
import pandas as pd
from collections import Counter
from statistics import mean, median, mode
import matplotlib.pyplot as plt
from pm4py.objects.log.importer.xes import importer as xes_importer

# Paths
INPUT_FOLDER = 'data/filtered/preprocessed_handover/categorized_items'
OUTPUT_FOLDER = 'data/business_question_2'

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def calculate_handovers(trace):
    roles = [event['userRole'] for event in trace if 'userRole' in event]
    handovers_between_roles = 0
    handovers_in_roles = 0
    for i in range(1, len(roles)):
        if roles[i-1] != roles[i]:
            handovers_between_roles += 1
        else :
            handovers_in_roles += 1
    return handovers_between_roles, handovers_in_roles

def calculate_case_duration(trace):
    if len(trace) < 2:
        return 0, 1
    else:
        timestamps = [event['time:timestamp'] for event in trace if 'time:timestamp' in event]
        if len(timestamps) < 2:
            return 0, 1
        else:
            start_time = min(timestamps)
            end_time = max(timestamps)
            duration = (end_time - start_time).total_seconds()
            return duration, 0

def calculations_per_category():
    between_handovers_per_category = {}
    inside_handovers_per_category = {}
    duration_null_counts = {}
    duration_per_category = {}

    for filename in os.listdir(INPUT_FOLDER):
        if filename.endswith('.xes'):
            process_type = os.path.splitext(filename)[0]
            file_path = os.path.join(INPUT_FOLDER, filename)
            log = xes_importer.apply(file_path)
            between_handovers_per_case = {}
            inside_handovers_per_case = {}
            durations_per_case = {}
            null_count = 0
            for trace in log:
                case_id = trace.attributes.get('concept:name', None)
                handovers_between_roles, handovers_in_roles = calculate_handovers(trace)
                between_handovers_per_case[case_id] = handovers_between_roles
                inside_handovers_per_case[case_id] = handovers_in_roles

                case_duration, extra_null = calculate_case_duration(trace)
                durations_per_case[case_id] = case_duration
                null_count += extra_null
            
            output_path = os.path.join(OUTPUT_FOLDER, f'{process_type}_handovers.csv')
            if not os.path.exists(output_path):
                # Combine case_id, between_handover_count, and inside_handover_count into a DataFrame
                df = pd.DataFrame([
                    {
                        'case_id': case_id,
                        'between_handover_count': between_handovers_per_case[case_id],
                        'inside_handover_count': inside_handovers_per_case[case_id]
                    }
                    for case_id in between_handovers_per_case
                ])
                df.to_csv(output_path, index=False)
            between_handovers_per_category[process_type] = list(between_handovers_per_case.values())
            inside_handovers_per_category[process_type] = list(inside_handovers_per_case.values())

            output_path = os.path.join(OUTPUT_FOLDER, f'{process_type}_case_durations.csv')
            if not os.path.exists(output_path):
                # Convert durations to seconds and handle None values
                pd.DataFrame(list(durations_per_case.items()), columns=['case_id', 'case_duration_seconds']).to_csv(output_path, index=False)
            duration_null_counts[process_type] = null_count
            duration_per_category[process_type] = list(durations_per_case.values())

    # Calculate mean, median, mode for each process type
    between_handover_stats = calculate_stats(between_handovers_per_category)
    inside_handover_stats = calculate_stats(inside_handovers_per_category)
    duration_stats = calculate_stats(duration_per_category)

    # Merge all stats into one DataFrame
    stats_df = pd.DataFrame(between_handover_stats)
    if not stats_df.empty and 'process_type' in stats_df.columns:
        stats_df = stats_df.rename(columns={
            'mean': 'between_handover_mean',
            'median': 'between_handover_median',
            'mode': 'between_handover_mode'
        })
    else:
        stats_df = pd.DataFrame(columns=['process_type', 'between_handover_mean', 'between_handover_median', 'between_handover_mode'])

    inside_df = pd.DataFrame(inside_handover_stats)
    if not inside_df.empty and 'process_type' in inside_df.columns:
        inside_df = inside_df.rename(columns={
            'mean': 'inside_handover_mean',
            'median': 'inside_handover_median',
            'mode': 'inside_handover_mode'
        })
    else:
        inside_df = pd.DataFrame(columns=['process_type', 'inside_handover_mean', 'inside_handover_median', 'inside_handover_mode'])

    duration_df = pd.DataFrame(duration_stats)
    if not duration_df.empty and 'process_type' in duration_df.columns:
        duration_df = duration_df.rename(columns={
            'mean': 'duration_mean',
            'median': 'duration_median',
            'mode': 'duration_mode'
        })
    else:
        duration_df = pd.DataFrame(columns=['process_type', 'duration_mean', 'duration_median', 'duration_mode'])

    null_counts_df = pd.DataFrame(list(duration_null_counts.items()), columns=['process_type', 'null_case_duration_count'])

    # Merge all on process_type
    merged = stats_df.merge(inside_df, on='process_type', how='outer') \
                     .merge(duration_df, on='process_type', how='outer') \
                     .merge(null_counts_df, on='process_type', how='outer')

    merged.to_csv(os.path.join(OUTPUT_FOLDER, 'handover_and_duration_statistics.csv'), index=False)
    print(merged)


    # Create boxplots for each process type
    for process_type in duration_per_category:
        durations = duration_per_category[process_type]
        between_handovers = between_handovers_per_category[process_type]
        inside_handovers = inside_handovers_per_category[process_type]

        fig, ax1 = plt.subplots(figsize=(8, 6))
        fig.suptitle(f'Boxplots for {process_type}')

        # Boxplot for durations on left y-axis
        bp1 = ax1.boxplot([durations], positions=[1], widths=0.6, patch_artist=True,
                          boxprops=dict(facecolor='lightblue'), medianprops=dict(color='black'))
        ax1.set_ylabel('Duration (seconds)', color='blue')
        ax1.set_xticks([1, 2, 3])
        ax1.set_xticklabels(['Duration (seconds)', 'Handovers\nBetween Roles', 'Handovers\nWithin Roles'])

        # Boxplots for handovers on right y-axis
        ax2 = ax1.twinx()
        bp2 = ax2.boxplot([between_handovers, inside_handovers], positions=[2, 3], widths=0.6, patch_artist=True,
                          boxprops=dict(facecolor='lightgreen'), medianprops=dict(color='black'))
        ax2.set_ylabel('Handovers Count', color='green')

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plot_path = os.path.join(OUTPUT_FOLDER, f'{process_type}_boxplots.png')
        plt.savefig(plot_path)
        plt.show()

def calculate_stats(list_counts):
    stats = []
    for process_type, numbers in list_counts.items():
        if numbers:
            try:
                mode_val = mode(numbers)
            except:
                mode_val = 'No unique mode'
            stats.append({
                'process_type': process_type,
                'mean': mean(numbers),
                'median': median(numbers),
                'mode': mode_val
            })
    return stats

if __name__ == "__main__":
    calculations_per_category()
    print("Handover frequency calculation completed.")