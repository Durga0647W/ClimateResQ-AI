import re

def normalize_location(location: str) -> str:
    if not location:
        return ""
    # 1. Trim and lowercase
    loc = location.strip().lower()
    
    # 2. Normalize commas and spaces
    loc = re.sub(r'\s*,\s*', ' ', loc)
    loc = re.sub(r'\s+', ' ', loc)
    
    # 3. Remove common city/state suffixes if the locality is present
    stopwords = ["chennai", "tamil nadu", "tamilnadu", "india", "city", "district", "tn"]
    
    # Simple regex replace for multi-word stopwords
    filtered_loc = loc
    for sw in stopwords:
        # regex to match whole word only
        filtered_loc = re.sub(r'\b' + re.escape(sw) + r'\b', '', filtered_loc).strip()
        
    filtered_loc = re.sub(r'\s+', ' ', filtered_loc).strip()
    
    if not filtered_loc:
        return loc # Fallback if entirely stopwords
        
    return filtered_loc
