import argparse
import json
import math
import re
import shutil
import warnings
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.manifold import TSNE

warnings.filterwarnings("ignore", category=FutureWarning)

FIELD_ALIASES = {
    "id": ("id", "paper_id", "pid"),
    "title": ("t", "title", "paper_title"),
    "year": ("y", "year", "pub_year"),
    "venue": ("v", "venue", "journal", "conference"),
    "citations": ("c", "citations", "citation", "num_citations"),
    "abstract": ("abs", "abstract", "summary"),
    "concepts": ("con", "concepts", "keywords", "tags", "topics")
}

PROBLEM_DEFINITIONS = {
    "detection": [
        r"\b(object|instance|face|pedestrian|vehicle|anomaly|skeleton)\s+detection\b",
        r"\bdetectors?\b",
        r"\byolo\b"
    ],
    "segmentation": [
        r"\b(semantic|instance|panoptic|video|medical|image)\s+segmentation\b",
        r"\bscene\s+parsing\b",
        r"\bsegment\b"
    ],
    "tracking": [
        r"\b(object|visual|video|multi-object|pose)\s+tracking\b",
        r"\bmot\b",
        r"\btrackers?\b"
    ],
    "recognition": [
        r"\b(image|action|face|gesture|scene|pattern)\s+recognition\b",
        r"\b(image|text|video)\s+classification\b",
        r"\bre-?identification\b",
        r"\bre-?id\b"
    ],
    "generation": [
        r"\b(image|video|text-to-image|content|scene|avatar)\s+generation\b",
        r"\b(image|view)\s+synthesis\b",
        r"\bgenerative\s+models?\b",
        r"\bstyle\s+transfer\b"
    ],
    "restoration": [
        r"\b(image|video)\s+restoration\b",
        r"\bsuper-?resolution\b",
        r"\bdenoising\b",
        r"\bdeblurring\b",
        r"\binpainting\b",
        r"\bderaining\b",
        r"\bdehazing\b"
    ],
    "3d_vision": [
        r"\b3d\s+reconstruction\b",
        r"\bdepth\s+estimation\b",
        r"\bpoint\s+clouds?\b",
        r"\bslam\b",
        r"\bnerf\b",
        r"\bneural\s+radiance\s+fields?\b",
        r"\b3d\s+generation\b"
    ]
}

METHOD_DEFINITIONS = {
    "cnn": [
        r"\bcnn\b", r"\bconvnets?\b", r"\bconvolutional\s+neural\s+networks?\b",
        r"\bresnet\b", r"\befficientnet\b", r"\bvgg\b", r"\bdensenet\b", r"\bmobilenet\b"
    ],
    "transformer": [
        r"\btransformers?\b", r"\bvision\s+transformers?\b", r"\bself-attention\b",
        r"\bswin\b", r"\bdetr\b", r"\bbert\b", r"\bcross-attention\b"
    ],
    "vit": [
        r"\bvit\b", r"\bvision\s+transformer\b", r"\bmae\b", r"\bmasked\s+autoencoders?\b"
    ],
    "diffusion": [
        r"\bdiffusion\s+models?\b", r"\bddpm\b", r"\bldm\b", r"\bstable\s+diffusion\b",
        r"\bscore-based\s+generative\b", r"\bdiffusion\s+probabilistic\b"
    ],
    "gan": [
        r"\bgan\b", r"\bgenerative\s+adversarial\b", r"\bstylegan\b", r"\bcyclegan\b", r"\bpix2pix\b"
    ],
    "mlp": [
        r"\bmlp\b", r"\bmultilayer\s+perceptrons?\b", r"\bmlp-mixer\b"
    ],
    "gnn": [
        r"\bgnn\b", r"\bgraph\s+neural\b", r"\bgcn\b", r"\bgraph\s+convolution\b"
    ],
    "nerf": [
        r"\bnerf\b", r"\bradiance\s+fields?\b", r"\bgaussian\s+splatting\b"
    ],
    "contrastive": [
        r"\bcontrastive\s+learning\b", r"\bclip\b", r"\bsimclr\b", r"\bmoco\b"
    ],
    "rnn": [
        r"\brnn\b", r"\blstm\b", r"\bgru\b", r"\brecurrent\b"
    ]
}

METHOD_START_YEAR = {
    "transformer": 2017,
    "vit": 2020,
    "diffusion": 2019,
    "nerf": 2020,
    "contrastive": 2019
}

SEMANTIC_TOPIC_DEFINITIONS = {
    "Foundation models": [
        r"\bfoundation\s+models?\b",
        r"\blarge\s+(vision|multimodal)\s+models?\b",
        r"\bvision\s+foundation\b"
    ],
    "Multimodal reasoning": [
        r"\bvision[-\s]*language\b",
        r"\bmultimodal\b",
        r"\bimage[-\s]*text\b",
        r"\bvideo[-\s]*text\b",
        r"\bllava\b"
    ],
    "Autonomous driving": [
        r"\bautonomous\s+driving\b",
        r"\bself-driving\b",
        r"\bbev\b",
        r"\blane\s+(detection|segmentation)\b"
    ],
    "Medical imaging": [
        r"\bmedical\s+imaging\b",
        r"\bradiology\b",
        r"\bct\b",
        r"\bmri\b",
        r"\bhistopathology\b"
    ],
    "Remote sensing": [
        r"\bremote\s+sensing\b",
        r"\bsatellite\b",
        r"\bsar\b",
        r"\baerial\s+image\b"
    ],
    "Human pose": [
        r"\bpose\s+estimation\b",
        r"\bskeleton\b",
        r"\bhuman\s+mesh\b",
        r"\bsmpl\b"
    ],
    "Video understanding": [
        r"\bvideo\s+(recognition|understanding|captioning)\b",
        r"\baction\s+recognition\b",
        r"\btemporal\s+segment\b"
    ],
    "Robot learning": [
        r"\brobot(ic)?\b",
        r"\bmanipulation\b",
        r"\bembodied\s+ai\b"
    ],
    "Generative 3D": [
        r"\bnerf\b",
        r"\bradiance\s+fields?\b",
        r"\b3d\s+gaussian\b",
        r"\bsplatting\b"
    ],
    "Scientific imaging": [
        r"\bmicroscopy\b",
        r"\bfluorescence\b",
        r"\boptical\s+coherence\b"
    ],
    "Responsible AI": [
        r"\bfair(ness)?\b",
        r"\bbias\b",
        r"\bmodel\s+card\b"
    ]
}

TOPIC_PRIORITY = {
    "Foundation models": 5,
    "Multimodal reasoning": 5,
    "Generative 3D": 4,
    "Robot learning": 4,
    "Autonomous driving": 4,
    "Video understanding": 4,
    "Human pose": 3,
    "Medical imaging": 3,
    "Responsible AI": 3,
    "Remote sensing": 2,
    "Scientific imaging": 2
}

CANONICAL_TOPIC_DEFINITIONS = {
    "Vision Foundation & Multimodal": [
        r"\bfoundation\s+models?\b",
        r"\blarge\s+(vision|multimodal|language)\s+models?\b",
        r"\bvision[-\s]*language\b",
        r"\bvlm\b",
        r"\bllm\b",
        r"\bclip\b",
        r"\bllava\b",
        r"\bgpt\b",
        r"\bgenerative\s+ai\b"
    ],
    "Generative Media & Diffusion": [
        r"\bdiffusion\s+models?\b",
        r"\btext-?to-?(image|video)\b",
        r"\bgenerative\s+(image|video|media)\b",
        r"\bimage\s+synthesis\b",
        r"\bscore-?based\b",
        r"\bgaussian\s+splatting\b"
    ],
    "Embodied AI & Robotics": [
        r"\brobot(ic)?\b",
        r"\bembodied\s+ai\b",
        r"\bmanipulation\b",
        r"\bgrasp(ing)?\b",
        r"\bmobile\s+manipulation\b",
        r"\bpolicy\s+learning\b"
    ],
    "Autonomous Driving & BEV": [
        r"\bautonomous\s+driving\b",
        r"\bself-?driving\b",
        r"\bbev\b",
        r"\bbird['’`-]?s\s+eye\s+view\b",
        r"\blane\s+(detection|segmentation)\b",
        r"\blidar\b",
        r"\boccupancy\s+network\b"
    ],
    "Medical Imaging & Diagnostics": [
        r"\bmedical\s+(imaging|diagnosis|image)\b",
        r"\bradiology\b",
        r"\bct\b",
        r"\bmri\b",
        r"\bhistopathology\b",
        r"\bultrasound\b",
        r"\bhealthcare\b",
        r"\boncology\b",
        r"\bdisease\s+detection\b",
        r"\bclinical\b"
    ],
    "Remote Sensing & Earth Observation": [
        r"\bremote\s+sensing\b",
        r"\bsatellite\b",
        r"\bsar\b",
        r"\baerial\s+image\b",
        r"\bearth\s+observation\b",
        r"\bagriculture\b",
        r"\bcrop\s+monitoring\b"
    ],
    "3D Vision & Reconstruction": [
        r"\b3d\s+(reconstruction|generation|human)\b",
        r"\bdepth\s+estimation\b",
        r"\bpoint\s+clouds?\b",
        r"\bnerf\b",
        r"\bradiance\s+fields?\b",
        r"\bgaussian\s+splatting\b",
        r"\bmetaverse\b",
        r"\bvirtual\s+reality\b"
    ],
    "Low-level Vision & Restoration": [
        r"\bsuper-?resolution\b",
        r"\bdenois(ing|e)\b",
        r"\bdeblurr?ing\b",
        r"\bderain(ing)?\b",
        r"\bdehazing\b",
        r"\bimage\s+restoration\b"
    ],
    "Video Intelligence & Tracking": [
        r"\bvideo\s+(understanding|recognition|captioning)\b",
        r"\baction\s+recognition\b",
        r"\btemporal\s+(segment|localization)\b",
        r"\btracking\b",
        r"\bmot\b"
    ],
    "Human-centric Understanding": [
        r"\bpose\s+estimation\b",
        r"\bhuman\s+mesh\b",
        r"\bsmpl\b",
        r"\bre-?identification\b",
        r"\bgait\b",
        r"\bgesture\b"
    ],
    "Responsible & Efficient AI": [
        r"\bfair(ness)?\b",
        r"\bbias\b",
        r"\bprivacy\b",
        r"\bcompression\b",
        r"\bdistillation\b",
        r"\bgreen\s+ai\b"
    ],
    "Scientific & Industrial Imaging": [
        r"\bmicroscopy\b",
        r"\bspectroscopy\b",
        r"\bmanufacturing\b",
        r"\bdefect\s+detection\b",
        r"\binspection\b",
        r"\bnon-?destructive\b"
    ],
    "General Perception & Scene Understanding": [
        r"\bobject\s+detection\b",
        r"\b(image|semantic|panoptic|instance)\s+segmentation\b",
        r"\bscene\s+parsing\b",
        r"\bimage\s+classification\b",
        r"\bretrieval\b"
    ]
}

CANONICAL_TOPIC_PRIORITY = {
    "Vision Foundation & Multimodal": 9,
    "Generative Media & Diffusion": 8,
    "Embodied AI & Robotics": 7,
    "Autonomous Driving & BEV": 7,
    "Medical Imaging & Diagnostics": 7,
    "Remote Sensing & Earth Observation": 6,
    "3D Vision & Reconstruction": 6,
    "Video Intelligence & Tracking": 5,
    "Human-centric Understanding": 5,
    "Low-level Vision & Restoration": 4,
    "Responsible & Efficient AI": 4,
    "Scientific & Industrial Imaging": 4,
    "General Perception & Scene Understanding": 1
}

DEFAULT_PRIMARY_SEMANTIC = "Uncategorized Research"

GENERIC_CONCEPTS = {
    "computer science",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "convolutional neural network",
    "benchmark",
    "survey",
    "dataset",
    "generalization"
}

GENERIC_CONCEPT_TOKENS = {
    "computer", "science", "artificial", "intelligence", "learning",
    "network", "networks", "model", "models", "paper", "study",
    "generalization", "method", "analysis", "system", "approach",
    "algorithm", "benchmark", "dataset", "data"
}

LOW_VALUE_TERMS = {
    "remote sensing",
    "landslide",
    "earthquake",
    "soil stability",
    "geology",
    "weather forecast",
    "agriculture",
    "crop monitoring",
    "meta analysis",
    "categorization",
    "open research",
    "key",
    "field",
    "modal",
    "generative grammar",
    "psychology",
    "mathematics",
    "medicine",
    "environmental science",
    "engineering",
    "physics",
    "biology",
    "business",
    "materials science",
    "geography",
    "computer security"
}

CONCEPT_BLACKLIST = {
    "computer vision",
    "artificial intelligence",
    "pattern recognition",
    "responsible ai"
}

LATEX_INLINE_PATTERN = re.compile(r"\$[^$]+\$")
LATEX_ENV_PATTERN = re.compile(r"\\begin\{[^}]+\}.*?\\end\{[^}]+\}", re.DOTALL)
LATEX_CMD_PATTERN = re.compile(
    r"\\(?:cite|ref|eqref|mathbf|mathrm|textit|emph)\{[^}]*\}")
GENERIC_CMD_PATTERN = re.compile(r"\\[a-zA-Z]+")
NON_ALPHA_PATTERN = re.compile(r"[^a-z0-9\+\-\s]")
PAREN_STRIP_PATTERN = re.compile(r"\([^)]*\)")

COMMON_STOPWORDS = {
    'the', 'and', 'for', 'with', 'that', 'have', 'this', 'from', 'been', 'into',
    'using', 'their', 'these', 'those', 'between', 'within', 'without', 'through',
    'towards', 'toward', 'upon', 'while', 'where', 'when', 'which', 'such', 'than',
    'also', 'however', 'therefore', 'overall', 'well', 'both', 'each', 'most',
    'more', 'many', 'much', 'can', 'could', 'would', 'should', 'may', 'might'
}

ACADEMIC_STOPWORDS = {
    'paper', 'method', 'proposed', 'approach', 'results', 'performance',
    'state-of-the-art', 'sota', 'using', 'based', 'model', 'network', 'algorithm',
    'framework', 'novel', 'data', 'dataset', 'learning', 'deep', 'visual',
    'computer', 'vision', 'image', 'images', 'task', 'tasks', 'efficient',
    'robust', 'accurate', 'analysis', 'study', 'via', 'neural', 'networks',
    'experiments', 'experimental', 'demonstrate', 'show', 'outperforms', 'existing',
    'methods', 'problem', 'address', 'propose', 'presents', 'introduction',
    'conclusion', 'abstract', 'training', 'trained', 'evaluation', 'benchmark',
    'application', 'applications'
}

STOPWORDS = COMMON_STOPWORDS | ACADEMIC_STOPWORDS
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DATA_DIR = PROJECT_ROOT / "web" / "data"


class CategoryMatcher:
    def __init__(self, definitions):
        self.patterns = {}
        for category, regex_list in definitions.items():
            combined = "|".join(f"(?:{pattern})" for pattern in regex_list)
            self.patterns[category] = re.compile(combined, re.IGNORECASE)

    def find_matches(self, text):
        if not text:
            return set()
        return {category for category, pattern in self.patterns.items() if pattern.search(text)}


PROBLEM_MATCHER = CategoryMatcher(PROBLEM_DEFINITIONS)
METHOD_MATCHER = CategoryMatcher(METHOD_DEFINITIONS)
TOPIC_MATCHER = CategoryMatcher(SEMANTIC_TOPIC_DEFINITIONS)
PRIMARY_TOPIC_MATCHER = CategoryMatcher(CANONICAL_TOPIC_DEFINITIONS)


def normalize_phrase(text):
    if not isinstance(text, str):
        return ""
    stripped = PAREN_STRIP_PATTERN.sub(" ", text)
    lowered = stripped.lower()
    lowered = re.sub(r"[\-_/:+]+", " ", lowered)
    lowered = NON_ALPHA_PATTERN.sub(' ', lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def strip_latex_chunks(text):
    if not isinstance(text, str):
        return ""
    cleaned = LATEX_ENV_PATTERN.sub(" ", text)
    cleaned = LATEX_INLINE_PATTERN.sub(" ", cleaned)
    cleaned = LATEX_CMD_PATTERN.sub(" ", cleaned)
    cleaned = GENERIC_CMD_PATTERN.sub(" ", cleaned)
    cleaned = cleaned.replace('{', ' ').replace('}', ' ')
    return cleaned


def clean_academic_text(text):
    cleaned = strip_latex_chunks(text)
    lowered = cleaned.lower()
    lowered = NON_ALPHA_PATTERN.sub(' ', lowered)
    tokens = [tok for tok in lowered.split()
              if tok and tok not in STOPWORDS and len(tok) > 2]
    return " ".join(tokens)


def prettify_concept(term):
    if term is None:
        return ""
    text = PAREN_STRIP_PATTERN.sub(" ", str(term))
    text = text.replace("_", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return ""
    tokens = text.split()
    formatted = []
    for token in tokens:
        if token.isupper() or any(ch.isdigit() for ch in token):
            formatted.append(token.upper())
        else:
            formatted.append(token.capitalize())
    return " ".join(formatted)


def is_meaningful_concept(term):
    if term is None:
        return False
    raw_text = str(term)
    if "(" in raw_text or ")" in raw_text:
        return False
    normalized = normalize_phrase(raw_text)
    if not normalized:
        return False
    if normalized in CONCEPT_BLACKLIST:
        return False
    if normalized in GENERIC_CONCEPTS:
        return False
    if normalized in LOW_VALUE_TERMS:
        return False
    tokens = normalized.split()
    if not tokens:
        return False
    if len(tokens) == 1 and (tokens[0] in GENERIC_CONCEPT_TOKENS or len(tokens[0]) <= 2):
        return False
    if all(tok in GENERIC_CONCEPT_TOKENS for tok in tokens):
        return False
    return True


def derive_semantic_tags(paper, tfidf_row, feature_names, limit, cluster_label=None):
    title = pick_field(paper, "title", "") or ""
    abstract = pick_field(paper, "abstract", "") or ""
    topic_hits = sorted(TOPIC_MATCHER.find_matches(f"{title} {abstract}"))
    topic_hits.sort(key=lambda name: TOPIC_PRIORITY.get(name, 1), reverse=True)
    topic_labels = [
        prettify_concept(label)
        for label in topic_hits
        if is_meaningful_concept(label)
    ]

    raw_concepts = ensure_list(pick_field(paper, "concepts", []))
    curated = [prettify_concept(concept)
               for concept in raw_concepts if is_meaningful_concept(concept)]

    tfidf_terms = []
    if tfidf_row is not None and feature_names is not None:
        tfidf_terms = [
            prettify_concept(term)
            for term in top_terms_for_row(tfidf_row, feature_names, max(limit * 2, 6))
            if is_meaningful_concept(term)
        ]

    enriched_context = " ".join(filter(
        None, [title, abstract, " ".join(raw_concepts), " ".join(tfidf_terms[:6])]))
    fallback_primary = cluster_label if cluster_label else topic_labels[0] if topic_labels else None
    primary_label = select_canonical_semantic(
        enriched_context, fallback_primary)
    
    # If still default, try to force a cluster label or top keyword
    if primary_label == DEFAULT_PRIMARY_SEMANTIC:
        if cluster_label:
            primary_label = cluster_label
        elif topic_labels:
            primary_label = topic_labels[0]
        elif tfidf_terms:
            primary_label = tfidf_terms[0]
            
    secondary_bucket = []
    if cluster_label and cluster_label != primary_label:
        secondary_bucket.append(cluster_label)

    buckets = ([primary_label], topic_labels,
               curated, secondary_bucket, tfidf_terms)
    seen = set()
    output = []
    target = max(limit, 3)
    for bucket in buckets:
        for term in bucket:
            normalized = normalize_phrase(term)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            output.append(term)
            if len(output) >= target:
                break
        if len(output) >= target:
            break

    if not output:
        output.append(DEFAULT_PRIMARY_SEMANTIC)
    return output[:target]


def pick_field(record, alias_key, default=None):
    for key in FIELD_ALIASES.get(alias_key, (alias_key,)):
        if key in record and record[key] not in (None, ""):
            return record[key]
    return default


def normalize_year(value):
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except ValueError:
        return None


def normalize_citations(value):
    if value is None:
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v]
    if isinstance(value, str):
        parts = re.split(r"[;,/]", value)
        return [p.strip() for p in parts if p.strip()]
    return []


def build_text_blob(paper):
    parts = []
    for alias in ("title", "abstract"):
        value = pick_field(paper, alias, "")
        if isinstance(value, str):
            parts.append(value)
    concept_list = ensure_list(pick_field(paper, "concepts", []))
    if concept_list:
        parts.append(" ".join(concept_list))
    combined = " ".join(parts)
    return clean_academic_text(combined)


def select_canonical_semantic(text, fallback=None):
    if not isinstance(text, str):
        text = ""
    matches = PRIMARY_TOPIC_MATCHER.find_matches(text)
    if matches:
        ordered = sorted(
            matches,
            key=lambda name: (
                CANONICAL_TOPIC_PRIORITY.get(name, 1), len(name)),
            reverse=True
        )
        return ordered[0]
    if fallback:
        formatted = prettify_concept(fallback)
        if formatted:
            return formatted
    return DEFAULT_PRIMARY_SEMANTIC


def keywords_from_vector(vector, feature_names, limit):
    if vector is None or not len(feature_names):
        return []
    if isinstance(vector, np.matrix):
        vector = np.asarray(vector).ravel()
    order = np.argsort(vector)[::-1]
    keywords = []
    seen = set()
    for idx in order:
        if idx < 0 or idx >= len(feature_names):
            continue
        term = prettify_concept(feature_names[idx])
        normalized = normalize_phrase(term)
        if not normalized or normalized in seen:
            continue
        if not is_meaningful_concept(term):
            continue
        keywords.append(term)
        seen.add(normalized)
        if len(keywords) >= limit:
            break
    return keywords


def build_semantic_clusters(tfidf_matrix, feature_names, desired_clusters):
    if tfidf_matrix is None or tfidf_matrix.shape[0] < 40 or tfidf_matrix.shape[1] < 8:
        return None, {}

    sample_count = tfidf_matrix.shape[0]
    feature_count = tfidf_matrix.shape[1]
    cluster_count = min(desired_clusters, max(4, sample_count // 400 + 6))
    cluster_count = min(cluster_count, feature_count)
    if cluster_count < 2:
        return None, {}

    model = MiniBatchKMeans(
        n_clusters=cluster_count,
        random_state=42,
        batch_size=min(2048, sample_count),
        n_init="auto"
    )

    try:
        labels = model.fit_predict(tfidf_matrix)
    except ValueError:
        return None, {}

    cluster_titles = {}
    for cluster_id in range(cluster_count):
        members = np.where(labels == cluster_id)[0]
        if members.size == 0:
            continue
        mean_vector = tfidf_matrix[members].mean(axis=0)
        keywords = keywords_from_vector(mean_vector, feature_names, limit=6)
        context = " ".join(keywords[:6])
        canonical = select_canonical_semantic(context)
        if canonical:
            label = canonical
        elif keywords:
            label = " / ".join(keywords[:3])
        else:
            label = f"Emerging Cluster {cluster_id + 1}"
        cluster_titles[cluster_id] = label

    return labels, cluster_titles


def select_top_papers(papers, per_year, overall_cap):
    grouped = defaultdict(list)
    for paper in papers:
        year = normalize_year(pick_field(paper, "year"))
        if year is None:
            continue
        citations = normalize_citations(pick_field(paper, "citations", 0))
        grouped[year].append((citations, paper))

    yearly = {}
    for year, items in grouped.items():
        items.sort(key=lambda pair: pair[0], reverse=True)
        yearly[year] = deque(paper for _, paper in items[:per_year])

    ordered_years = sorted(yearly.keys(), reverse=True)
    if not overall_cap:
        merged = []
        for year in ordered_years:
            merged.extend(list(yearly[year]))
        return merged

    total_candidates = sum(len(bucket) for bucket in yearly.values())
    if total_candidates <= overall_cap:
        merged = []
        for year in ordered_years:
            merged.extend(list(yearly[year]))
        return merged

    selected = []
    while len(selected) < overall_cap and ordered_years:
        progressed = False
        for year in ordered_years:
            bucket = yearly.get(year)
            if bucket:
                selected.append(bucket.popleft())
                progressed = True
                if len(selected) == overall_cap:
                    break
        if not progressed:
            break

    return selected


def compute_embeddings(papers, max_features):
    documents = [build_text_blob(p) for p in papers]
    if not any(doc.strip() for doc in documents):
        zeros = np.zeros((len(papers), 2))
        return zeros, None, []

    min_df = 1 if len(documents) < 50 else 2
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=(1, 2),
        max_df=0.65,
        min_df=min_df
    )
    try:
        tfidf = vectorizer.fit_transform(documents)
    except ValueError:
        zeros = np.zeros((len(papers), 2))
        return zeros, None, []

    if tfidf.shape[0] < 2 or tfidf.shape[1] < 2:
        coords = np.zeros((tfidf.shape[0], 2))
        if tfidf.shape[0]:
            coords[:, 0] = tfidf.sum(axis=1).A1
        return coords, tfidf, vectorizer.get_feature_names_out()

    svd_components = min(50, tfidf.shape[1], tfidf.shape[0])
    if svd_components < 2:
        svd_components = 2
    reducer = TruncatedSVD(n_components=svd_components, random_state=42)
    svd_coords = reducer.fit_transform(tfidf)

    coords = None
    sample_count = len(papers)
    if sample_count >= 5 and svd_coords.shape[1] >= 2:
        perplexity = min(40, max(5, sample_count // 3))
        if perplexity >= sample_count:
            perplexity = max(2, sample_count - 1)
        if perplexity >= 2 and perplexity < sample_count:
            try:
                tsne_kwargs = {
                    "n_components": 2,
                    "perplexity": perplexity,
                    "init": 'pca',
                    "learning_rate": 'auto',
                    "metric": 'cosine',
                    "random_state": 42
                }
                # scikit-learn 1.5+ renames n_iter -> max_iter; keep backward compatibility
                if "max_iter" in TSNE.__init__.__code__.co_varnames:
                    tsne_kwargs["max_iter"] = 1000
                else:
                    tsne_kwargs["n_iter"] = 1000
                tsne = TSNE(**tsne_kwargs)
                coords = tsne.fit_transform(svd_coords)
            except ValueError:
                coords = None

    if coords is None:
        base = svd_coords[:,
                          :2] if svd_coords.shape[1] >= 2 else svd_coords[:, [0]]
        if base.shape[1] < 2:
            padded = np.zeros((base.shape[0], 2))
            padded[:, 0] = base[:, 0]
            coords = padded
        else:
            coords = base

    return coords, tfidf, vectorizer.get_feature_names_out()


def top_terms_for_row(row, feature_names, limit):
    if row is None or row.nnz == 0 or len(feature_names) == 0:
        return []
    pairs = sorted(zip(row.data, row.indices), reverse=True)[:limit]
    return [feature_names[idx] for _, idx in pairs]


def build_landscape(papers, max_features, top_terms, semantic_clusters):
    coords, tfidf, feature_names = compute_embeddings(papers, max_features)
    cluster_assignments = None
    cluster_titles = {}
    if semantic_clusters and tfidf is not None and feature_names is not None:
        cluster_assignments, cluster_titles = build_semantic_clusters(
            tfidf, feature_names, semantic_clusters)
    records = []
    for idx, paper in enumerate(papers):
        year = normalize_year(pick_field(paper, "year"))
        record = {
            "id": pick_field(paper, "id", f"paper-{idx}"),
            "title": pick_field(paper, "title", "Untitled"),
            "year": year,
            "venue": pick_field(paper, "venue", ""),
            "citations": normalize_citations(pick_field(paper, "citations", 0)),
            "x": float(coords[idx][0]) if coords.size else 0.0,
            "y": float(coords[idx][1]) if coords.size else 0.0,
        }

        row = tfidf.getrow(idx) if tfidf is not None else None
        cluster_label = None
        if cluster_assignments is not None:
            cluster_idx = int(cluster_assignments[idx])
            cluster_label = cluster_titles.get(cluster_idx)
        concepts = derive_semantic_tags(
            paper, row, feature_names, top_terms, cluster_label=cluster_label)
        record["concepts"] = concepts
        record["semantic_primary"] = concepts[0] if concepts else None
        record["semantic_cluster"] = cluster_label
        records.append(record)

    return records


def compute_link_weight(paper):
    citations = normalize_citations(pick_field(paper, "citations", 0))
    return math.log(citations + 1) + 1


def build_sankey(papers, min_value, recent_years=10):
    """聚合 problem→method 年度流向，标题命中的论文给予更高权重。"""
    links_by_year = defaultdict(lambda: defaultdict(float))
    observed_years = set()

    print("开始提取桑基图流向数据...")

    for i, paper in enumerate(papers):
        year = normalize_year(pick_field(paper, "year"))
        if year is None:
            continue

        title = pick_field(paper, "title", "") or ""
        abstract = pick_field(paper, "abstract", "") or ""
        title_problems = PROBLEM_MATCHER.find_matches(title)
        abstract_problems = PROBLEM_MATCHER.find_matches(abstract)
        problems = title_problems | abstract_problems
        if not problems:
            continue

        title_methods = METHOD_MATCHER.find_matches(title)
        abstract_methods = METHOD_MATCHER.find_matches(abstract)
        methods = set()
        for meth in title_methods | abstract_methods:
            min_year = METHOD_START_YEAR.get(meth)
            if min_year and year < min_year:
                continue
            methods.add(meth)
        if not methods:
            continue

        base_weight = compute_link_weight(paper)
        if title_problems and title_methods:
            weight = base_weight * 2.0
        elif title_problems or title_methods:
            weight = base_weight
        else:
            weight = base_weight * 0.5

        combo_count = max(1, len(problems) * len(methods))
        distributed = weight / combo_count

        observed_years.add(year)
        for prob in problems:
            for meth in methods:
                links_by_year[year][(prob, meth)] += distributed

        if (i + 1) % 20000 == 0:
            print(f"  已处理 {i + 1} 篇...")

    if not observed_years:
        return []

    sorted_years = sorted(observed_years)
    if recent_years and len(sorted_years) > recent_years:
        cutoff = sorted_years[-recent_years]
    else:
        cutoff = sorted_years[0]

    final_payload = []
    for year in sorted_years:
        if year < cutoff:
            continue
        for (prob, meth), total_weight in links_by_year[year].items():
            if total_weight >= min_value:
                final_payload.append({
                    "year": year,
                    "source": prob,
                    "target": meth,
                    "value": round(total_weight, 2)
                })

    final_payload.sort(key=lambda x: (x["year"], -x["value"]))
    return final_payload


def save_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return path


def mirror_to_web_data(source_path):
    try:
        WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"[warn] 无法创建 web/data 目录: {exc}")
        return None
    source_path = Path(source_path)
    target_path = WEB_DATA_DIR / source_path.name
    try:
        shutil.copy2(source_path, target_path)
        return target_path
    except OSError as exc:
        print(f"[warn] 无法同步 {source_path.name} 至 web/data: {exc}")
        return None


def resolve_existing(path_str):
    path = Path(path_str)
    if path.exists():
        return path
    candidate = PROJECT_ROOT / path_str
    if candidate.exists():
        return candidate
    return path


def resolve_output(path_str):
    path = Path(path_str)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path_str


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Prepare advanced visualization data.")
    parser.add_argument("--input", default="data/cleaned_papers.json")
    parser.add_argument("--landscape-output",
                        default="data/landscape_data.json")
    parser.add_argument("--sankey-output", default="data/sankey_data.json")
    parser.add_argument("--top-per-year", type=int, default=300)
    parser.add_argument("--max-landscape", type=int, default=15000)
    parser.add_argument("--tfidf-features", type=int, default=1000)
    parser.add_argument("--top-terms", type=int, default=5)
    parser.add_argument("--min-link", type=float, default=2.0)
    parser.add_argument("--semantic-clusters", type=int, default=14)
    return parser.parse_args(argv)


def main(cli_args=None):
    if isinstance(cli_args, argparse.Namespace):
        args = cli_args
    else:
        args = parse_args(cli_args)
    input_path = resolve_existing(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"找不到输入文件: {input_path}")

    landscape_output_path = resolve_output(args.landscape_output)
    sankey_output_path = resolve_output(args.sankey_output)

    with input_path.open("r", encoding="utf-8") as f:
        papers = json.load(f)

    top_papers = select_top_papers(
        papers, args.top_per_year, args.max_landscape)
    landscape_payload = build_landscape(
        top_papers, args.tfidf_features, args.top_terms, args.semantic_clusters)
    sankey_payload = build_sankey(papers, args.min_link)

    landscape_path = save_json(landscape_output_path, landscape_payload)
    sankey_path = save_json(sankey_output_path, sankey_payload)
    mirror_to_web_data(landscape_path)
    mirror_to_web_data(sankey_path)

    print(f"Landscape records: {len(landscape_payload)}")
    print(f"Sankey links: {len(sankey_payload)}")


if __name__ == "__main__":
    main()
