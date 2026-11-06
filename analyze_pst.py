import os
import argparse
import sys
import pandas as pd

from src.extractor import parse_pst_file, generate_sample_credit_data
from src.threading import reconstruct_threads_and_compute_metrics
from src.classifier import classify_threads
from src.visualizer import build_sankey_diagram

def main():
    parser = argparse.ArgumentParser(description="Credit Management PST Email Analysis Pipeline")
    parser.add_argument("--pst-path", type=str, help="Path to local .pst email export file")
    parser.add_argument("--years", type=float, default=2.0, help="Window size in years (default: 2.0)")
    parser.add_argument("--output-dir", type=str, default="./output", help="Directory for output deliverables")
    parser.add_argument("--demo-sample", action="store_true", help="Run pipeline on synthetic sample data for testing/demo")

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    print("=" * 70)
    print(" CREDIT MANAGEMENT PST EMAIL ANALYSIS PIPELINE")
    print(f" Timeframe Window: Last {args.years} Years")
    print("=" * 70)

    # Step 1: Extraction / Ingestion
    if args.demo_sample or not args.pst_path:
        print("[Pipeline] No PST path provided or --demo-sample flag active. Generating synthetic sample dataset...")
        emails_df = generate_sample_credit_data(years=args.years, num_threads=120)
    else:
        print(f"[Pipeline] Processing PST file: {args.pst_path}")
        emails_df = parse_pst_file(args.pst_path, years=args.years)

    if emails_df.empty:
        print("[Pipeline] Error: No emails extracted. Exiting pipeline.")
        sys.exit(1)

    # Save raw filtered emails
    parquet_path = os.path.join(args.output_dir, "raw_emails_filtered.parquet")
    emails_df.to_parquet(parquet_path, index=False)
    print(f"[Pipeline] Saved raw filtered email metadata to: {parquet_path}")

    # Step 2: Thread Reconstruction & Metrics
    print("\n[Pipeline] Step 2: Reconstructing email conversation threads in DuckDB...")
    threads_df = reconstruct_threads_and_compute_metrics(emails_df)

    # Step 3: Taxonomy Classification
    print("\n[Pipeline] Step 3: Classifying credit management categories and root causes...")
    classified_df = classify_threads(threads_df)

    # Save summary metrics
    csv_metrics_path = os.path.join(args.output_dir, "credit_thread_metrics.csv")
    export_cols = ['thread_id', 'category', 'root_cause', 'outcome', 'email_count', 'duration_days', 'avg_response_hours', 'subject_clean', 'first_email_date', 'last_email_date']
    classified_df[export_cols].to_csv(csv_metrics_path, index=False)
    print(f"[Pipeline] Exported thread metrics CSV to: {csv_metrics_path}")

    # Step 4: Sankey Diagram Generation
    print("\n[Pipeline] Step 4: Generating interactive Sankey diagram...")
    html_sankey_path = os.path.join(args.output_dir, "sankey_root_cause.html")
    build_sankey_diagram(classified_df, output_path=html_sankey_path)

    # Summary Statistics to Console
    print("\n" + "=" * 70)
    print(" ANALYSIS SUMMARY RESULTS")
    print("=" * 70)
    print(f" Total Filtered Emails:      {len(emails_df):,}")
    print(f" Total Unique Threads:        {len(classified_df):,}")
    print(f" Avg Emails / Thread:         {classified_df['email_count'].mean():.2f}")
    print(f" Avg Thread Duration (Days):  {classified_df['duration_days'].mean():.2f} days")
    print(f" Avg Response Lag (Hours):    {classified_df['avg_response_hours'].mean():.2f} hours")
    print("\n Breakdown by Credit Category:")
    cat_summary = classified_df.groupby('category').agg(
        thread_count=('thread_id', 'count'),
        avg_emails=('email_count', 'mean'),
        avg_days=('duration_days', 'mean')
    ).reset_index()
    print(cat_summary.to_string(index=False))

    print("\n Artifacts generated:")
    print(f"  1. Parquet Emails: {parquet_path}")
    print(f"  2. Metrics CSV:    {csv_metrics_path}")
    print(f"  3. Sankey HTML:    {html_sankey_path}")
    print("=" * 70)

if __name__ == "__main__":
    main()
