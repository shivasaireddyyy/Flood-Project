"""Decision-support rules: rescue priority, recommendations, evacuation steps."""

LEVEL_WEIGHT = {"Low": 10, "Medium": 50, "High": 90}

RECOMMENDATIONS = {
    "Low": ["Stay informed through official weather and flood bulletins.",
            "Keep drains and nearby water channels clear of debris.",
            "Review your family emergency plan and keep contacts handy."],
    "Medium": ["Prepare an emergency kit: water, food, medicines, torch, power bank, documents.",
               "Move valuables and electronics to higher shelves or floors.",
               "Identify your nearest shelter and the route to it.",
               "Avoid low-lying roads, underpasses and river banks."],
    "High": ["Evacuate low-lying areas now toward the nearest higher-ground shelter.",
             "Switch off electricity and gas at the mains before leaving.",
             "Never walk or drive through flowing floodwater.",
             "Help children, elderly and disabled people first; call emergency services if trapped.",
             "Follow official evacuation orders and keep your phone charged."],
}


def priority_score(probs, density="Medium", vulnerable_groups=0, medical_dependence=False):
    """0-100 score: expected risk weighted by exposure and vulnerability."""
    expected = sum(probs.get(l, 0) * w for l, w in LEVEL_WEIGHT.items())
    factor = {"Low": 0.9, "Medium": 1.0, "High": 1.2}[density]
    factor += 0.08 * vulnerable_groups + (0.1 if medical_dependence else 0)
    return round(min(100.0, expected * factor), 1)


def priority_label(score):
    if score >= 75:
        return "Critical"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Moderate"
    return "Routine"


def evacuation_steps(level, nearest):
    if level == "Low":
        return ["No evacuation needed. Monitor conditions."]
    steps = []
    if nearest is not None and not nearest.empty:
        n = nearest.iloc[0]
        kind = "government safe house" if n.get("govt") else n["type"]
        steps.append(f"Head to {n['name']} ({kind}), about {n.distance_km:.1f} km away "
                     f"(~{int(n.walk_min)} min walk / ~{int(n.drive_min)} min drive).")
        if n.get("higher_ground") == "Yes":
            steps.append("This location is on higher ground than your position.")
        steps.append(f"Backup options: " + ", ".join(nearest["name"].iloc[1:3].tolist()) if len(nearest) > 1
                     else "Check local authorities for additional shelters.")
    else:
        steps.append("No safe locations loaded. Upload a shelters CSV or enable OpenStreetMap lookup.")
    if level == "High":
        steps.append("Leave immediately; do not wait for water to enter your area.")
    return steps
