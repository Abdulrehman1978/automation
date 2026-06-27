class PriorityScorer:
    def score(self, trends: list) -> list:
        # MVP: sort by score
        for t in trends:
            t["priority_score"] = t["combined_score"]
        return sorted(trends, key=lambda x: x["priority_score"], reverse=True)
