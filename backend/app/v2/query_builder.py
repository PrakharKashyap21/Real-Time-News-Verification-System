import re
from typing import List, Set, Optional, Dict
from backend.app.v2.schemas import ExtractedClaim, EvidenceItem, StanceType

class FactCheckQueryBuilder:
    """Deterministic query builder and relevance filter for Google Fact Check Search API and NewsAPI."""

    # Reporting Scaffolding to remove from primary queries
    SCAFFOLDING_PATTERNS = [
        r"\baccording to [^,.:]+,?\b",
        r"\bit is reported that\b",
        r"\bit has been reported that\b",
        r"\bit was reported that\b",
        r"\b(medical |scientific |geological |astronomical |historical |investigative |government )?(researchers|scientists|experts|officials|reports|sources|studies|records|documents|agencies|investigators) (said|say|says|stated|announced|announces|warned|warns|warn|claim|claims|claimed|allege|alleges|alleged|show|shows|showed|suggest|suggests|indicate|indicates|indicated|confirmed|confirms|confirm|found|find|finds|discovered|discovers|discover|proves|prove|proved)( that)?\b",
        r"\b(people|users|critics|observers|astronauts) (claim|claims|believe|believes|think|thinks|alleged|claimed|confirm|confirmed|confirms)( that)?\b",
        r"\b(confirmed|confirms|confirm|stated|announced|announces|warned|warns|claimed|claims|declared|declares) that\b",
        r"\b(released|issued) an emergency announcement (predicting|stating|claiming)?( that)?\b",
        r"\bbreaking news:?\b",
        r"\b(unverified|unconfirmed) (assertion|report|claim):?\b",
        r"\ba (photograph|photo|picture|video|image) (purporting to show|circulating on social media showing|showing|of|shows)\b",
        r"\b(viral )?(social media )?(posts|videos|images|claims) (circulating online )?(falsely )?(claimed|allege|alleges|alleged|state|states|stated|suggest|suggests|show|shows|purports to show)( that)?\b",
        r"\b(claims|allegations) that\b",
        r"\b(allegedly|reportedly|supposedly|purportedly)\b",
        r"\b(widely|recently|falsely) (circulated|reported|claimed|shared)\b",
    ]

    # Stopwords to filter out during query refinement (EXCLUDING negation words and numbers)
    LOW_INFO_WORDS = {
        "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
        "when", "where", "how", "who", "which", "this", "that", "these", "those",
        "then", "just", "so", "than", "such", "both", "through", "about", "into",
        "over", "after", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "can",
        "could", "should", "may", "might", "shall", "must", "to", "from", "up",
        "down", "in", "out", "on", "off", "for", "with", "by", "at", "it", "its",
        "of", "said", "says", "reported", "claims", "also", "shows", "confirmed",
        "announcement", "announced", "announces", "officials", "predicting", "investigative",
        "geological", "astronomical", "across", "total", "completely", "better", "drinking",
        "near", "successfully", "around", "within", "without", "between", "among", "via",
        "onto", "upon", "times", "more", "most", "less", "least", "well", "good", "bad",
        "great", "new", "old", "best", "worst", "confirms", "confirming", "proves",
        "proving", "proved", "showing", "showed", "in the world", "world"
    }

    # Negation words MUST BE PRESERVED
    NEGATION_WORDS = {
        "not", "no", "never", "false", "cannot", "cant", "wont", "dont",
        "doesnt", "didnt", "isnt", "arent", "wasnt", "werent", "untrue", "neither", "nor"
    }

    # Known canonical aliases for fallback search diversification
    CANONICAL_ALIASES = {
        "lhc": "Large Hadron Collider",
        "cern": "CERN Large Hadron Collider",
        "jwst": "James Webb Space Telescope",
        "who": "World Health Organization",
        "hgp": "Human Genome Project",
        "unesco": "UNESCO",
        "nasa": "NASA",
        "covid": "COVID-19",
        "covid-19": "COVID-19",
        "isro": "ISRO",
    }

    def _clean_scaffolding(self, text: str) -> str:
        clean = text.strip()
        for pattern in self.SCAFFOLDING_PATTERNS:
            clean = re.sub(pattern, "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def _extract_negations(self, text: str) -> Set[str]:
        words = re.findall(r"\b[A-Za-z']+\b", text.lower())
        return {w for w in words if w in self.NEGATION_WORDS or w.endswith("n't")}

    def build_primary_query(self, claim: ExtractedClaim) -> str:
        """Constructs a deterministic, high-precision primary query string from the claim."""
        if not claim or not claim.text:
            return ""

        raw_text = claim.text.strip()
        # 1. Strip reporting scaffolding
        clean_text = self._clean_scaffolding(raw_text)
        if not clean_text:
            clean_text = raw_text

        # 2. Extract tokens and score salience
        tokens = re.findall(r"\b[A-Za-z0-9'-]+\b", clean_text)
        if not tokens:
            return ""

        substantive = []
        for idx, token in enumerate(tokens):
            t_lower = token.lower()
            if t_lower in self.NEGATION_WORDS or t_lower.endswith("n't"):
                substantive.append((idx, token, 4))
            elif token[0].isupper() or any(char.isdigit() for char in token):
                substantive.append((idx, token, 3))
            elif len(t_lower) > 2 and t_lower not in self.LOW_INFO_WORDS:
                substantive.append((idx, token, 2))

        # If sparse substantive tokens, fall back to clean tokens
        if len(substantive) < 2:
            query_tokens = tokens[:7]
        elif len(substantive) <= 8:
            query_tokens = [item[1] for item in substantive]
        else:
            # Multi-part claim: Select 4 leading head items (entities/subjects) and 4 trailing items (objects/dates/qualifiers)
            head_items = substantive[:4]
            tail_items = substantive[-4:]
            combined = {item[0]: item for item in head_items + tail_items}
            # Also include any intermediate high-priority items (negations/digits)
            for item in substantive[4:-4]:
                if item[2] >= 3:
                    combined[item[0]] = item
            selected_items = sorted(list(combined.values()), key=lambda x: x[0])
            query_tokens = [item[1] for item in selected_items[:8]]

        query = " ".join(query_tokens)

        # Enforce max query length (bounded at 90 chars for search precision)
        if len(query) > 90:
            query = query[:90].rsplit(" ", 1)[0]

        return query.strip()

    def build_fallback_query(self, claim: ExtractedClaim) -> str:
        """Constructs a deterministic secondary/fallback query from core entities and key claim objects."""
        if not claim or not claim.text:
            return ""

        clean_text = self._clean_scaffolding(claim.text.strip())
        tokens = re.findall(r"\b[A-Za-z0-9'-]+\b", clean_text)
        if not tokens:
            return ""

        # Extract entities, negations, numbers, and tail substantive words
        entities = [t for t in tokens if t[0].isupper() or any(c.isdigit() for c in t)]
        substantive = [t for t in tokens if len(t) > 2 and t.lower() not in self.LOW_INFO_WORDS]
        negations = list(self._extract_negations(clean_text))

        # Check for known entity alias expansion if entity acronym is present
        alias_tokens = []
        for ent in entities:
            ent_low = ent.lower()
            if ent_low in self.CANONICAL_ALIASES:
                alias_phrase = self.CANONICAL_ALIASES[ent_low]
                for w in alias_phrase.split():
                    if w.lower() not in [a.lower() for a in alias_tokens]:
                        alias_tokens.append(w)

        tail_words = substantive[-3:] if len(substantive) >= 3 else substantive
        
        fallback_tokens = []
        # Add negations first
        for neg in sorted(negations):
            if neg.lower() not in [t.lower() for t in fallback_tokens]:
                fallback_tokens.append(neg)

        # Add alias tokens or entity tokens
        source_entities = alias_tokens if alias_tokens else entities
        for ent in source_entities[:3]:
            if ent.lower() not in [t.lower() for t in fallback_tokens]:
                fallback_tokens.append(ent)

        # Add tail object words
        for w in tail_words:
            if w.lower() not in [t.lower() for t in fallback_tokens]:
                fallback_tokens.append(w)

        query = " ".join(fallback_tokens[:6])
        if len(query) > 80:
            query = query[:80].rsplit(" ", 1)[0]

        return query.strip()

    def filter_relevant_evidence(
        self, claim: ExtractedClaim, evidence_items: List[EvidenceItem]
    ) -> List[EvidenceItem]:
        """Applies deterministic relevance filtering on retrieved evidence items."""
        if not claim or not evidence_items:
            return []

        # Use EvidenceMatcher to perform exact claim and entity+predicate+object relevance filtering
        from backend.app.v2.evidence_matcher import get_evidence_matcher, RelevanceClassification
        matcher = get_evidence_matcher()

        filtered_items: List[EvidenceItem] = []
        for item in evidence_items:
            match_res = matcher.match_evidence(claim, item)
            if match_res.relevance == RelevanceClassification.RELEVANT:
                # Update item with matched stance and relevance score
                item_copy = item.model_copy(update={
                    "stance": match_res.stance,
                    "relevance_score": match_res.token_overlap_ratio
                })
                filtered_items.append(item_copy)

        return filtered_items


_query_builder_instance = None

def get_query_builder() -> FactCheckQueryBuilder:
    global _query_builder_instance
    if _query_builder_instance is None:
        _query_builder_instance = FactCheckQueryBuilder()
    return _query_builder_instance

