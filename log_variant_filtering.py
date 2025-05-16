import os
import pandas as pd
import pm4py
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.statistics.variants.log import get as variants_module
from collections import Counter
import argparse

def load_log(file_path):
    """Load an event log from a file path."""
    if file_path.endswith('.xes'):
        return xes_importer.apply(file_path)
    elif file_path.endswith('.csv'):
        log_df = pd.read_csv(file_path)
        return pm4py.format_dataframe(log_df, case_id='case_id', activity_key='activity', timestamp_key='timestamp')
    else:
        raise ValueError(f"Unsupported file format for {file_path}")

def get_variants(log):
    """Extract variants from the log with their frequencies."""
    variant_stats = variants_module.get_variants_along_with_case_durations(log)
    variants = {variant: len(cases) for variant, cases in variant_stats.items()}
    return dict(sorted(variants.items(), key=lambda x: x[1], reverse=True))

def filter_by_coverage(log, variants, coverage_percentage):
    """Filter log to include variants that cover a specific percentage of cases."""
    total_cases = sum(variants.values())
    target_coverage = total_cases * (coverage_percentage / 100)
    
    accumulated = 0
    selected_variants = []
    
    for variant, freq in variants.items():
        accumulated += freq
        selected_variants.append(variant)
        if accumulated >= target_coverage:
            break
    
    return pm4py.filter_variants(log, selected_variants)

def filter_top_n(log, variants, n):
    """Filter log to include only the top N most frequent variants."""
    top_variants = list(variants.keys())[:n]
    return pm4py.filter_variants(log, top_variants)

def save_filtered_log(filtered_log, output_path):
    """Save the filtered log to a file."""
    if output_path.endswith('.xes'):
        pm4py.write_xes(filtered_log, output_path)
    elif output_path.endswith('.csv'):
        df = pm4py.convert_to_dataframe(filtered_log)
        df.to_csv(output_path, index=False)
    else:
        raise ValueError(f"Unsupported output format for {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Filter event logs based on variant coverage or top N variants.')
    parser.add_argument('--data_dir', type=str, default='data/filtered', help='Directory containing log files')
    parser.add_argument('--output_dir', type=str, default='data/variant_filtered', help='Directory to save filtered logs')
    parser.add_argument('--coverage', type=float, help='Coverage percentage (e.g., 80 for 80%)')
    parser.add_argument('--top_n', type=int, help='Number of top variants to keep')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    if not args.coverage and not args.top_n:
        print("Error: You must specify either --coverage or --top_n")
        return
    
    # Process all log files in the data directory
    for filename in os.listdir(args.data_dir):
        if filename.endswith('.xes') or filename.endswith('.csv'):
            file_path = os.path.join(args.data_dir, filename)
            print(f"Processing {filename}...")
            
            try:
                log = load_log(file_path)
                variants = get_variants(log)
                
                base_name = os.path.splitext(filename)[0]
                
                if args.coverage:
                    filtered_log = filter_by_coverage(log, variants, args.coverage)
                    output_path = os.path.join(args.output_dir, f"{base_name}_coverage_{int(args.coverage)}.xes")
                    save_filtered_log(filtered_log, output_path)
                    print(f"  - Filtered log with {args.coverage}% coverage saved to {output_path}")
                
                if args.top_n:
                    filtered_log = filter_top_n(log, variants, args.top_n)
                    output_path = os.path.join(args.output_dir, f"{base_name}_top_{args.top_n}.xes")
                    save_filtered_log(filtered_log, output_path)
                    print(f"  - Filtered log with top {args.top_n} variants saved to {output_path}")
                    
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
    
    print("Filtering completed.")

if __name__ == "__main__":
    main()