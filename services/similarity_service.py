from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config.settings import SIMILARITY_THRESHOLD
import json

def find_similar_reports(new_description, new_location, existing_reports):
    if not existing_reports:
        return [], [], []
    def combine(desc, loc):
        return f"{desc} {loc}".strip()
    texts = [combine(r.get("description",""), r.get("location","")) for r in existing_reports]
    try:
        matrix = TfidfVectorizer(stop_words="english", ngram_range=(1,2)).fit_transform(texts + [combine(new_description,new_location)])
        scores = cosine_similarity(matrix[-1], matrix[:-1])[0]
    except Exception:
        return [], [], []
    matches = []
    corroborating = []
    duplicates = []
    for i, score in enumerate(scores):
        if float(score) >= SIMILARITY_THRESHOLD:
            # Check for Jaccard similarity to confirm duplicate vs corroborating if needed,
            # or just use the tf-idf cosine score with the specified thresholds.
            match_doc = {
                "report_id": existing_reports[i].get("report_id"),
                "similarity_score": round(float(score), 3),
                "description_preview": existing_reports[i].get("description", "")[:100],
                "location": existing_reports[i].get("location", "")
            }
            matches.append(match_doc)
            
            # As requested in the specification, similarity >= 0.80 is duplicate
            if float(score) >= 0.80:
                duplicates.append(match_doc)
            else:
                corroborating.append(match_doc)
                
    matches = sorted(matches, key=lambda x: x["similarity_score"], reverse=True)[:5]
    return matches, corroborating, duplicates

def create_or_update_cluster(incident_id, similar_reports, db):
    if not similar_reports: return None
    from database.models import IncidentCluster
    cluster_id = f"CLU-{incident_id}"
    ids = [r["report_id"] for r in similar_reports]
    scores = {r["report_id"]:r["similarity_score"] for r in similar_reports}
    existing = db.query(IncidentCluster).filter_by(cluster_id=cluster_id).first()
    if existing:
        old = json.loads(existing.related_report_ids or "[]")
        existing.related_report_ids = json.dumps(list(dict.fromkeys(old+ids)))
        existing.similarity_scores = json.dumps(scores)
    else:
        db.add(IncidentCluster(cluster_id=cluster_id, primary_incident_id=incident_id,
                               related_report_ids=json.dumps(ids), similarity_scores=json.dumps(scores)))
    db.commit()
    return cluster_id
