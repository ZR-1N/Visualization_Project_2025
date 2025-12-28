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
    "Cnn": [r"\bcnn\b", r"\bconvnet\b", r"\bconvolutional\b", r"\bresnet\b", r"\befficientnet\b"],
    "Transformer": [r"\btransformer\b", r"\bself-attention\b", r"\bswin\b", r"\bdetr\b", r"\bvit\b"],
    "Diffusion": [r"\bdiffusion\b", r"\bddpm\b", r"\bldm\b", r"\bstable\s+diffusion\b"],
    "Gan": [r"\bgan\b", r"\badversarial\b", r"\bstylegan\b"],
    "Nerf": [r"\bnerf\b", r"\bradiance\s+field\b", r"\bgaussian\s+splatting\b"],
    "Gnn": [r"\bgnn\b", r"\bgraph\b", r"\bgcn\b"],
    "Mlp": [r"\bmlp\b", r"\bperceptron\b"],
    "Rnn": [r"\brnn\b", r"\blstm\b", r"\bgru\b"],
    "Contrastive": [r"\bcontrastive\b", r"\bclip\b", r"\bsimclr\b", r"\bmoco\b"],
    "Detection": [r"\bdetection\b", r"\byolo\b", r"\brcnn\b"],
    "Segmentation": [r"\bsegmentation\b", r"\bmask\b", r"\bsam\b"],
    "Generation": [r"\bgeneration\b", r"\bsynthesis\b"],
    "Multimodal": [r"\bmultimodal\b", r"\bvision-language\b", r"\bvqa\b", r"\bcaptioning\b"]
}

TOPIC_PRIORITY = {
    "Diffusion": 10,
    "Nerf": 9,
    "Transformer": 8,
    "Contrastive": 7,
    "Gan": 6,
    "Gnn": 5,
    "Multimodal": 5,
    "Detection": 4,
    "Segmentation": 4,
    "Cnn": 3,
    "Rnn": 2,
    "Mlp": 2,
    "Generation": 1
}

CANONICAL_TOPIC_DEFINITIONS = {
    "Vision Transformer (ViT)": [r"\bvit\b", r"\bvision\s+transformer\b", r"\bswin\b", r"\bdeit\b", r"\bbeit\b", r"\bpvt\b", r"\bcait\b", r"\bt2t\b"],
    "Diffusion Models": [r"\bdiffusion\b", r"\bddpm\b", r"\bldm\b", r"\bstable\s+diffusion\b", r"\bscore-based\b", r"\bdenoising\s+diffusion\b"],
    "NeRF & Neural Fields": [r"\bnerf\b", r"\bradiance\s+field\b", r"\bgaussian\s+splatting\b", r"\bview\s+synthesis\b", r"\bimplicit\s+function\b"],
    "Multimodal Alignment (CLIP)": [r"\bclip\b", r"\balign\b", r"\bcontrastive\s+language\b", r"\btext-image\s+matching\b", r"\bopen-vocabulary\b"],
    "Large Vision-Language Models": [r"\bllava\b", r"\bminigpt\b", r"\bblip\b", r"\bflamingo\b", r"\bvisual\s+gpt\b", r"\binstructblip\b", r"\bvlm\b"],
    "Object Detection": [r"\byolo\b", r"\byolov\d\b", r"\bcenternet\b", r"\befficientdet\b", r"\bssd\b", r"\bretina\b", r"\bfcos\b", r"\br-?cnn\b", r"\bfaster\s+rcnn\b", r"\bmask\s+rcnn\b", r"\bcascade\s+rcnn\b", r"\bregion\s+proposal\b", r"\bobject\s+detection\b", r"\bdetectors?\b"],
    "DETR & Object Queries": [r"\bdetr\b", r"\bdeformable\s+detr\b", r"\bobject\s+query\b", r"\bset\s+prediction\b"],
    "Segmentation (SAM & U-Net)": [r"\bunet\b", r"\bdeeplab\b", r"\bpspnet\b", r"\bmask2former\b", r"\bsegment\s+anything\b", r"\bsam\b", r"\bpanoptic\s+fpn\b"],
    "GANs & Image Synthesis": [r"\bgan\b", r"\bstylegan\b", r"\bcyclegan\b", r"\bpix2pix\b", r"\bimage-to-image\b", r"\bbiggan\b", r"\bstyle\s+transfer\b"],
    "CNN Backbones": [r"\bresnet\b", r"\befficientnet\b", r"\bvgg\b", r"\bdensenet\b", r"\bmobilenet\b", r"\bconvnext\b", r"\binception\b", r"\bxception\b"],
    "Self-Supervised Learning": [r"\bsimclr\b", r"\bmoco\b", r"\bbyol\b", r"\bdino\b", r"\bmae\b", r"\bmasked\s+image\s+modeling\b", r"\bcontrastive\b"],
    "3D Reconstruction & SLAM": [r"\bslam\b", r"\bstructure\s+from\s+motion\b", r"\bmulti-view\s+stereo\b", r"\bpoint\s+cloud\b", r"\bmesh\s+reconstruction\b"],
    "Video & Motion": [r"\bvideo\s+transformer\b", r"\btime\s+series\b", r"\boptical\s+flow\b", r"\baction\s+recognition\b", r"\btracking\b", r"\bmot\b"]
}

CANONICAL_TOPIC_PRIORITY = {
    "Diffusion Models": 10,
    "Large Vision-Language Models": 10,
    "NeRF & Neural Fields": 9,
    "Vision Transformer (ViT)": 9,
    "Multimodal Alignment (CLIP)": 8,
    "DETR & Object Queries": 8,
    "Self-Supervised Learning": 7,
    "GANs & Image Synthesis": 7,
    "Object Detection": 6,
    "Segmentation (SAM & U-Net)": 5,
    "3D Reconstruction & SLAM": 5,
    "CNN Backbones": 4,
    "Video & Motion": 3
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
    'noise',
    'algorithm',
    'challenge',
    'performance',
    'accuracy',
    'efficiency',
    'robustness',
    'framework',
    'architecture',
    'methodology',
    'implementation',
    'evaluation',
    'experiment',
    'ablation',
    'comparison',
    'overview',
    'survey',
    'review',
    'perspective',
    'future',
    'trend',
    'direction',
    'opportunity',
    'issue',
    'limitation',
    'gap',
    'advance',
    'progress',
    'state',
    'art',
    'practice',
    'application',
    'usage',
    'deployment',
    'system',
    'tool',
    'platform',
    'infrastructure',
    'hardware',
    'software',
    'device',
    'equipment',
    'setup',
    'configuration',
    'parameter',
    'setting',
    'feature',
    'representation',
    'embedding',
    'vector',
    'space',
    'manifold',
    'distribution',
    'function',
    'mapping',
    'transform',
    'operation',
    'layer',
    'unit',
    'block',
    'module',
    'component',
    'part',
    'element',
    'structure',
    'design',
    'scheme',
    'strategy',
    'policy',
    'protocol',
    'standard',
    'criterion',
    'measure',
    'metric',
    'score',
    'index',
    'value',
    'factor',
    'term',
    'concept',
    'idea',
    'notion',
    'principle',
    'theory',
    'hypothesis',
    'assumption',
    'conjecture',
    'proposition',
    'lemma',
    'theorem',
    'proof',
    'corollary',
    'definition',
    'example',
    'sample',
    'instance',
    'case',
    'scenario',
    'situation',
    'condition',
    'environment',
    'context',
    'setting',
    'background',
    'foreground',
    'object',
    'subject',
    'target',
    'source',
    'input',
    'output',
    'result',
    'outcome',
    'effect',
    'impact',
    'influence',
    'consequence',
    'implication',
    'significance',
    'importance',
    'relevance',
    'role',
    'contribution',
    'innovation',
    'novelty',
    'improvement',
    'enhancement',
    'extension',
    'modification',
    'adaptation',
    'adjustment',
    'correction',
    'revision',
    'update',
    'upgrade',
    'version',
    'variant',
    'alternative',
    'option',
    'choice',
    'selection',
    'decision',
    'action',
    'activity',
    'behavior',
    'process',
    'procedure',
    'routine',
    'task',
    'job',
    'mission',
    'goal',
    'objective',
    'aim',
    'purpose',
    'intention',
    'motivation',
    'reason',
    'cause',
    'explanation',
    'interpretation',
    'understanding',
    'insight',
    'knowledge',
    'information',
    'data',
    'evidence',
    'fact',
    'truth',
    'reality',
    'world',
    'universe',
    'nature',
    'life',
    'human',
    'person',
    'people',
    'user',
    'customer',
    'client',
    'consumer',
    'participant',
    'observer',
    'annotator',
    'worker',
    'agent',
    'actor',
    'player',
    'partner',
    'collaborator',
    'competitor',
    'adversary',
    'attacker',
    'defender',
    'learner',
    'teacher',
    'student',
    'expert',
    'novice',
    'beginner',
    'professional',
    'practitioner',
    'researcher',
    'scientist',
    'engineer',
    'developer',
    'designer',
    'architect',
    'manager',
    'leader',
    'director',
    'supervisor',
    'administrator',
    'organizer',
    'coordinator',
    'facilitator',
    'mediator',
    'arbitrator',
    'judge',
    'reviewer',
    'critic',
    'editor',
    'publisher',
    'author',
    'writer',
    'reader',
    'viewer',
    'listener',
    'speaker',
    'presenter',
    'audience',
    'crowd',
    'group',
    'team',
    'community',
    'society',
    'organization',
    'institution',
    'institute',
    'center',
    'laboratory',
    'department',
    'division',
    'section',
    'branch',
    'unit',
    'sector',
    'industry',
    'market',
    'economy',
    'business',
    'company',
    'corporation',
    'firm',
    'enterprise',
    'startup',
    'agency',
    'bureau',
    'office',
    'studio',
    'workshop',
    'factory',
    'plant',
    'facility',
    'station',
    'base',
    'camp',
    'site',
    'location',
    'place',
    'area',
    'region',
    'zone',
    'district',
    'territory',
    'country',
    'nation',
    'state',
    'city',
    'town',
    'village',
    'neighborhood',
    'street',
    'road',
    'path',
    'way',
    'route',
    'track',
    'lane',
    'channel',
    'corridor',
    'bridge',
    'tunnel',
    'gateway',
    'portal',
    'interface',
    'boundary',
    'border',
    'edge',
    'limit',
    'margin',
    'threshold',
    'level',
    'degree',
    'extent',
    'scope',
    'range',
    'scale',
    'magnitude',
    'dimension',
    'size',
    'volume',
    'capacity',
    'quantity',
    'amount',
    'number',
    'count',
    'frequency',
    'rate',
    'ratio',
    'percentage',
    'proportion',
    'fraction',
    'part',
    'share',
    'slice',
    'piece',
    'segment',
    'section',
    'fragment',
    'bit',
    'byte',
    'pixel',
    'voxel',
    'point',
    'line',
    'curve',
    'surface',
    'plane',
    'shape',
    'form',
    'pattern',
    'texture',
    'color',
    'tone',
    'shade',
    'hue',
    'brightness',
    'contrast',
    'saturation',
    'intensity',
    'luminance',
    'illuminance',
    'radiance',
    'reflectance',
    'transmittance',
    'absorbance',
    'scattering',
    'diffraction',
    'refraction',
    'interference',
    'polarization',
    'dispersion',
    'aberration',
    'distortion',
    'noise',
    'blur',
    'artifact',
    'occlusion',
    'shadow',
    'reflection',
    'specularity',
    'highlight',
    'glare',
    'transparency',
    'opacity',
    'visibility',
    'clarity',
    'sharpness',
    'focus',
    'resolution',
    'quality',
    'fidelity',
    'accuracy',
    'precision',
    'recall',
    'sensitivity',
    'specificity',
    'reliability',
    'validity',
    'consistency',
    'stability',
    'robustness',
    'efficiency',
    'effectiveness',
    'performance',
    'speed',
    'latency',
    'throughput',
    'bandwidth',
    'storage',
    'memory',
    'compute',
    'power',
    'energy',
    'cost',
    'price',
    'value',
    'benefit',
    'profit',
    'revenue',
    'income',
    'budget',
    'fund',
    'grant',
    'award',
    'prize',
    'honor',
    'recognition',
    'citation',
    'reference',
    'bibliography',
    'appendix',
    'supplement',
    'material',
    'code',
    'software',
    'data',
    'dataset',
    'model',
    'network',
    'system',
    'method',
    'algorithm',
    'technique',
    'approach',
    'framework',
    'pipeline',
    'workflow',
    'process',
    'procedure',
    'protocol',
    'standard',
    'policy',
    'strategy',
    'plan',
    'project',
    'program',
    'initiative',
    'campaign',
    'movement',
    'trend',
    'direction',
    'future',
    'vision',
    'mission',
    'goal',
    'objective',
    'aim',
    'target',
    'purpose'
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
    'more', 'many', 'much', 'can', 'could', 'would', 'should', 'may', 'might',
    'our', 'are', 'is', 'was', 'were', 'be', 'has', 'had', 'do', 'does', 'did', 'but',
    'not', 'only', 'all', 'any', 'some', 'other', 'its', 'it', 'time', 'domain', 'year',
    'years', 'two', 'new', 'one', 'use', 'used', 'using', 'research', 'review', 'machine',
    'prediction', 'predict', 'predicting',
    'feature', 'features', 'algorithm', 'algorithms', 'challenge', 'challenges',
    'noise', 'human', 'image', 'images', 'visual', 'vision', 'performance', 'method',
    'methods', 'proposed', 'approach', 'framework', 'system', 'study', 'analysis',
    'evaluation', 'experiment', 'experiments', 'experimental', 'result', 'results',
    'state-of-the-art', 'sota', 'dataset', 'datasets', 'benchmark', 'benchmarks',
    'novel', 'new', 'paper', 'work', 'research', 'review', 'survey', 'overview',
    'comprehensive', 'recent', 'advance', 'advances', 'trend', 'trends',
    'problem', 'problems', 'solution', 'solutions', 'application', 'applications',
    'technique', 'techniques', 'strategy', 'strategies', 'scheme', 'schemes',
    'mechanism', 'mechanisms', 'model', 'models', 'network', 'networks',
    'architecture', 'architectures', 'structure', 'structures', 'design', 'designs',
    'learning', 'training', 'testing', 'validation', 'inference',
    'deep', 'neural', 'machine', 'artificial', 'intelligence', 'computer',
    'task', 'tasks', 'capability', 'capabilities', 'quality', 'improvement',
    'accuracy', 'efficiency', 'robustness', 'generalization', 'complexity',
    'parameter', 'parameters', 'component', 'components', 'module', 'modules',
    'layer', 'layers', 'block', 'blocks', 'unit', 'units', 'input', 'output',
    'representation', 'representations', 'information', 'context', 'content',
    'detail', 'details', 'object', 'objects', 'scene', 'scenes', 'video', 'videos',
    'sample', 'samples', 'example', 'examples', 'instance', 'instances',
    'level', 'scale', 'resolution', 'size', 'speed', 'rate', 'time', 'real-time',
    'based', 'high', 'low', 'large', 'small', 'simple', 'complex',
    'fast', 'slow', 'strong', 'weak', 'good', 'bad', 'best', 'better',
    'multi', 'single', 'cross', 'joint', 'dual', 'hybrid', 'hierarchical',
    'global', 'local', 'spatial', 'temporal', 'spatiotemporal',
    'end', 'pipeline', 'stage', 'step', 'phase',
    'prior', 'post', 'pre', 're', 'non', 'semi', 'un', 'self',
    'supervised', 'unsupervised', 'weakly', 'fully', 'different'
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


YEARLY_DOMINANT_MAP = {
    2014: {"theme": "Two-Stage Detection (R-CNN)", "keywords": [r"r-cnn", r"rcnn", r"region-based", r"alexnet", r"vgg"]},
    2015: {"theme": "CNN Backbones (ResNet)", "keywords": [r"resnet", r"residual network", r"residual learning", r"batch normalization"]},
    2016: {"theme": "YOLO & Real-time Detection", "keywords": [r"yolo", r"ssd", r"real-time detection", r"faster r-cnn"]},
    2017: {"theme": "CNN Architectures (DenseNet)", "keywords": [r"densenet", r"dense connection", r"feature pyramid", r"fpn"]},
    2018: {"theme": "GANs & Image Synthesis", "keywords": [r"gan", r"generative adversarial", r"pix2pix", r"cyclegan"]},
    2019: {"theme": "Self-Supervised Learning", "keywords": [r"self-supervised", r"contrastive learning", r"moco", r"simclr", r"efficientnet"]},
    2020: {"theme": "Vision Transformer (ViT)", "keywords": [r"vit", r"vision transformer", r"dosovitskiy", r"detr", r"nerf"]},
    2021: {"theme": "Transformer Dominance (Swin)", "keywords": [r"transformer", r"swin", r"mae", r"clip"]},
    2022: {"theme": "Diffusion Models", "keywords": [r"diffusion model", r"stable diffusion", r"latent diffusion", r"ddpm", r"imagen"]},
    2023: {"theme": "Segmentation (SAM)", "keywords": [r"segment anything", r"sam", r"foundation model", r"controlnet", r"generative", r"diffusion"]},
    2024: {"theme": "Generative AI & LLMs", "keywords": [r"multimodal", r"large language", r"gpt", r"gemini", r"vlm", r"llava", r"sora", r"generative", r"diffusion", r"autonomous", r"robotics", r"yolo", r"real-time"]}
}


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


STRICT_CONCEPT_WHITELIST = {
    # Architectures & Models
    "cnn", "convnet", "resnet", "densenet", "efficientnet", "vgg", "mobilenet", "inception", "xception",
    "transformer", "vision transformer", "vit", "swin", "detr", "bert", "gpt", "clip", "t5", "mae",
    "gan", "stylegan", "cyclegan", "pix2pix", "biggan", "vae", "vq-vae",
    "diffusion", "ddpm", "ldm", "stable diffusion", "controlnet", "lora",
    "nerf", "gaussian splatting", "3d gaussian splatting", "instant ngp",
    "rnn", "lstm", "gru",
    "gnn", "gcn", "gat", "pointnet", "pointnet++", "unet", "fpn", "mask r-cnn", "faster r-cnn", "yolo", "ssd",
    "mlp", "mlp-mixer",

    # Core Mechanisms
    "attention", "self-attention", "cross-attention", "convolution",
    "contrastive learning", "self-supervised learning", "representation learning",
    "reinforcement learning", "transfer learning", "domain adaptation", "knowledge distillation",
    "few-shot learning", "zero-shot learning", "meta-learning", "active learning",
    "federated learning", "continual learning", "incremental learning",
    "generative", "adversarial", "discriminative", "probabilistic", "bayesian",

    # Tasks
    "object detection", "semantic segmentation", "instance segmentation", "panoptic segmentation",
    "image classification", "action recognition", "pose estimation", "depth estimation",
    "optical flow", "visual tracking", "object tracking", "mot",
    "image captioning", "vqa", "visual question answering", "text-to-image", "image-to-text",
    "super-resolution", "denoising", "inpainting", "deblurring", "image restoration",
    "3d reconstruction", "view synthesis", "slam", "structure from motion",
    "face recognition", "person re-identification", "pedestrian detection",
    "anomaly detection", "salient object detection", "edge detection",
    "medical imaging", "remote sensing", "autonomous driving", "robotics"
}


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

    # Strict whitelist check
    if normalized not in STRICT_CONCEPT_WHITELIST:
        # Allow if it matches any of the semantic topic definitions regexes
        # This is a bit expensive but ensures consistency
        found = False
        for pattern_list in SEMANTIC_TOPIC_DEFINITIONS.values():
            combined = "|".join(pattern_list)
            if re.search(combined, normalized, re.IGNORECASE):
                found = True
                break
        if not found:
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


CONCEPT_START_YEAR = {
    "Transformer": 2017,
    "Vision Transformer": 2020,
    "Vision Transformer (ViT)": 2020,
    "Diffusion": 2019,
    "Diffusion Models": 2019,
    "NeRF": 2020,
    "NeRF & Neural Fields": 2020,
    "CLIP": 2021,
    "Multimodal Alignment (CLIP)": 2021,
    "Swin": 2021,
    "MAE": 2021,
    "Self-Supervised Learning": 2019,
    "DETR": 2020,
    "DETR & Object Queries": 2020,
    "Large Vision-Language Models": 2022,
    "SAM": 2023,
    # U-Net 2015, SAM 2023. This is a mixed category.
    "Segmentation (SAM & U-Net)": 2015,
    "YOLO": 2016,
    "Object Detection": 2014,
    "R-CNN": 2014,
    "GAN": 2014,
    "GANs & Image Synthesis": 2014,
    "ResNet": 2015,
    "CNN Backbones": 2012,
    "CNN Architectures": 2012,
    "Video & Motion": 2010,
    "3D Reconstruction & SLAM": 2010,
    "Contrastive": 2019
}

CONCEPT_END_YEAR = {
    "Rnn": 2021,
    "Lstm": 2021,
    "Gru": 2021
}

TERM_HIERARCHY = {
    "Object Detection": {"YOLO", "R-CNN", "DETR", "Detection", "DETR & Object Queries"},
    "Detection": {"YOLO", "R-CNN", "DETR", "Object Detection"},
    "Recognition": {"Face Recognition", "Action Recognition", "Re-Identification", "Image Classification"},
    "Cnn": {"ResNet", "VGG", "EfficientNet", "CNN Backbones", "CNN Architectures"},
    "Transformer": {"ViT", "Swin", "DETR", "Vision Transformer (ViT)", "Vision Transformer"},
    "Generation": {"GAN", "Diffusion", "GANs & Image Synthesis", "Diffusion Models"},
    "Segmentation": {"Segmentation (SAM & U-Net)", "Semantic Segmentation", "Instance Segmentation"},
}

ERA_SPECIFIC_WHITELIST = {
    "2010-2012": {
        "SIFT", "HOG", "SVM", "DPM", "Sparse Coding", "BoW", "GIST", "Deformable Part Models",
        "Optical Flow", "Tracking", "Segmentation", "Detection", "Face Recognition", "Action Recognition",
        "Object Detection", "Image Classification", "Machine Learning", "Pattern Recognition", "Clustering",
        "Super-Resolution", "Denoising", "Inpainting", "Restoration", "Image Restoration"
    },
    "2013-2015": {
        "CNN", "AlexNet", "VGG", "R-CNN", "Dropout", "ReLU", "SPP-net", "Fast R-CNN", "OverFeat",
        "GoogLeNet", "Inception", "Deep Learning", "Convolutional Neural Network", "Detection", "Segmentation",
        "Transfer Learning", "Fine-tuning", "Data Augmentation", "Optimization", "Neural Network",
        "Recurrent Neural Network", "RNN", "LSTM"
    },
    "2016-2018": {
        "ResNet", "YOLO", "Faster R-CNN", "SSD", "GAN", "DCGAN", "CycleGAN", "Pix2Pix",
        "Mask R-CNN", "DenseNet", "MobileNet", "RetinaNet", "FPN", "LSTM", "RNN", "GRU", "Attention",
        "Semantic Segmentation", "Instance Segmentation"
    },
    "2019-2021": {
        "ViT", "Vision Transformer", "Transformer", "DETR", "EfficientNet", "Swin Transformer", "NeRF",
        "Self-Supervised Learning", "Contrastive Learning", "SimCLR", "MoCo", "CLIP", "PointNet",
        "GNN", "Graph Neural Network", "NAS", "AutoML", "Knowledge Distillation", "Domain Adaptation"
    },
    "2022-2025": {
        "Diffusion", "Diffusion Models", "Stable Diffusion", "Latent Diffusion", "DDPM", "Generative AI",
        "LLM", "Large Language Model", "Multimodal", "Vision-Language Model", "VLM", "CLIP",
        "BLIP", "LLaVA", "SAM", "Segment Anything", "Gaussian Splatting", "3D Gaussian Splatting",
        "YOLOv8", "YOLOv9", "YOLOv10", "BEV", "Occupancy Network", "Foundation Model", "LoRA", "ControlNet",
        "Sora", "Gemini", "GPT-4", "Prompt Engineering", "Zero-Shot", "Few-Shot", "Transformer", "Generative"
    }
}


def get_allowed_concepts_for_year(year):
    if not year:
        return set()
    allowed = set()

    # Always allow core tasks if they are not superseded (but we handle superseding via TERM_HIERARCHY)
    # Actually, let's just use the era whitelist + strict global whitelist
    # But we need to make sure we don't block "Detection" in 2024 if it's not redundant.
    # The user wants "High Quality" keywords.

    # Cumulative approach? No, strictly era-based is safer to avoid "RNN" in 2024.
    # But "CNN" is still relevant in 2024.
    # So we should allow previous eras' terms *unless* they are explicitly deprecated.

    # Better approach:
    # 1. Start with concepts from current era.
    # 2. Add concepts from *previous* eras (accumulated).
    # 3. Remove concepts in CONCEPT_END_YEAR if year > end_year.

    ranges = [
        (2010, 2012), (2013, 2015), (2016, 2018), (2019, 2021), (2022, 2025)
    ]

    for start, end in ranges:
        if start <= year:  # If this era has started by `year`
            key = f"{start}-{end}"
            if key in ERA_SPECIFIC_WHITELIST:
                allowed.update(ERA_SPECIFIC_WHITELIST[key])

    return allowed


def derive_semantic_tags(paper, tfidf_row, feature_names, limit, cluster_label=None):
    title = pick_field(paper, "title", "") or ""
    abstract = pick_field(paper, "abstract", "") or ""
    year_val = normalize_year(pick_field(paper, "year"))

    # Pre-calculate allowed concepts for this year
    allowed_concepts_set = get_allowed_concepts_for_year(year_val)
    if not allowed_concepts_set:
        # Fallback for years outside our ranges (e.g. pre-2010), allow everything in STRICT_WHITELIST
        allowed_concepts_set = STRICT_CONCEPT_WHITELIST

    topic_hits = sorted(TOPIC_MATCHER.find_matches(f"{title} {abstract}"))
    topic_hits.sort(key=lambda name: TOPIC_PRIORITY.get(name, 1), reverse=True)

    # Filter topic_hits by start year
    valid_topic_labels = []
    for label in topic_hits:
        pretty = prettify_concept(label)

        # Check against allowed set
        # We need to be careful: allowed_concepts_set has Title Case terms.
        # But we should also allow fuzzy matching if needed? No, let's be strict.
        # However, ERA_SPECIFIC_WHITELIST might not cover everything in SEMANTIC_TOPIC_DEFINITIONS.
        # So let's allow if it's in allowed_concepts_set OR it passes the old checks AND is not banned.

        # Actually, user wants strict whitelist.
        # So we check if `pretty` is in `allowed_concepts_set`.
        # But `allowed_concepts_set` might be missing some generic terms like "Object Detection".
        # I added "Detection" to eras.

        # Let's enforce strictness:
        # 1. Must be in allowed_concepts_set (which accumulates over eras)
        # 2. Must NOT be in CONCEPT_END_YEAR blacklist for this year

        # Check whitelist
        # We need normalized comparison
        if not any(normalize_phrase(pretty) == normalize_phrase(a) for a in allowed_concepts_set):
            continue

        start_year = CONCEPT_START_YEAR.get(
            label) or CONCEPT_START_YEAR.get(pretty)
        if start_year and year_val and year_val < start_year:
            continue

        end_year = CONCEPT_END_YEAR.get(pretty)
        if end_year and year_val and year_val > end_year:
            continue

        # New strict whitelist check
        # We check if the concept is "allowed" for this year.
        # This handles the "RNN in 2024" case because "RNN" is in 2016-2018 era but has end_year=2021.

        # Wait, get_allowed_concepts_for_year accumulates all previous eras.
        # So "RNN" (from 2016-2018) WILL be in `allowed_concepts_set` for 2024!
        # So we MUST rely on CONCEPT_END_YEAR to remove it.

        if is_meaningful_concept(label):
            valid_topic_labels.append(pretty)

    raw_concepts = ensure_list(pick_field(paper, "concepts", []))
    curated = []
    for concept in raw_concepts:
        if not is_meaningful_concept(concept):
            continue
        term = prettify_concept(concept)

        # Check against allowed set
        if not any(normalize_phrase(term) == normalize_phrase(a) for a in allowed_concepts_set):
            continue

        start_year = CONCEPT_START_YEAR.get(term)
        if start_year and year_val and year_val < start_year:
            continue

        end_year = CONCEPT_END_YEAR.get(term)
        if end_year and year_val and year_val > end_year:
            continue

        curated.append(term)

    tfidf_terms = []
    if tfidf_row is not None and feature_names is not None:
        raw_terms = top_terms_for_row(
            tfidf_row, feature_names, max(limit * 2, 6))
        for term in raw_terms:
            pretty = prettify_concept(term)
            if not is_meaningful_concept(pretty):
                continue

            # Check against allowed set
            if not any(normalize_phrase(pretty) == normalize_phrase(a) for a in allowed_concepts_set):
                continue

            start_year = CONCEPT_START_YEAR.get(pretty)
            if start_year and year_val and year_val < start_year:
                continue

            end_year = CONCEPT_END_YEAR.get(pretty)
            if end_year and year_val and year_val > end_year:
                continue

            tfidf_terms.append(pretty)

    enriched_context = " ".join(filter(
        None, [title, abstract, " ".join(raw_concepts), " ".join(tfidf_terms[:6])]))

    primary_label = DEFAULT_PRIMARY_SEMANTIC

    # Priority 0: Explicit Yearly Dominant Theme (User Design)
    if year_val in YEARLY_DOMINANT_MAP:
        cfg = YEARLY_DOMINANT_MAP[year_val]
        # Check if any keyword matches
        for pat in cfg["keywords"]:
            if re.search(pat, enriched_context, re.IGNORECASE):
                primary_label = cfg["theme"]
                # Inject the keyword into concepts
                raw_concepts.insert(0, prettify_concept(
                    pat.replace(r"\\b", "").replace(r"-", " ")))
                break

    # Priority 1: Canonical Topics (High-level tracks)
    if primary_label == DEFAULT_PRIMARY_SEMANTIC:
        candidate = select_canonical_semantic(enriched_context, None)
        # Check start/end year for canonical topic
        start_year = CONCEPT_START_YEAR.get(candidate)
        end_year = CONCEPT_END_YEAR.get(candidate)
        if not (start_year and year_val and year_val < start_year) and \
           not (end_year and year_val and year_val > end_year):
            primary_label = candidate

    # Priority 2: Problem Definitions (from Sankey)
    if primary_label == DEFAULT_PRIMARY_SEMANTIC:
        problem_hits = sorted(PROBLEM_MATCHER.find_matches(enriched_context))
        if problem_hits:
            primary_label = prettify_concept(problem_hits[0])

    # Priority 3: Method Definitions (from Sankey)
    if primary_label == DEFAULT_PRIMARY_SEMANTIC:
        method_hits = sorted(METHOD_MATCHER.find_matches(enriched_context))
        if method_hits:
            # Check start/end year for method
            cand = prettify_concept(method_hits[0])
            start_year = CONCEPT_START_YEAR.get(cand)
            end_year = CONCEPT_END_YEAR.get(cand)
            if not (start_year and year_val and year_val < start_year) and \
               not (end_year and year_val and year_val > end_year):
                primary_label = cand

    fallback_primary = None
    if cluster_label:
        start_year = CONCEPT_START_YEAR.get(cluster_label)
        end_year = CONCEPT_END_YEAR.get(cluster_label)
        # Check strict whitelist for cluster label too
        is_allowed = any(normalize_phrase(cluster_label) ==
                         normalize_phrase(a) for a in allowed_concepts_set)

        if is_allowed and not (start_year and year_val and year_val < start_year) and \
           not (end_year and year_val and year_val > end_year):
            fallback_primary = cluster_label

    if not fallback_primary and valid_topic_labels:
        fallback_primary = valid_topic_labels[0]

    # If still default, try to force a cluster label or top keyword
    if primary_label == DEFAULT_PRIMARY_SEMANTIC:
        if fallback_primary:
            primary_label = fallback_primary
        elif tfidf_terms:
            primary_label = tfidf_terms[0]
        elif curated:
            primary_label = curated[0]

    secondary_bucket = []
    if cluster_label and cluster_label != primary_label:
        # Filter secondary cluster label by year too
        start_year = CONCEPT_START_YEAR.get(cluster_label)
        end_year = CONCEPT_END_YEAR.get(cluster_label)
        is_allowed = any(normalize_phrase(cluster_label) ==
                         normalize_phrase(a) for a in allowed_concepts_set)

        if is_allowed and not (start_year and year_val and year_val < start_year) and \
           not (end_year and year_val and year_val > end_year):
            secondary_bucket.append(cluster_label)

    buckets = ([primary_label], valid_topic_labels,
               curated, secondary_bucket, tfidf_terms)
    seen = set()
    output = []

    # Prepend explicit Problem/Method matches to concepts if not already primary
    context_problems = sorted(PROBLEM_MATCHER.find_matches(enriched_context))
    context_methods = sorted(METHOD_MATCHER.find_matches(enriched_context))

    prioritized_concepts = []
    for p in context_problems:
        prioritized_concepts.append(prettify_concept(p))
    for m in context_methods:
        prioritized_concepts.append(prettify_concept(m))

    for term in prioritized_concepts:
        normalized = normalize_phrase(term)
        if not normalized or normalized in seen:
            continue
        # Also filter concepts by year
        start_year = CONCEPT_START_YEAR.get(term)
        end_year = CONCEPT_END_YEAR.get(term)
        if start_year and year_val and year_val < start_year:
            continue
        if end_year and year_val and year_val > end_year:
            continue

        # Check against allowed set
        if not any(normalize_phrase(term) == normalize_phrase(a) for a in allowed_concepts_set):
            continue

        # Hierarchy check
        is_redundant = False
        if term in TERM_HIERARCHY:
            children = TERM_HIERARCHY[term]
            for existing in output:
                if existing in children or normalize_phrase(existing) in {normalize_phrase(c) for c in children}:
                    is_redundant = True
                    break
        if is_redundant:
            continue

        seen.add(normalized)
        output.append(term)

    target = max(limit, 3)
    for bucket in buckets:
        for term in bucket:
            normalized = normalize_phrase(term)
            if not normalized or normalized in seen:
                continue

            # Year check
            start_year = CONCEPT_START_YEAR.get(term)
            end_year = CONCEPT_END_YEAR.get(term)
            if start_year and year_val and year_val < start_year:
                continue
            if end_year and year_val and year_val > end_year:
                continue

            # Check against allowed set
            if not any(normalize_phrase(term) == normalize_phrase(a) for a in allowed_concepts_set):
                continue

            # Hierarchy check
            is_redundant = False
            if term in TERM_HIERARCHY:
                children = TERM_HIERARCHY[term]
                for existing in output:
                    # Check if any existing term is a child of the current term
                    if existing in children or normalize_phrase(existing) in {normalize_phrase(c) for c in children}:
                        is_redundant = True
                        break
            if is_redundant:
                continue

            seen.add(normalized)
            output.append(term)
            if len(output) >= target:
                break
        if len(output) >= target:
            break

    if not output:
        if tfidf_terms:
            output.append(tfidf_terms[0])
        elif curated:
            output.append(curated[0])
        else:
            output.append(DEFAULT_PRIMARY_SEMANTIC)

    # Post-process to remove redundant parents (e.g. remove "Detection" if "YOLO" is present)
    final_output = []
    to_remove = set()
    for parent in output:
        if parent in TERM_HIERARCHY:
            children = TERM_HIERARCHY[parent]
            for child in output:
                if child == parent:
                    continue
                if child in children or normalize_phrase(child) in {normalize_phrase(c) for c in children}:
                    to_remove.add(parent)
                    break

    final_output = [c for c in output if c not in to_remove]

    # Ensure we still have something
    if not final_output and output:
        final_output = output[:1]

    return final_output[:target]


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

        # Try to improve cluster label with Problems/Methods if canonical fails
        if not canonical or canonical == DEFAULT_PRIMARY_SEMANTIC:
            problem_hits = sorted(PROBLEM_MATCHER.find_matches(context))
            if problem_hits:
                canonical = prettify_concept(problem_hits[0])
            else:
                method_hits = sorted(METHOD_MATCHER.find_matches(context))
                if method_hits:
                    canonical = prettify_concept(method_hits[0])

        if canonical:
            label = canonical
        elif keywords:
            label = " / ".join(keywords[:3])
        else:
            label = f"Emerging Cluster {cluster_id + 1}"

        if label == "Uncategorized Research":
            if keywords:
                label = " / ".join(keywords[:2])
            else:
                label = f"Cluster {cluster_id + 1}"

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

            # Verify cluster label against year
            if cluster_label:
                c_start = CONCEPT_START_YEAR.get(cluster_label)
                c_end = CONCEPT_END_YEAR.get(cluster_label)
                if c_start and year and year < c_start:
                    cluster_label = None
                elif c_end and year and year > c_end:
                    cluster_label = None

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
