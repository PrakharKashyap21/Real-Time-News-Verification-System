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

    DEMONYMS = {
        "indian", "american", "british", "french", "german", "chinese",
        "russian", "japanese", "canadian", "australian", "european", "asian"
    }

    GENERIC_ROLE_DESCRIPTORS = {
        "retailer", "retailers", "company", "companies", "firm", "firms",
        "official", "officials", "quarter", "quarters", "year", "years",
        "month", "months", "study", "studies", "report", "reports", "reported",
        "reporting", "post", "posts", "posted", "statement", "statements",
        "say", "says", "said", "according", "year-on-year", "yoy",
        "period", "periods", "financial", "record", "results", "result"
    }

    def _get_proposition(self, claim: ExtractedClaim):
        if claim and hasattr(claim, "proposition") and claim.proposition:
            return claim.proposition
        from backend.app.v2.evidence_matcher import get_evidence_matcher
        matcher = get_evidence_matcher()
        return matcher.parse_proposition(claim.text if claim and claim.text else "")

    def build_news_primary_query(self, claim: ExtractedClaim) -> str:
        """Constructs a high-recall, compact proposition-driven query for Live News (NewsAPI/GDELT).
        Focuses on: primary subject/entity + core domain object + meaningful predicate.
        Excludes numbers, verbose dates, and generic role/demonym descriptors.
        """
        if not claim or not claim.text:
            return ""

        clean_text = self._clean_scaffolding(claim.text.strip())
        clean_text_lower = clean_text.lower()
        prop = self._get_proposition(claim)

        # 1. Subject extraction (clean named entities, excluding demonyms & generic roles)
        clean_subjects = []
        raw_subjects = prop.subjects if prop and prop.subjects else []
        for s in raw_subjects:
            s_clean = s.strip().rstrip("-")
            s_low = s_clean.lower()
            # Preserve uppercase acronyms (e.g. WHO, NASA, EU, FDA)
            is_acronym = s_clean.isupper() and len(s_clean) >= 2
            if (
                (is_acronym or (s_low not in self.DEMONYMS and s_low not in self.GENERIC_ROLE_DESCRIPTORS and s_low not in self.LOW_INFO_WORDS))
                and not any(m in s_low for m in [
                    "january", "february", "march", "april", "may", "june",
                    "july", "august", "september", "october", "november", "december"
                ])
                and not re.search(r"\b(?:19\d\d|20\d\d)\b", s_clean)
                and len(s_clean) > 1
            ):
                if s_clean not in clean_subjects and not any(s_clean.lower() == cs.lower() for cs in clean_subjects):
                    clean_subjects.append(s_clean)

        # If clean_subjects is empty, extract capitalized proper words
        if not clean_subjects:
            words = re.findall(r"\b[A-Z][a-z0-9'-]+\b", clean_text)
            for w in words:
                w_low = w.lower()
                if (
                    w_low not in self.DEMONYMS
                    and w_low not in self.GENERIC_ROLE_DESCRIPTORS
                    and w_low not in self.LOW_INFO_WORDS
                    and len(w) > 1
                ):
                    clean_subjects.append(w)
                    break

        # 2. Core domain object extraction (excluding numbers, dates, descriptors)
        clean_objects = []
        raw_objects = prop.objects if prop and prop.objects else []
        for obj in raw_objects:
            obj_clean = obj.strip().lower()
            if (
                obj_clean not in self.GENERIC_ROLE_DESCRIPTORS
                and obj_clean not in self.LOW_INFO_WORDS
                and obj_clean not in [cs.lower() for cs in clean_subjects]
                and not obj_clean.isdigit()
                and not any(m in obj_clean for m in [
                    "january", "february", "march", "april", "may", "june",
                    "july", "august", "september", "october", "november", "december",
                    "july-september"
                ])
                and len(obj_clean) > 2
            ):
                clean_objects.append(obj_clean)

        # Sort objects by position of occurrence in text to preserve primary domain focus
        def _obj_pos(o: str) -> int:
            p = clean_text_lower.find(o)
            return p if p != -1 else 9999
        clean_objects = sorted(clean_objects, key=_obj_pos)

        # 3. Meaningful predicate / action extraction
        predicate_word = ""
        ACTION_SEARCH_WORDS = [
            "revenue", "profit", "profits", "merger", "acquired", "acquisition", "landed",
            "landing", "launch", "launched", "spread", "spreading", "discovered",
            "discovery", "won", "awarded", "rise", "rose", "growth", "fall", "dropped",
            "approved", "cleared", "banned", "tested"
        ]
        tokens_low = [t.lower() for t in re.findall(r"\b[A-Za-z0-9'-]+\b", clean_text)]
        for act in ACTION_SEARCH_WORDS:
            if act in tokens_low and act not in [cs.lower() for cs in clean_subjects] and act not in clean_objects:
                predicate_word = act
                break

        # Assemble compact query
        query_terms = []
        # Add up to 2 distinct subjects
        for s in clean_subjects[:2]:
            query_terms.append(s)

        # Add top 1-2 core objects
        for o in clean_objects[:2]:
            if o.lower() not in [t.lower() for t in query_terms]:
                query_terms.append(o)

        # Add predicate word if not already present
        if predicate_word and predicate_word.lower() not in [t.lower() for t in query_terms]:
            query_terms.append(predicate_word)

        # Priority Fallback: If sparse, fall back to high-salience tokens
        if not query_terms:
            substantive = [t for t in re.findall(r"\b[A-Za-z0-9'-]+\b", clean_text) if len(t) > 2 and t.lower() not in self.LOW_INFO_WORDS and not t.isdigit()]
            query_terms = substantive[:3]

        query = " ".join(query_terms[:4])
        if len(query) > 60:
            query = query[:60].rsplit(" ", 1)[0]

        return query.strip()

    def build_news_fallback_query(self, claim: ExtractedClaim) -> str:
        """Constructs a compact secondary fallback query for Live News."""
        primary_q = self.build_news_primary_query(claim)
        tokens = primary_q.split()
        if len(tokens) > 2:
            return " ".join(tokens[:2])
        return primary_q

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

