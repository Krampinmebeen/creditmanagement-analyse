import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def build_sankey_diagram(classified_threads_df: pd.DataFrame, output_path: str = "./output/sankey_root_cause.html") -> str:
    """
    Generate an interactive Plotly Sankey diagram mapping Category -> Root Cause -> Outcome.
    Exports a standalone HTML file.
    """
    if classified_threads_df.empty:
        print("[Visualizer] Warning: Empty DataFrame provided. Sankey diagram generation skipped.")
        return ""

    # Aggregate flow counts
    # Flow 1: Category -> Root Cause
    flow_cat_root = classified_threads_df.groupby(['category', 'root_cause'], as_index=False).agg(
        value=('thread_id', 'count')
    ).rename(columns={'category': 'source', 'root_cause': 'target'})

    # Flow 2: Root Cause -> Outcome
    flow_root_outcome = classified_threads_df.groupby(['root_cause', 'outcome'], as_index=False).agg(
        value=('thread_id', 'count')
    ).rename(columns={'root_cause': 'source', 'outcome': 'target'})

    flows = pd.concat([flow_cat_root, flow_root_outcome], ignore_index=True)

    # Unique list of nodes
    all_nodes = list(pd.unique(flows[['source', 'target']].values.ravel('K')))
    node_map = {node: idx for idx, node in enumerate(all_nodes)}

    sources = flows['source'].map(node_map).tolist()
    targets = flows['target'].map(node_map).tolist()
    values = flows['value'].tolist()

    # Color palette
    colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
    ]
    node_colors = [colors[i % len(colors)] for i in range(len(all_nodes))]

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=all_nodes,
            color=node_colors
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color="rgba(180, 180, 180, 0.4)"
        )
    )])

    fig.update_layout(
        title_text="<b>Credit Management Thread Flow: Category ➔ Root Cause ➔ Outcome</b>",
        font_size=13,
        font_family="Arial, sans-serif",
        height=700,
        margin=dict(l=20, r=20, t=60, b=20)
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.write_html(output_path)
    print(f"[Visualizer] Sankey diagram exported successfully to: {output_path}")
    return output_path

def build_cumulative_volume_chart(classified_threads_df: pd.DataFrame, output_path: str = "./output/cumulative_volume_over_time.html") -> str:
    """
    Generate an interactive Plotly chart showing monthly new and cumulative thread volume over time
    broken down by Credit Category and Root Causes.
    """
    if classified_threads_df.empty:
        return ""

    df = classified_threads_df.copy()
    df['first_email_date'] = pd.to_datetime(df['first_email_date'], utc=True)
    df['month_str'] = df['first_email_date'].dt.strftime('%Y-%m')

    # Group by Month and Category
    monthly_cat = df.groupby(['month_str', 'category']).size().unstack(fill_value=0)
    months = sorted(monthly_cat.index.tolist())
    monthly_cat = monthly_cat.reindex(months, fill_value=0)
    cumulative_cat = monthly_cat.cumsum()

    # Subplots: Row 1 = Cumulative Volume, Row 2 = Monthly Inflow
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=(
            "<b>Cumulative Thread Volume by Issue Category (Last 2 Years)</b>",
            "<b>Monthly New Thread Inflow by Category</b>"
        )
    )

    category_colors = {
        "Dunning & Overdue": "#d62728",
        "General Credit Query": "#1f77b4",
        "Process & PO Issues": "#ff7f0e",
        "Invoice Dispute": "#9467bd",
        "Payment Terms & Limit": "#2ca02c",
        "Payment Allocation": "#17becf"
    }

    # Trace 1: Cumulative
    for cat in cumulative_cat.columns:
        color = category_colors.get(cat, "#7f7f7f")
        fig.add_trace(
            go.Scatter(
                x=months,
                y=cumulative_cat[cat],
                mode='lines+markers',
                name=cat,
                line=dict(width=2.5, color=color),
                legendgroup=cat,
                hovertemplate="<b>%{x}</b><br>" + cat + " Cumulative: <b>%{y:,}</b> threads<extra></extra>"
            ),
            row=1, col=1
        )

        # Trace 2: Monthly Inflow (Bar)
        fig.add_trace(
            go.Bar(
                x=months,
                y=monthly_cat[cat],
                name=cat,
                marker_color=color,
                legendgroup=cat,
                showlegend=False,
                hovertemplate="<b>%{x}</b><br>" + cat + " Inflow: <b>%{y:,}</b> threads<extra></extra>"
            ),
            row=2, col=1
        )

    fig.update_layout(
        barmode='stack',
        height=850,
        font_family="Arial, sans-serif",
        font_size=12,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=50, r=40, t=100, b=50)
    )

    fig.update_yaxes(title_text="Cumulative Threads", row=1, col=1)
    fig.update_yaxes(title_text="Monthly Threads", row=2, col=1)
    fig.update_xaxes(title_text="Month", row=2, col=1)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.write_html(output_path)
    print(f"[Visualizer] Cumulative volume chart exported successfully to: {output_path}")
    return output_path
