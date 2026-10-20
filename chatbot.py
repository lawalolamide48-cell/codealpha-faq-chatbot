"""
chatbot.py - NLP engine for the FAQ chatbot.

Pipeline
--------
1. Load FAQs (question, keywords, answer) from faqs.json.
2. Pre-process text with NLTK: lowercase, tokenize, remove punctuation and
   stop words, lemmatize.
3. Convert every FAQ to a TF-IDF vector (unigrams + bigrams).
4. For each user message, build its TF-IDF vector and compute the cosine
   similarity against all FAQs.
5. Return the best match if its score passes a confidence threshold,
   otherwise return a polite fallback with suggested questions.

Run `python chatbot.py` to chat with the bot in the terminal.
"""

import json
import random
import re
from pathlib import Path

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import RegexpTokenizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Words that carry meaning in a support context and must not be dropped.
KEEP_WORDS = {"not", "no", "cannot", "free", "out", "back", "after", "before"}

CONFIDENCE_THRESHOLD = 0.20   # minimum score to answer directly
SUGGESTION_THRESHOLD = 0.08   # minimum score to be offered as a suggestion

SMALL_TALK = {
    "greeting": {
        "pattern": r"^(hi|hello|hey|good (morning|afternoon|evening)|howdy)\b",
        "replies": [
            "Hello! I'm the ShopEase assistant. Ask me about orders, shipping, returns, or payments.",
            "Hi there! How can I help you today?",
        ],
    },
    "thanks": {
        "pattern": r"\b(thanks|thank you|thx|cheers)\b",
        "replies": ["You're welcome! Is there anything else I can help with?"],
    },
    "goodbye": {
        "pattern": r"^(bye|goodbye|see you|that'?s all)\b",
        "replies": ["Goodbye! Have a great day."],
    },
}


def _ensure_nltk_data():
    """Download required NLTK corpora on first run."""
    for package, path in (("stopwords", "corpora/stopwords"),
                          ("wordnet", "corpora/wordnet")):
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(package, quiet=True)


class TextPreprocessor:
    """Cleans raw text into a list of normalised tokens."""

    def __init__(self):
        _ensure_nltk_data()
        self.tokenizer = RegexpTokenizer(r"[a-z0-9]+")
        self.stop_words = set(stopwords.words("english")) - KEEP_WORDS
        self.lemmatizer = WordNetLemmatizer()

    def _lemma(self, token):
        try:
            verb = self.lemmatizer.lemmatize(token, pos="v")
            return self.lemmatizer.lemmatize(verb, pos="n")
        except LookupError:  # WordNet unavailable: fall back to the raw token
            return token

    def tokens(self, text):
        text = text.lower()
        text = re.sub(r"https?://\S+", " ", text)
        words = self.tokenizer.tokenize(text)
        return [self._lemma(w) for w in words if w not in self.stop_words]


class FAQChatbot:
    def __init__(self, faq_path):
        self.preprocessor = TextPreprocessor()
        self.faqs = json.loads(Path(faq_path).read_text(encoding="utf-8"))

        # The question is repeated so it outweighs the keywords and answer.
        corpus = [
            f"{f['question']} {f['question']} {f.get('keywords', '')}"
            for f in self.faqs
        ]
        self.vectorizer = TfidfVectorizer(
            tokenizer=self.preprocessor.tokens,
            lowercase=False,
            token_pattern=None,
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self.faq_matrix = self.vectorizer.fit_transform(corpus)

    # ------------------------------------------------------------------ #
    def _small_talk(self, message):
        text = message.lower().strip()
        for intent in SMALL_TALK.values():
            if re.search(intent["pattern"], text):
                return random.choice(intent["replies"])
        return None

    def _rank(self, message):
        """Return (index, score) pairs sorted from best to worst match."""
        if not self.preprocessor.tokens(message):
            return []
        query_vec = self.vectorizer.transform([message])
        scores = cosine_similarity(query_vec, self.faq_matrix).ravel()
        return sorted(enumerate(scores), key=lambda p: p[1], reverse=True)

    # ------------------------------------------------------------------ #
    def get_response(self, message):
        message = (message or "").strip()
        if not message:
            return {"type": "error", "answer": "Please type a question so I can help."}

        small_talk = self._small_talk(message)
        if small_talk:
            return {"type": "small_talk", "answer": small_talk}

        ranked = self._rank(message)
        if ranked and ranked[0][1] >= CONFIDENCE_THRESHOLD:
            idx, score = ranked[0]
            faq = self.faqs[idx]
            return {
                "type": "answer",
                "answer": faq["answer"],
                "matched_question": faq["question"],
                "category": faq["category"],
                "confidence": round(float(score), 2),
            }

        suggestions = [
            self.faqs[i]["question"]
            for i, s in ranked[:3] if s >= SUGGESTION_THRESHOLD
        ]
        return {
            "type": "fallback",
            "answer": ("I couldn't find a confident answer to that. "
                       "Try rephrasing, or contact support at support@shopease.example."),
            "suggestions": suggestions,
        }

    def sample_questions(self, per_category=1):
        """One question per category, used as quick-start chips in the UI."""
        seen, picks = {}, []
        for f in self.faqs:
            if seen.get(f["category"], 0) < per_category:
                seen[f["category"]] = seen.get(f["category"], 0) + 1
                picks.append(f["question"])
        return picks


if __name__ == "__main__":
    bot = FAQChatbot(Path(__file__).with_name("faqs.json"))
    print("ShopEase FAQ Chatbot (type 'quit' to exit)\n")
    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user.lower() in {"quit", "exit"}:
            break
        reply = bot.get_response(user)
        print(f"Bot: {reply['answer']}")
        if reply.get("confidence") is not None:
            print(f"     (matched: {reply['matched_question']} | score {reply['confidence']})")
        for s in reply.get("suggestions", []):
            print(f"     - Did you mean: {s}")
        print()
