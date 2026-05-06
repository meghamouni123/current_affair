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
            _mpnet_model = SentenceTransformer('all-mpnet-base-v2')
        except Exception as e:
            logger.error(f"MPNet load failed: {e}")
    return _mpnet_model


def _split_sentences(text: str) -> List[str]:
    abbrevs = r'(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|etc|approx|Rs|U\.S|U\.K)'
    t = re.sub(rf'\b({abbrevs})\.', r'\1<DOT>', text.strip())
    sents = re.split(r'(?<=[.!?])\s+', t)
    result = []
    for s in sents:
        s = s.replace('<DOT>', '.').strip()
        if len(s.split()) >= 6:
            result.append(s)
    return result


def _word_overlap(s1: str, s2: str) -> float:
    STOP = {'the','a','an','and','or','but','in','on','at','to','for','of','with',
            'by','from','is','are','was','were','be','been','has','have','had',
            'this','that','it','its','as','also','which','who','not','no','so',
            'he','she','they','we','their','his','her','said','says','told'}
    def words(s):
        return set(re.sub(r'[^a-z0-9\s]', ' ', s.lower()).split()) - STOP
    w1, w2 = words(s1), words(s2)
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)


def _is_duplicate(sent: str, selected: List[str], threshold: float = 0.40) -> bool:
    for s in selected:
        if _word_overlap(sent, s) >= threshold:
            return True
    return False


def _lexrank_extract(text: str, max_tokens: int = 950) -> str:
    import nltk
    import numpy as np
    import networkx as nx
    from sklearn.metrics.pairwise import cosine_similarity

    for resource in ['punkt_tab', 'punkt']:
        try:
            nltk.data.find(f'tokenizers/{resource}')
        except LookupError:
            nltk.download(resource, quiet=True)

    sentences = nltk.sent_tokenize(text)
    sentences = [s.strip() for s in sentences if len(s.split()) >= 5]
    if len(sentences) <= 3:
        return text

    mpnet = _get_mpnet()
    if mpnet is None:
        return ' '.join(text.split()[:800])

    sent_embs  = mpnet.encode(sentences, batch_size=32, show_progress_bar=False)
    sim_matrix = cosine_similarity(sent_embs)
    np.fill_diagonal(sim_matrix, 0)

    graph = nx.from_numpy_array(sim_matrix)
    try:
        scores = nx.eigenvector_centrality_numpy(graph)
    except Exception:
        scores = nx.pagerank(graph)

    ranked = sorted(scores, key=scores.get, reverse=True)
    selected, token_count = [], 0
    for idx in ranked:
        toks = len(sentences[idx].split())
        if token_count + toks > max_tokens:
            break
        selected.append((idx, sentences[idx]))
        token_count += toks

    selected.sort(key=lambda x: x[0])
    return ' '.join(s for _, s in selected)


def _bart_summarize(input_text: str) -> Optional[str]:
    try:
        tokenizer, model = _get_bart()
        inputs = tokenizer(input_text, return_tensors='pt', max_length=1024, truncation=True)
        summary_ids = model.generate(
            inputs['input_ids'],
            max_length=220,
            min_length=80,
            num_beams=4,
            early_stopping=True,
            no_repeat_ngram_size=3,
            length_penalty=1.5,
        )
        return tokenizer.decode(summary_ids[0], skip_special_tokens=True).strip()
    except Exception as e:
        logger.error(f"BART summarization error: {e}")
        return None


def _build_bullets(
    bart_summary: Optional[str],
    full_text: str,
    headline: str,
    num_bullets: int = 6,
) -> Optional[str]:
    bart_sents = _split_sentences(bart_summary) if bart_summary else []

    full_sents = _split_sentences(full_text)

    import math
    from collections import Counter
    STOP = {'the','a','an','and','or','but','in','on','at','to','for','of','with',
            'by','from','is','are','was','were','be','been','has','have','had',
            'this','that','it','its','as','also','which','who','not','no','so',
            'he','she','they','we','their','his','her','said','says','told'}
    NUM_PAT   = re.compile(r'\b\d+(?:\.\d+)?(?:\s*%|\s*crore|\s*billion|\s*lakh|\s*million)?\b')
    IMPORTANT = ['launched','inaugurated','signed','appointed','won','first','india',
                 'government','scheme','awarded','ranked','record','approved','passed',
                 'agreement','bilateral','summit','policy','act','bill','mission']

    all_words = []
    for s in full_sents:
        all_words.extend(w.lower().strip('.,!?;:') for w in s.split()
                         if w.lower().strip('.,!?;:') not in STOP and len(w) > 2)
    tf = Counter(all_words)
    total = max(sum(tf.values()), 1)
    n = len(full_sents)

    def score(sent, pos):
        words = sent.lower().split()
        if not words: return 0.0
        ws = sum(tf.get(w.strip('.,!?;:'), 0) / total for w in words) / len(words)
        ks = sum(1 for t in IMPORTANT if t in sent.lower()) * 0.15
        ns = min(len(NUM_PAT.findall(sent)) * 0.12, 0.35)
        ps = 0.20 if pos == 0 else (0.10 if pos <= n * 0.2 else 0.0)
        lp = 1.0 if len(words) <= 35 else 0.75
        return (ws + ks + ns + ps) * lp

    scored_full = sorted(enumerate(full_sents), key=lambda x: score(x[1], x[0]), reverse=True)
    top_full = [s for _, s in scored_full[:num_bullets * 2]]

    selected: List[str] = []

    for sent in bart_sents:
        sent = sent.strip().rstrip('.')
        if sent.endswith('?'):
            continue
        if len(sent.split()) < 8:
            continue
        if _word_overlap(headline, sent) > 0.65:
            continue
        if _is_duplicate(sent, selected):
            continue
        selected.append(sent)
        if len(selected) >= num_bullets:
            break

    for sent in top_full:
        if len(selected) >= num_bullets:
            break
        sent = sent.strip().rstrip('.')
        if sent.endswith('?'):
            continue
        if len(sent.split()) < 8:
            continue
        if _word_overlap(headline, sent) > 0.65:
            continue
        if _is_duplicate(sent, selected, threshold=0.35):
            continue
        selected.append(sent)

    if len(selected) < 3:
        return None

    bullets = []
    for sent in selected:
        if len(sent) > 300:
            sent = sent[:300].rsplit(' ', 1)[0] + '…'
        sent = sent[0].upper() + sent[1:]
        bullets.append(f'• {sent}.')

    return '\n'.join(bullets)


def generate_summary(headline: str, text: str, num_bullets: int = 6) -> Optional[str]:
    body = (text or '').strip()
    if not body:
        body = headline

    if len(body.split()) > 800:
        input_text = _lexrank_extract(body, max_tokens=950)
    else:
        input_text = body

    bart_output = _bart_summarize(input_text)

    result = _build_bullets(bart_output, body, headline, num_bullets)

    if result:
        return result

    return _extractive_fallback(headline, body, num_bullets)


def _extractive_fallback(headline: str, text: str, num_bullets: int = 6) -> Optional[str]:
    import math
    from collections import Counter

    STOP = {'the','a','an','and','or','but','in','on','at','to','for','of','with',
            'by','from','is','are','was','were','be','been','has','have','had',
            'this','that','these','those','it','its','as','also','which','who',
            'not','no','so','such','he','she','they','we','their','his','her',
            'said','says','told','according'}

    sentences = _split_sentences(text)
    if not sentences:
        return None

    body_sents = [s for s in sentences if _word_overlap(headline, s) < 0.55]
    if len(body_sents) < 2:
        body_sents = sentences

    all_words = []
    for s in body_sents:
        all_words.extend(w.lower().strip('.,!?;:') for w in s.split()
                         if w.lower().strip('.,!?;:') not in STOP and len(w) > 2)
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
            (tf.get(w.strip('.,!?;:'), 0) / total) *
            math.log((n + 1) / (doc_cnt.get(w.strip('.,!?;:'), 0) + 1))
            for w in words
        ) / len(words)
        ks = sum(1 for t in IMPORTANT if t in sent.lower()) * 0.15
        ns = min(len(NUM_PAT.findall(sent)) * 0.12, 0.35)
        ps = 0.25 if pos == 0 else (0.15 if pos <= n * 0.2 else 0.0)
        lp = 1.0 if len(words) <= 35 else 0.75
        return (ws + ks + ns + ps) * lp

    scored   = sorted(enumerate(body_sents), key=lambda x: score(x[1], x[0]), reverse=True)
    selected: List[str] = []
    for _, sent in scored:
        if len(selected) >= num_bullets:
            break
        sent = sent.strip().rstrip('.')
        if sent.endswith('?'):
            continue
        if len(sent.split()) < 8:
            continue
        if _is_duplicate(sent, selected, threshold=0.35):
            continue
        selected.append(sent)

    order = {s: i for i, s in enumerate(body_sents)}
    selected.sort(key=lambda s: order.get(s, 999))

    if len(selected) < 3:
        return None

    bullets = []
    for sent in selected:
        if len(sent) > 300:
            sent = sent[:300].rsplit(' ', 1)[0] + '…'
        sent = sent[0].upper() + sent[1:]
        bullets.append(f'• {sent}.')

    return '\n'.join(bullets)
