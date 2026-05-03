import os
import logging
import numpy as np
from typing import Tuple, List

logger = logging.getLogger(__name__)

MODEL_DIR       = os.path.join(os.path.dirname(__file__), '..', 'models')
CLASSIFIER_PATH = os.path.join(MODEL_DIR, 'ca_classifier_mpnet.pkl')

CATEGORIES = [
    'Economy & Banking', 'Polity & Governance', 'International Relations',
    'Science & Technology', 'Schemes & Appointments', 'Reports & Indices',
    'Sports', 'Awards & Honours', 'Important Days & Obituaries',
    'Summits & Conferences', 'National News', 'State News', 'NOT_RELEVANT'
]

CATEGORY_PATTERNS = {
    'Economy & Banking': [
        'rbi', 'reserve bank', 'repo rate', 'gdp', 'inflation', 'fiscal deficit',
        'sebi', 'sensex', 'nifty', 'gst', 'budget', 'fdi', 'forex', 'rupee',
        'monetary policy', 'interest rate', 'cpi', 'wpi', 'banking', 'nbfc',
        'credit policy', 'bank rate', 'msme', 'disinvestment', 'tax revenue',
        'trade deficit', 'rbi governor', 'financial inclusion', 'upi', 'npci',
    ],
    'Polity & Governance': [
        'parliament', 'lok sabha', 'rajya sabha', 'constitution', 'supreme court',
        'high court', 'election commission', 'cabinet', 'bill passed', 'amendment',
        'act passed', 'ordinance', 'governor', 'chief justice', 'niti aayog',
        'president of india', 'prime minister', 'chief minister', 'preamble',
        'fundamental rights', 'article 370', 'eci', 'general election', 'rti',
        'lokpal', 'enforcement directorate', 'delimitation', 'by-election',
    ],
    'International Relations': [
        'bilateral', 'mou signed', 'diplomatic', 'foreign minister', 'ambassador',
        'united nations', 'g20', 'brics', 'saarc', 'asean', 'treaty',
        'summit between', 'state visit', 'trade agreement', 'quad', 'nato',
        'india-china', 'india-pakistan', 'india-us', 'india-russia', 'india-japan',
        'foreign policy', 'geopolitics', 'sanctions', 'un security council',
        'extradition', 'defence cooperation', 'strategic partnership',
    ],
    'Science & Technology': [
        'isro', 'nasa', 'satellite launch', 'space mission', 'drdo', 'iit',
        'artificial intelligence', 'quantum', 'nuclear', 'vaccine', 'genome',
        'spacecraft', 'rocket launch', 'innovation', '5g', 'semiconductor',
        'chandrayaan', 'gaganyaan', 'aditya', 'pslv', 'gslv',
        'climate change', 'renewable energy', 'solar energy', 'electric vehicle',
        'biotechnology', 'gene editing', 'cybersecurity', 'digital india',
    ],
    'Schemes & Appointments': [
        'yojana', 'scheme launched', 'programme launched', 'portal launched',
        'appointed as', 'takes charge', 'new director', 'new ceo', 'inaugurated',
        'foundation stone', 'welfare scheme', 'abhiyan', 'mission launched',
        'pm modi launches', 'government launches', 'ministry launches',
        'appointed chairman', 'appointed director', 'appointed governor',
        'new appointment', 'takes over as', 'elected as president',
        'pm kisan', 'ayushman bharat', 'jan dhan', 'mudra', 'jal jeevan',
        'ujjwala', 'swachh bharat', 'make in india', 'svamitva',
    ],
    'Reports & Indices': [
        'index released', 'report released', 'ranking', 'survey', 'report by',
        'world bank report', 'imf report', 'undp', 'human development index',
        'ease of doing business', 'global hunger', 'happiness report',
        'press freedom index', 'corruption perception', 'global innovation index',
        'economic survey', 'annual report', 'niti aayog report', 'rbi report',
        'india ranked', 'india ranks', 'india position', 'global competitiveness',
    ],
    'Sports': [
        'cricket', 'ipl', 'world cup', 'olympics', 'commonwealth games',
        'asian games', 'gold medal', 'silver medal', 'bronze medal',
        'championship', 'fifa', 'tennis', 'badminton', 'hockey', 'kabaddi',
        'bcci', 'test match', 'odi', 't20', 'grand slam', 'wimbledon',
        'chess olympiad', 'cwg', 'world athletics', 'para olympics',
        'khelo india', 'national games', 'arjuna award', 'dronacharya',
    ],
    'Awards & Honours': [
        'padma', 'bharat ratna', 'nobel prize', 'oscar award', 'booker prize',
        'gallantry award', 'bravery award', 'conferred', 'national award',
        'received award', 'grammy', 'pulitzer', 'magsaysay',
        'padma vibhushan', 'padma bhushan', 'padma shri', 'param vir chakra',
        'ashoka chakra', 'sahitya akademi', 'man booker', 'fields medal',
        'awarded to', 'felicitated', 'honoured with', 'civilian honour',
        'lifetime achievement', 'honorary doctorate',
    ],
    'Important Days & Obituaries': [
        'world day', 'international day', 'national day', 'observed on',
        'birth anniversary', 'death anniversary', 'foundation day',
        'passes away', 'passed away', 'demise', 'veteran dies', 'commemorat',
        'world environment day', 'world health day', 'republic day',
        'independence day', 'gandhi jayanti', 'teachers day', 'children day',
        'constitution day', 'national science day', 'international yoga day',
        'died at', 'died on', 'obituary', 'condolences', 'former president',
    ],
    'Summits & Conferences': [
        'cop conference', 'g20 summit', 'saarc summit', 'brics summit',
        'ministerial meet', 'world economic forum', 'davos', 'annual session',
        'global forum', 'international conference', 'summit held', 'conclave',
        'g7 summit', 'nato summit', 'un general assembly', 'unga',
        'climate summit', 'cop28', 'cop29', 'cop30', 'paris agreement',
        'bilateral summit', 'quad summit', 'east asia summit', 'asean summit',
    ],
    'National News': [
        'india government', 'central government', 'union minister',
        'ministry of', 'cabinet minister', 'national highway', 'railway project',
        'metro rail', 'airport', 'flood relief', 'disaster management', 'ndrf',
        'security forces', 'naxal', 'terrorist', 'encounter',
        'supreme court order', 'high court order', 'cbi probe',
    ],
    'State News': [
        'state government', 'chief minister', 'state cabinet',
        'state assembly', 'vidhan sabha', 'state budget',
        'andhra pradesh', 'telangana', 'karnataka', 'tamil nadu', 'kerala',
        'maharashtra', 'gujarat', 'rajasthan', 'uttar pradesh', 'bihar',
        'west bengal', 'odisha', 'madhya pradesh', 'punjab', 'haryana',
        'assam', 'manipur', 'goa', 'delhi', 'jammu kashmir', 'ladakh',
    ],
}

NOT_RELEVANT_SIGNALS = [
    'bollywood', 'celebrity gossip', 'horoscope', 'dating tips',
    'fashion week', 'beauty tips', 'tv serial', 'reality show',
    'box office', 'web series', 'hair care', 'skin care',
    'weight loss tips', 'movie review', 'gossip',
    'weather forecast', 'rain alert', 'traffic jam', 'road block',
    'recipe', 'cooking tips', 'restaurant review', 'food review',
    'stock tips', 'buy sell', 'share price target', 'multibagger',
    'ipl score', 'match score', 'live score', 'fantasy team',
]


def train_classifier(dataset_path: str = None):
    import pandas as pd
    from sentence_transformers import SentenceTransformer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score
    import joblib

    if dataset_path is None:
        dataset_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'cleaned_dataset.csv')

    logger.info("Loading dataset...")
    df = pd.read_csv(dataset_path)
    df = df.dropna(subset=['text', 'category'])
    df = df[df['text'].astype(str).str.split().str.len() >= 8]

    texts  = df['text'].astype(str).tolist()
    labels = df['category'].tolist()

    logger.info("Loading all-mpnet-base-v2...")
    mpnet = SentenceTransformer('all-mpnet-base-v2')
    logger.info(f"Encoding {len(texts)} articles...")
    embeddings = mpnet.encode(texts, show_progress_bar=True, batch_size=32)

    X_train, X_test, y_train, y_test = train_test_split(
        embeddings, labels, test_size=0.2, random_state=42, stratify=labels
    )

    logger.info("Training LogisticRegression on MPNet embeddings...")
    clf = LogisticRegression(max_iter=1000, solver='lbfgs', random_state=42)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    logger.info(f"Validation Accuracy: {acc:.4f}")
    logger.info("\n" + classification_report(y_test, y_pred))

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(clf, CLASSIFIER_PATH)
    logger.info(f"Classifier saved → {CLASSIFIER_PATH}")
    return acc


class ArticleClassifier:
    def __init__(self):
        self.mpnet_model = None
        self.clf         = None
        self.is_loaded   = False
        self._load_models()

    def _load_models(self):
        try:
            import joblib
            from sentence_transformers import SentenceTransformer

            MPNET_LOCAL = os.path.join(MODEL_DIR, 'mpnet_model')
            if os.path.exists(MPNET_LOCAL):
                logger.info("Loading MPNet from local models/ folder...")
                self.mpnet_model = SentenceTransformer(MPNET_LOCAL)
            else:
                logger.info("Downloading MPNet (first time only ~420MB)...")
                self.mpnet_model = SentenceTransformer('all-mpnet-base-v2')
                self.mpnet_model.save(MPNET_LOCAL)
                logger.info(f"MPNet saved → next run fast!")

            if os.path.exists(CLASSIFIER_PATH):
                self.clf = joblib.load(CLASSIFIER_PATH)
                self.is_loaded = True
                logger.info("MPNet + LogisticRegression loaded successfully.")
            else:
                logger.warning(
                    f"No trained classifier at {CLASSIFIER_PATH}. "
                    "Run: python scripts/train_model.py\n"
                    "Using keyword fallback until model is trained."
                )
        except Exception as e:
            logger.error(f"Model load error: {e}")

    def get_embedding(self, text: str) -> np.ndarray:
        if self.mpnet_model is None:
            return np.zeros(768)
        return self.mpnet_model.encode([text])[0]

    def get_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        if self.mpnet_model is None:
            return np.zeros((len(texts), 768))
        return self.mpnet_model.encode(texts, batch_size=32, show_progress_bar=False)

    def classify(self, text: str) -> Tuple[str, float]:
        if not self.is_loaded or self.clf is None:
            return self._keyword_fallback(text)
        try:
            emb   = self.mpnet_model.encode([text])
            probs = self.clf.predict_proba(emb)[0]
            idx   = int(np.argmax(probs))
            return self.clf.classes_[idx], round(float(probs[idx]), 4)
        except Exception as e:
            logger.error(f"classify error: {e}")
            return self._keyword_fallback(text)

    def classify_batch(self, texts: List[str]) -> List[Tuple[str, float]]:
        if not self.is_loaded or self.clf is None:
            return [self._keyword_fallback(t) for t in texts]
        try:
            embs  = self.mpnet_model.encode(texts, batch_size=32)
            probs = self.clf.predict_proba(embs)
            return [
                (self.clf.classes_[int(np.argmax(p))], round(float(np.max(p)), 4))
                for p in probs
            ]
        except Exception as e:
            logger.error(f"batch classify error: {e}")
            return [self._keyword_fallback(t) for t in texts]

    def is_exam_relevant(self, text: str, threshold: float = 0.80) -> Tuple[bool, str, float]:
        tl = text.lower()
        for sig in NOT_RELEVANT_SIGNALS:
            if sig in tl:
                return False, 'NOT_RELEVANT', 0.30
        # Strong keyword override — if 2+ keywords match a category, use it
        kw_scores = {
            cat: sum(1 for kw in kws if kw in tl)
            for cat, kws in CATEGORY_PATTERNS.items()
        }
        kw_scores = {k: v for k, v in kw_scores.items() if v >= 2}
        if kw_scores:
            best_kw = max(kw_scores, key=kw_scores.get)
            kw_conf = min(0.82 + kw_scores[best_kw] * 0.03, 0.95)
            return True, best_kw, kw_conf
        # ML model classification
        cat, conf = self.classify(text)
        return (conf >= threshold and cat != 'NOT_RELEVANT'), cat, conf

    def _keyword_fallback(self, text: str) -> Tuple[str, float]:
        tl = text.lower()
        for sig in NOT_RELEVANT_SIGNALS:
            if sig in tl:
                return 'NOT_RELEVANT', 0.75
        scores = {
            cat: sum(1 for kw in kws if kw in tl)
            for cat, kws in CATEGORY_PATTERNS.items()
        }
        scores = {k: v for k, v in scores.items() if v > 0}
        if not scores:
            return 'NOT_RELEVANT', 0.50
        best = max(scores, key=scores.get)
        return best, min(0.68 + scores[best] * 0.05, 0.93)


_instance: ArticleClassifier = None


def get_classifier() -> ArticleClassifier:
    global _instance
    if _instance is None:
        _instance = ArticleClassifier()
    return _instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    clf = get_classifier()
    tests = [
        "RBI keeps repo rate unchanged at 6.5% monetary policy",
        "India launches PSLV satellite from Sriharikota ISRO",
        "India and Japan sign semiconductor cooperation MoU bilateral",
        "PM Modi inaugurates PM Surya Ghar yojana scheme solar energy",
        "India wins gold medal Asian Games 2026 100m sprint",
        "Padma Vibhushan awarded to renowned classical dancer",
        "Bollywood actor celebrity gossip movie review",
    ]
    for t in tests:
        cat, conf = clf.classify(t)
        mark = '✅' if cat != 'NOT_RELEVANT' and conf >= 0.8 else '❌'
        print(f"  {mark} [{cat}] ({conf:.2f}) {t[:70]}")