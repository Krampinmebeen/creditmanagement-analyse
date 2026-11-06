import duckdb
import pandas as pd
import numpy as np

def reconstruct_threads_and_compute_metrics(emails_df: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstruct email threads using DuckDB SQL analytics.
    Groups messages by parent-child references or cleaned subject line,
    and computes duration, message counts, and response statistics per thread.
    """
    if emails_df.empty:
        return pd.DataFrame()

    # Ensure optional synthetic columns exist if missing
    for col in ['true_category', 'true_root_cause', 'true_outcome']:
        if col not in emails_df.columns:
            emails_df[col] = None

    con = duckdb.connect(database=':memory:')
    con.register('raw_emails', emails_df)

    # Step 1: Assign thread cluster using SQL window functions & subject matching
    query_threading = """
    WITH base AS (
        SELECT
            message_id,
            in_reply_to,
            subject_clean,
            sender,
            body,
            date,
            COALESCE(
                in_reply_to,
                FIRST_VALUE(message_id) OVER (
                    PARTITION BY subject_clean 
                    ORDER BY date 
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                )
            ) AS root_message_id,
            true_category,
            true_root_cause,
            true_outcome
        FROM raw_emails
    ),
    threads_assigned AS (
        SELECT
            *,
            DENSE_RANK() OVER (ORDER BY root_message_id) AS thread_id
        FROM base
    )
    SELECT * FROM threads_assigned
    """

    threaded_df = con.execute(query_threading).df()
    con.register('threaded_emails', threaded_df)

    # Step 2: Aggregate metrics per thread_id
    query_metrics = """
    WITH thread_stats AS (
        SELECT
            thread_id,
            COUNT(message_id) AS email_count,
            MIN(date) AS first_email_date,
            MAX(date) AS last_email_date,
            ROUND(EPOCH(MAX(date) - MIN(date)) / 86400.0, 2) AS duration_days,
            STRING_AGG(body, ' | ') AS concatenated_body,
            FIRST(subject_clean) AS subject_clean,
            FIRST(true_category) AS true_category,
            FIRST(true_root_cause) AS true_root_cause,
            FIRST(true_outcome) AS true_outcome
        FROM threaded_emails
        GROUP BY thread_id
    ),
    response_lags AS (
        SELECT
            thread_id,
            AVG(lag_seconds) / 3600.0 AS avg_response_hours
        FROM (
            SELECT
                thread_id,
                EPOCH(date - LAG(date) OVER (PARTITION BY thread_id ORDER BY date)) AS lag_seconds
            FROM threaded_emails
        )
        WHERE lag_seconds IS NOT NULL
        GROUP BY thread_id
    )
    SELECT
        t.thread_id,
        t.subject_clean,
        t.email_count,
        t.first_email_date,
        t.last_email_date,
        t.duration_days,
        COALESCE(ROUND(r.avg_response_hours, 2), 0.0) AS avg_response_hours,
        t.concatenated_body,
        t.true_category,
        t.true_root_cause,
        t.true_outcome
    FROM thread_stats t
    LEFT JOIN response_lags r ON t.thread_id = r.thread_id
    ORDER BY t.email_count DESC, t.duration_days DESC
    """

    metrics_df = con.execute(query_metrics).df()
    con.close()

    print(f"[Threading] Successfully aggregated {len(metrics_df):,} unique email threads.")
    return metrics_df
