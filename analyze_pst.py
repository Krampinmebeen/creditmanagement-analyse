import os
import argparse
import sys
import pandas as pd

from src.extractor import parse_pst_file, generate_sample_credit_data
from src.threading import reconstruct_threads_and_compute_metrics
from src.classifier import classify_threads
from src.visualizer import build_sankey_diagram, build_cumulative_volume_chart

def main():
    parser = argparse.ArgumentParser(description="Credit Management PST Email Analysis Pipeline")
    parser.add_argument("--pst-path", type=str, help="Path to local .pst email export file")
    parser.add_argument("--years", type=float, default=2.0, help="Window size in years (default: 2.0)")
    parser.add_argument("--output-dir", type=str, default="./output", help="Directory for output deliverables")
    parser.add_argument("--demo-sample", action="store_true", help="Run pipeline on synthetic sample data for testing/demo")

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    print("=" * 70)
    print(" CREDIT MANAGEMENT PST EMAIL ANALYSIS PIPELINE (ADVANCED 4-LEVEL)")
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

    # Step 3: Taxonomy Classification (Hierarchical Root Cause Priority)
    print("\n[Pipeline] Step 3: Classifying credit management categories and root causes...")
    classified_df = classify_threads(threads_df)

    # Save summary metrics
    csv_metrics_path = os.path.join(args.output_dir, "credit_thread_metrics.csv")
    export_cols = ['thread_id', 'direction', 'category', 'root_cause', 'outcome', 'email_count', 'duration_days', 'avg_response_hours', 'initial_sender', 'subject_clean', 'first_email_date', 'last_email_date']
    classified_df[export_cols].to_csv(csv_metrics_path, index=False)
    print(f"[Pipeline] Exported thread metrics CSV to: {csv_metrics_path}")

    # Step 4: Visualizations
    print("\n[Pipeline] Step 4: Generating interactive visual dashboards...")
    html_sankey_path = os.path.join(args.output_dir, "sankey_root_cause.html")
    build_sankey_diagram(classified_df, output_path=html_sankey_path)

    html_cumulative_path = os.path.join(args.output_dir, "cumulative_volume_over_time.html")
    build_cumulative_volume_chart(classified_df, output_path=html_cumulative_path)

    # Monthly Cumulative CSV
    classified_df['month'] = pd.to_datetime(classified_df['first_email_date'], utc=True).dt.strftime('%Y-%m')
    monthly_summary = classified_df.groupby(['month', 'category']).size().unstack(fill_value=0)
    cumulative_summary = monthly_summary.cumsum()
    cumulative_csv_path = os.path.join(args.output_dir, "monthly_cumulative_volume.csv")
    cumulative_summary.to_csv(cumulative_csv_path)
    print(f"[Pipeline] Exported monthly cumulative volume table to: {cumulative_csv_path}")

    # Summary Statistics to Console
    print("\n" + "=" * 70)
    print(" ANALYSIS SUMMARY RESULTS (4-LEVEL HIERARCHY & RESOLUTION DYNAMICS)")
    print("=" * 70)
    print(f" Total Filtered Emails:              {len(emails_df):,}")
    print(f" Total Unique Threads:                {len(classified_df):,}")
    print(f" One-Touch Threads (1 Message):      {(classified_df['email_count']==1).sum():,} ({(classified_df['email_count']==1).mean()*100:.1f}%)")
    print(f" Active Multi-Email Threads (>1 Msg):{(classified_df['email_count']>1).sum():,} ({(classified_df['email_count']>1).mean()*100:.1f}%)")
    print(f" Overall Duration Median:            {classified_df['duration_days'].median():.2f} days | Mean: {classified_df['duration_days'].mean():.2f} days")
    
    multi_df = classified_df[classified_df['email_count'] > 1]
    if not multi_df.empty:
        print(f" Multi-Email Thread Duration Median: {multi_df['duration_days'].median():.2f} days | Mean: {multi_df['duration_days'].mean():.2f} days")
        print(f" Multi-Email Response Lag Median:    {multi_df['avg_response_hours'].median():.2f} hours")

    print("\n Breakdown by Thread Direction:")
    print(classified_df['direction'].value_counts().to_string())

    print("\n Breakdown by Credit Category (Active Multi-Email Threads Median Duration):")
    cat_records = []
    for cat, grp in classified_df.groupby('category'):
        m_grp = grp[grp['email_count'] > 1]
        cat_records.append({
            'Category': cat,
            'Total Threads': len(grp),
            'One-Touch (0d)': (grp['email_count'] == 1).sum(),
            'Multi-Touch': len(m_grp),
            'Overall Median (d)': round(grp['duration_days'].median(), 2),
            'Multi-Email Median (d)': round(m_grp['duration_days'].median(), 2) if not m_grp.empty else 0.0,
            'Mean Days': round(grp['duration_days'].mean(), 2)
        })
    cat_summary = pd.DataFrame(cat_records)
    print(cat_summary.to_string(index=False))

    print("\n Artifacts generated:")
    print(f"  1. Parquet Emails:       {parquet_path}")
    print(f"  2. Metrics CSV:          {csv_metrics_path}")
    print(f"  3. Cumulative CSV:       {cumulative_csv_path}")
    print(f"  4. Sankey HTML:          {html_sankey_path}")
    print(f"  5. Cumulative Chart HTML:{html_cumulative_path}")
    print("=" * 70)

if __name__ == "__main__":
    main()
