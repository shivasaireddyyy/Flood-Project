"""Dataset-agnostic ML core: works with any tabular CSV."""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

LEVELS = ["Low", "Medium", "High"]
TARGET_HINTS = ["flood", "risk", "severity", "inundation", "label", "target", "class"]
HIGH_WORDS = {"high", "severe", "yes", "true", "flood", "flooded", "extreme", "critical", "danger"}
LOW_WORDS = {"low", "no", "none", "false", "safe", "normal", "noflood"}
MID_WORDS = {"medium", "moderate", "mid", "med", "warning", "alert"}


def _norm(v):
    return str(v).strip().lower().replace(" ", "").replace("_", "").replace("-", "")


def guess_target(df):
    """Pick the most likely target column by name, else the last column."""
    for hint in TARGET_HINTS:
        for c in df.columns:
            if hint in str(c).lower():
                return c
    return df.columns[-1]


def is_continuous(series):
    return pd.api.types.is_numeric_dtype(series) and series.nunique() > 10


def default_mapping(series):
    """Map each distinct target value to Low/Medium/High (user can edit)."""
    vals = series.dropna().unique().tolist()
    try:
        vals = sorted(vals)
    except TypeError:
        vals = sorted(vals, key=str)
    n, numeric = len(vals), pd.api.types.is_numeric_dtype(series)
    mapping = {}
    for i, v in enumerate(vals):
        k = _norm(v)
        if not numeric and k in HIGH_WORDS:
            lvl = "High"
        elif not numeric and k in MID_WORDS:
            lvl = "Medium"
        elif not numeric and k in LOW_WORDS:
            lvl = "Low"
        elif n == 2:
            lvl = "Low" if i == 0 else "High"
        else:
            lvl = LEVELS[min(2, i * 3 // n)]
        mapping[v] = lvl
    return mapping


def make_labels(series, mapping=None, q_low=0.5, q_high=0.8):
    """Turn any target column into Low/Medium/High labels."""
    if is_continuous(series):
        t1, t2 = series.quantile(q_low), series.quantile(q_high)
        out = np.select([series >= t2, series >= t1], ["High", "Medium"], default="Low")
        out = pd.Series(out, index=series.index, dtype=object)
        out[series.isna()] = np.nan
        return out, {"low_to_medium": float(t1), "medium_to_high": float(t2)}
    mapping = mapping or default_mapping(series)
    return series.map(mapping), mapping


def select_features(df, target, max_cat=30):
    feats = []
    for c in df.columns:
        if c == target:
            continue
        s = df[c]
        if s.isna().mean() > 0.6 or s.nunique(dropna=True) <= 1:
            continue
        if pd.api.types.is_numeric_dtype(s):
            feats.append(c)
        elif s.nunique() <= max_cat and s.nunique() < len(s) * 0.5:
            feats.append(c)
    return feats


def _preprocessor(X):
    num = [c for c in X.columns if pd.api.types.is_numeric_dtype(X[c])]
    cat = [c for c in X.columns if c not in num]
    parts = []
    if num:
        parts.append(("num", Pipeline([("imp", SimpleImputer(strategy="median")),
                                       ("sc", StandardScaler())]), num))
    if cat:
        parts.append(("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                                       ("oh", OneHotEncoder(handle_unknown="ignore",
                                                            sparse_output=False))]), cat))
    return ColumnTransformer(parts)


def _models():
    return {
        "Logistic Regression": LogisticRegression(max_iter=1000, class_weight="balanced"),
        "Decision Tree": DecisionTreeClassifier(max_depth=8, class_weight="balanced", random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=200, class_weight="balanced",
                                                random_state=42, n_jobs=-1),
        "Gradient Boosting": GradientBoostingClassifier(random_state=42),
        "SVM": SVC(probability=True, class_weight="balanced", random_state=42),
    }


def train_and_compare(X, y, test_size=0.2, seed=42):
    ok = y.notna()
    X, y = X[ok].reset_index(drop=True), y[ok].reset_index(drop=True)
    yi = y.map({l: i for i, l in enumerate(LEVELS)}).astype(int)
    counts = yi.value_counts()
    if len(counts) < 2:
        raise ValueError("Target produced only one risk class. Adjust the mapping or thresholds.")
    strat = yi if counts.min() >= 2 else None
    Xtr, Xte, ytr, yte = train_test_split(X, yi, test_size=test_size, random_state=seed, stratify=strat)
    present = sorted(yi.unique().tolist())
    rows, fitted, cms = [], {}, {}
    for name, clf in _models().items():
        pipe = Pipeline([("prep", _preprocessor(X)), ("clf", clf)])
        pipe.fit(Xtr, ytr)
        pred = pipe.predict(Xte)
        p, r, f, _ = precision_recall_fscore_support(yte, pred, average="macro", zero_division=0)
        per = precision_recall_fscore_support(yte, pred, labels=present, average=None, zero_division=0)[1]
        high_recall = per[present.index(2)] if 2 in present else np.nan
        rows.append({"Model": name, "Accuracy": accuracy_score(yte, pred), "Precision": p,
                     "Recall": r, "F1": f, "High-risk recall": high_recall})
        fitted[name] = pipe
        cms[name] = confusion_matrix(yte, pred, labels=present)
    res = pd.DataFrame(rows).sort_values(["F1", "High-risk recall"], ascending=False).reset_index(drop=True)
    return {"results": res, "models": fitted, "best": res.iloc[0]["Model"], "cms": cms,
            "classes": [LEVELS[i] for i in present], "label_counts": y.value_counts().to_dict()}


def feature_importance(pipe):
    names = [n.split("__", 1)[-1] for n in pipe.named_steps["prep"].get_feature_names_out()]
    clf = pipe.named_steps["clf"]
    if hasattr(clf, "feature_importances_"):
        imp = clf.feature_importances_
    elif hasattr(clf, "coef_"):
        imp = np.abs(clf.coef_).mean(axis=0)
    else:
        return None
    return pd.Series(imp, index=names).sort_values(ascending=False)


def default_inputs(df, features):
    d = {}
    for c in features:
        s = df[c]
        if pd.api.types.is_numeric_dtype(s):
            d[c] = {"type": "num", "default": float(s.median()), "min": float(s.min()), "max": float(s.max())}
        else:
            d[c] = {"type": "cat", "options": sorted(s.dropna().astype(str).unique().tolist()),
                    "default": str(s.mode().iloc[0])}
    return d


def predict_levels(pipe, frame):
    """Return (level, probability dict) for each row of `frame`."""
    proba = pipe.predict_proba(frame)
    classes = pipe.named_steps["clf"].classes_
    out = []
    for row in proba:
        d = {l: 0.0 for l in LEVELS}
        for c, p in zip(classes, row):
            d[LEVELS[int(c)]] = float(p)
        out.append((max(d, key=d.get), d))
    return out


def demo_dataset(n=1500, seed=0):
    """Synthetic data purely for demonstrating the app. Not real observations."""
    rng = np.random.default_rng(seed)
    rain = rng.gamma(2, 40, n)
    temp = rng.normal(28, 5, n)
    hum = np.clip(rng.normal(70, 15, n), 20, 100)
    wl = np.clip(rng.normal(3, 1.2, n), 0, None)
    soil = rng.uniform(5, 60, n)
    score = 0.012 * rain + 0.5 * wl + 0.02 * soil + 0.01 * hum + rng.normal(0, 0.3, n)
    lab = np.select([score >= np.quantile(score, 0.8), score >= np.quantile(score, 0.5)],
                    ["High", "Medium"], "Low")
    return pd.DataFrame({"rainfall_mm": rain, "temperature_c": temp, "humidity_pct": hum,
                         "water_level_m": wl, "soil_moisture_pct": soil, "flood_risk": lab})
