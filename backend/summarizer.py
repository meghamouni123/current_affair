import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_bart_tokenizer = None
_bart_model     = None
_mpnet_model    = None


def _get_bart():
    global _bart_tokenizer, _bart_model
    if _bart_tokenizer is None:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        logger.info("Loading facebook/bart-large-cnn...")
        _bart_tokenizer = AutoTokenizer.from_pretrained('facebook/bart-large-cnn')
        _bart_model     = AutoModelForSeq2SeqLM.from_pretrained('facebook/bart-large-cnn')
        logger.info("BART model loaded.")
    return _bart_tokenizer, _bart_model


def _get_mpnet():
    global _mpnet_model
    if _mpnet_model is None:
        try:
            from classifier import get_classifier
            clf = get_classifier()
            if clf.mpnet_model is not None:
                _mpnet_model = clf.mpnet_model
                return _mpnet_model
        except Exception:
            pass
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading MPNet for LexRank pre-summarization...")
            _mpnet_model = SentenceTransformer('all-mpnet-base-v2')
        except Exception as e:
            logger.error(f"MPNet load failed: {e}")
    return _mpnet_model


def _lexrank_extract(text: str, max_tokens: int = 950) -> str:
    import nltk
    import numpy as np
    import networkx as nx
    from sklearn.metrics.pairwise import cosine_similarity

    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        nltk.download('punkt_tab', quiet=True)
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)

    sentences = nltk.sent_tokenize(text)
    sentences = [s.strip() for s in sentences if len(s.split()) >= 5]
    if len(sentences) <= 3:
        return text

    mpnet = _get_mpnet()
    if mpnet is None:
        words = text.split()
        return ' '.join(words[:800])

    sent_embs  = mpnet.encode(sentences, batch_size=32, show_progress_bar=False)
    sim_matrix = cosine_similarity(sent_embs)
    np.fill_diagonal(sim_matrix, 0)

    graph = nx.from_numpy_array(sim_matrix)
    try:
        scores = nx.eigenvector_centrality_numpy(graph)
    except Exception:
        scores = nx.pagerank(graph)

    ranked_indices = sorted(scores, key=scores.get, reverse=True)
    selected = []
    token_count = 0
    for idx in ranked_indices:
        sent = sentences[idx]
        toks = len(sent.split())
        if token_count + toks > max_tokens:
            break
        selected.append((idx, sent))
        token_count += toks

    selected.sort(key=lambda x: x[0])
    return ' '.join(s for _, s in selected)


def _bart_summarize(input_text: str) -> Optional[str]:
    try:
        tokenizer, model = _get_bart()
        inputs = tokenizer(input_text, return_tensors='pt', max_length=1024, truncation=True)
        summary_ids = model.generate(
            inputs['input_ids'],
            max_length=150,
            min_length=50,
            num_beams=4,
            early_stopping=True,
            no_repeat_ngram_size=3
        )
        return tokenizer.decode(summary_ids[0], skip_special_tokens=True).strip()
    except Exception as e:
        logger.error(f"BART summarization error: {e}")
        return None


def _format_bullets(summary: str, headline: str, num_bullets: int = 6) -> Optional[str]:
    if not summary:
        return None

    raw = re.split(r'(?<=[.!?])\s+', summary.strip())
    sentences = [s.strip().rstrip('.') for s in raw if len(s.split()) >= 8]

    if not sentences:
        return None

    def _overlap(s1: str, s2: str) -> float:
        stop = {'the','a','an','and','or','in','on','at','to','for','of','with','by','is','are','was','were','has','have'}
        w1 = set(re.sub(r'[^a-z0-9\s]', ' ', s1.lower()).split()) - stop
        w2 = set(re.sub(r'[^a-z0-9\s]', ' ', s2.lower()).split()) - stop
        if not w1:
            return 0.0
        return len(w1 & w2) / len(w1)

    filtered = [s for s in sentences if _overlap(headline, s) < 0.55]
    if not filtered:
        filtered = sentences

    selected = filtered[:num_bullets]
    if len(selected) < 3:
        extra = [s for s in sentences if s not in filtered]
        selected = (filtered + extra)[:num_bullets]
    if len(selected) < 3:
        return None

    bullets = []
    for sent in selected:
        # Ensure each bullet has at least ~2 lines worth of content (15+ words)
        if len(sent.split()) < 10:
            continue
        if len(sent) > 280:
            sent = sent[:280].rsplit(' ', 1)[0] + '…'
        sent = sent[0].upper() + sent[1:]
        bullets.append(f'• {sent}.')

    return '\n'.join(bullets) if len(bullets) >= 3 else None


def generate_summary(headline: str, text: str, num_bullets: int = 6) -> Optional[str]:
    body = (text or '').strip()
    if not body:
        body = headline

    word_count = len(body.split())

    if word_count > 800:
        input_text = _lexrank_extract(body, max_tokens=950)
    else:
        input_text = body

    raw_summary = _bart_summarize(input_text)

    if not raw_summary:
        return _extractive_fallback(headline, body, num_bullets)

    bullets = _format_bullets(raw_summary, headline, num_bullets)

    if not bullets:
        return _extractive_fallback(headline, body, num_bullets)

    return bullets


def _extractive_fallback(headline: str, text: str, num_bullets: int = 6) -> Optional[str]:
    import math
    from collections import Counter

    STOPWORDS = {
        'the','a','an','and','or','but','in','on','at','to','for','of','with',
        'by','from','is','are','was','were','be','been','has','have','had',
        'this','that','these','those','it','its','as','also','which','who',
        'not','no','so','such','he','she','they','we','their','his','her',
        'said','says','told','according',
    }

    def _split(t):
        abbrevs = r'(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|etc|approx|Rs|U\.S|U\.K)'
        p = re.sub(rf'\b({abbrevs})\.', r'\1<DOT>', t.strip())
        sents = re.split(r'(?<=[.!?])\s+', p)
        return [s.replace('<DOT>', '.').strip() for s in sents if len(s.split()) >= 6]

    sentences = _split(text)
    if not sentences:
        return None

    def _hl_overlap(s):
        w1 = set(re.sub(r'[^a-z0-9\s]', ' ', headline.lower()).split()) - STOPWORDS
        w2 = set(re.sub(r'[^a-z0-9\s]', ' ', s.lower()).split()) - STOPWORDS
        if not w1: return 0.0
        return len(w1 & w2) / len(w1)

    body_sents = [s for s in sentences if _hl_overlap(s) < 0.55]
    if len(body_sents) < 2:
        body_sents = sentences

    all_words = []
    for s in body_sents:
        all_words.extend(
            w.lower().strip('.,!?;:') for w in s.split()
            if w.lower().strip('.,!?;:') not in STOPWORDS and len(w) > 2
        )
    tf = Counter(all_words)
    total = max(sum(tf.values()), 1)
    doc_cnt = Counter()
    for s in body_sents:
        doc_cnt.update(set(w.lower().strip('.,!?;:') for w in s.split()))
    n = len(body_sents)

    NUM_PAT   = re.compile(r'\b\d+(?:\.\d+)?(?:\s*%|\s*crore|\s*billion|\s*lakh)?\b')
    IMPORTANT = ['launched','inaugurated','signed','appointed','won','first','india',
                 'government','scheme','awarded','ranked','record','approved','passed']

    def score(sent, pos):
        words = sent.lower().split()
        if not words: return 0.0
        ws = sum(
            (tf.get(w.strip('.,!?;:'), 0)/total) *
            math.log((n+1)/(doc_cnt.get(w.strip('.,!?;:'), 0)+1))
            for w in words
        ) / len(words)
        ks = sum(1 for t in IMPORTANT if t in sent.lower()) * 0.15
        ns = min(len(NUM_PAT.findall(sent)) * 0.12, 0.35)
        ps = 0.25 if pos == 0 else (0.15 if pos <= n*0.2 else 0.0)
        lp = 1.0 if len(words) <= 35 else 0.75
        return (ws + ks + ns + ps) * lp

    scored   = sorted(enumerate(body_sents), key=lambda x: score(x[1], x[0]), reverse=True)
    top      = sorted(scored[:num_bullets], key=lambda x: x[0])
    selected = [s for _, s in top]

    if len(selected) < 3:
        return None

    bullets = []
    for sent in selected:
        sent = sent.strip().rstrip('.')
        if not sent: continue
        if len(sent.split()) < 10:
            continue
        if len(sent) > 280:
            sent = sent[:280].rsplit(' ', 1)[0] + '…'
        sent = sent[0].upper() + sent[1:]
        bullets.append(f'• {sent}.')

    return '\n'.join(bullets) if len(bullets) >= 3 else None
