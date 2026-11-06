import os
import pandas as pd
import plotly.graph_objects as go

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
        value=('thread_id', 'count'),
        avg_duration=('duration_days', 'mean')
    ).rename(columns={'category': 'source', 'root_cause': 'target'})

    # Flow 2: Root Cause -> Outcome
    flow_root_outcome = classified_threads_df.groupby(['root_cause', 'outcome'], as_index=False).agg(
        value=('thread_id', 'count'),
        avg_duration=('duration_days', 'mean')
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
