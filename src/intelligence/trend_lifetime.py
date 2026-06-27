def predict_lifetimes(clusters: list) -> list:
    # MVP: filter out weak trends
    actionable = []
    for c in clusters:
        if c["combined_score"] > 1000:
            c["lifecycle_stage"] = "growing"
            actionable.append(c)
    return actionable
