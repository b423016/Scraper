"""
Central configuration for the Multi-Source Scraper and Trust Scoring System.
All tunable constants and settings live here.
"""

# ---------------------------------------------------------------------------
# Input URLs (placeholder – replace with real ones before final run)
# ---------------------------------------------------------------------------
INPUT_URLS = [
    # 3 Blog Posts
    "https://blog.google/technology/health/google-research-healthcare-ai/",
    "https://blog.google/technology/health/how-were-using-ai-to-help-transform-healthcare/",
    "https://blog.google/innovation-and-ai/technology/health/google-ai-and-health/3-predictions-for-ai-in-healthcare-in-2024/",
    # 2 YouTube Videos
    "https://www.youtube.com/watch?v=cdXzR-cmmkc",
    "https://www.youtube.com/watch?v=Ivn4Gi0aCfc",
    # 1 PubMed Article
    "https://pubmed.ncbi.nlm.nih.gov/39801619/",
]

# ---------------------------------------------------------------------------
# Embedding Model
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# ---------------------------------------------------------------------------
# Trust Score Weights  (must sum to 1.0)
# ---------------------------------------------------------------------------
TRUST_WEIGHTS = {
    "author_credibility": 0.25,
    "citation_count": 0.20,
    "domain_authority": 0.20,
    "recency": 0.20,
    "medical_disclaimer": 0.15,
}

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
MIN_CHUNK_LENGTH = 50      # characters
MAX_CHUNK_LENGTH = 1500    # characters

# ---------------------------------------------------------------------------
# Topic Tagging
# ---------------------------------------------------------------------------
TOP_K_TAGS = 5
SIMILARITY_THRESHOLD = 0.35

# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------
DUPLICATE_THRESHOLD = 0.92

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_UNKNOWN = "unknown"

# ---------------------------------------------------------------------------
# Output Paths
# ---------------------------------------------------------------------------
OUTPUT_DIR = "output"
COMBINED_OUTPUT = "output/scraped_data.json"
BLOGS_OUTPUT = "output/blogs.json"
YOUTUBE_OUTPUT = "output/youtube.json"
PUBMED_OUTPUT = "output/pubmed.json"

# ---------------------------------------------------------------------------
# PubMed / Entrez
# ---------------------------------------------------------------------------
ENTREZ_EMAIL = "your-email@example.com"  # Required by NCBI Entrez

# ---------------------------------------------------------------------------
# Controlled Topic Vocabulary
# Each topic has a tag and a rich description for semantic matching.
# ---------------------------------------------------------------------------
TOPIC_VOCABULARY = [
    {
        "tag": "artificial intelligence",
        "description": "artificial intelligence, AI systems, intelligent agents, automation, cognitive computing",
    },
    {
        "tag": "machine learning",
        "description": "machine learning, supervised learning, unsupervised learning, neural networks, model training, prediction",
    },
    {
        "tag": "deep learning",
        "description": "deep learning, convolutional neural networks, recurrent networks, transformers, neural architecture",
    },
    {
        "tag": "natural language processing",
        "description": "natural language processing, NLP, text analysis, language models, sentiment analysis, tokenization",
    },
    {
        "tag": "healthcare",
        "description": "healthcare, medicine, hospitals, patient care, healthcare systems, medical services, clinical practice",
    },
    {
        "tag": "medical research",
        "description": "medical research, clinical trials, biomedical studies, drug discovery, epidemiology, public health research",
    },
    {
        "tag": "clinical medicine",
        "description": "clinical medicine, diagnosis, treatment, patient outcomes, medical procedures, clinical decision support",
    },
    {
        "tag": "public health",
        "description": "public health, disease prevention, health policy, vaccination, epidemiology, population health",
    },
    {
        "tag": "data science",
        "description": "data science, data analysis, statistics, data visualization, exploratory analysis, big data",
    },
    {
        "tag": "web scraping",
        "description": "web scraping, HTML parsing, crawling, web data extraction, data collection from websites",
    },
    {
        "tag": "data engineering",
        "description": "data engineering, data pipelines, ETL, data warehousing, data infrastructure, data processing",
    },
    {
        "tag": "information retrieval",
        "description": "information retrieval, search engines, document indexing, ranking, query processing, semantic search",
    },
    {
        "tag": "education",
        "description": "education, learning, teaching, online courses, e-learning, academic instruction, training",
    },
    {
        "tag": "cybersecurity",
        "description": "cybersecurity, network security, encryption, threat detection, vulnerability, information security",
    },
    {
        "tag": "software engineering",
        "description": "software engineering, software development, programming, code quality, testing, DevOps, architecture",
    },
    {
        "tag": "robotics",
        "description": "robotics, autonomous systems, robotic process automation, drones, mechatronics, actuators",
    },
    {
        "tag": "finance",
        "description": "finance, fintech, banking, investment, trading, financial markets, economic analysis",
    },
    {
        "tag": "climate and environment",
        "description": "climate change, environment, sustainability, renewable energy, carbon emissions, ecology",
    },
    {
        "tag": "biotechnology",
        "description": "biotechnology, genetic engineering, genomics, bioinformatics, synthetic biology, CRISPR",
    },
    {
        "tag": "ethics and policy",
        "description": "ethics, AI ethics, technology policy, regulation, governance, fairness, bias, responsible AI",
    },
]

# ---------------------------------------------------------------------------
# Medical-related tags (for disclaimer logic)
# ---------------------------------------------------------------------------
MEDICAL_TAGS = {
    "healthcare",
    "medical research",
    "clinical medicine",
    "public health",
    "biotechnology",
}

# ---------------------------------------------------------------------------
# Medical disclaimer keywords
# ---------------------------------------------------------------------------
DISCLAIMER_KEYWORDS = [
    "not a substitute for medical advice",
    "not medical advice",
    "consult a qualified physician",
    "consult your doctor",
    "consult a healthcare professional",
    "informational purposes only",
    "educational purposes only",
    "does not constitute medical advice",
    "seek professional medical advice",
    "speak with your healthcare provider",
]
