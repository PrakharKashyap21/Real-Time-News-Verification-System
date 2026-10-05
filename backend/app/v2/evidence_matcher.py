import re
from enum import Enum
from typing import List, Set, Optional, Dict, Any, Tuple
from pydantic import BaseModel
from backend.app.v2.schemas import (
    ExtractedClaim,
    EvidenceItem,
    EvidenceSourceType,
    StanceType
)


class RelevanceClassification(str, Enum):
    RELEVANT = "RELEVANT"
    IRRELEVANT = "IRRELEVANT"


class EvidenceMatchResult(BaseModel):
    relevance: RelevanceClassification
    stance: StanceType
    token_overlap_count: int = 0
    token_overlap_ratio: float = 0.0
    entity_overlap: List[str] = []
    number_overlap: List[str] = []
    date_overlap: List[str] = []
    negation_mismatch: bool = False
    matching_explanation: str = ""


class EvidenceMatcher:
    """Deterministic, inspectable claim-to-evidence relevance and exact-claim matching engine.

    Ensures fact-check and live news evidence matches the specific claim proposition
    (entities, action/predicate, core objects, and qualifiers) rather than topical overlap.
    """

    STOPWORDS = {
        "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
        "when", "where", "how", "who", "which", "this", "that", "these", "those",
        "then", "just", "so", "than", "such", "both", "through", "about", "into",
        "over", "after", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "can",
        "could", "should", "may", "might", "shall", "must", "to", "from", "up",
        "down", "in", "out", "on", "off", "for", "with", "by", "at", "it", "its",
        "of", "said", "says", "reported", "claims", "according", "also", "did",
        "does", "fact", "check", "report", "news", "viral", "post", "posts",
        "claim", "claims", "statement", "saying", "online", "image", "photo"
    }

    MONTHS_AND_DAYS = {
        "january", "february", "march", "april", "may", "june", "july", "august",
        "september", "october", "november", "december", "jan", "feb", "mar", "apr",
        "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    }

    NEGATION_WORDS = {
        "not", "no", "never", "cannot", "cant", "wont", "dont", "doesnt",
        "didnt", "isnt", "arent", "wasnt", "werent", "untrue", "false", "neither", "nor"
    }

    DEBUNK_MARKERS = {
        "fake", "hoax", "conspiracy", "myth", "debunk", "debunked", "debunks",
        "staged", "fabricate", "fabricated", "falsified", "faked", "rumor",
        "rumour", "untrue", "falsehood", "misleading", "scam"
    }

    ACTION_VERB_GROUPS = [
        {"discover", "discovered", "discovers", "discovery", "find", "found", "finds", "detect", "detected", "uncover", "uncovered", "spot", "spotted"},
        {"land", "landed", "landing", "lands", "touchdown", "touched down"},
        {"ban", "banned", "banning", "bans", "prohibit", "prohibited", "outlaw", "outlawed", "restrict", "restricted"},
        {"approve", "approved", "approves", "approving", "approval", "authorize", "authorized", "clear", "cleared", "pass", "passed"},
        {"declare", "declared", "declares", "declaring", "declaration", "name", "named", "names", "designate", "designated", "announce", "announced"},
        {"sequence", "sequenced", "sequencing", "map", "mapped", "decode", "decoded"},
        {"end", "ended", "ending", "ends", "terminate", "terminated", "conclude", "concluded", "lift", "lifted"},
        {"cure", "cured", "cures", "curing", "treat", "treated", "treats", "heal", "healed"},
        {"create", "created", "creates", "build", "built", "open", "opened"},
        {"spread", "spreads", "spreading", "transmit", "transmits", "transmitting", "transmission", "cause", "caused", "causes", "causing", "emit", "emits", "emitting", "induce", "induces", "inducing", "trigger", "triggers", "triggering"},
        {"infect", "infects", "infecting", "infection", "infections", "contagious", "infectious"},
        {"photograph", "photographed", "photographs", "capture", "captured", "image", "imaged", "picture", "pictured"},
        {"tax", "taxed", "taxes", "taxing", "levy", "levied"},
        {"die", "died", "dies", "kill", "killed", "assassinate", "assassinated"},
        {"win", "won", "wins", "winning"},
        {"acquire", "acquired", "acquires", "buy", "bought", "purchase", "purchased"}
    ]

    ENTITY_ALIASES = {
        "large hadron collider": {"large hadron collider", "lhc", "cern"},
        "lhc": {"large hadron collider", "lhc", "cern"},
        "cern": {"large hadron collider", "lhc", "cern"},
        "who": {"world health organization", "who"},
        "world health organization": {"world health organization", "who"},
        "nasa": {"national aeronautics and space administration", "nasa"},
        "unesco": {"unesco", "united nations educational, scientific and cultural organization"},
        "hgp": {"human genome project", "hgp"},
        "human genome project": {"human genome project", "hgp"},
        "covid": {"covid-19", "covid", "coronavirus", "sars-cov-2"},
        "covid-19": {"covid-19", "covid", "coronavirus", "sars-cov-2"},
        "coronavirus": {"covid-19", "covid", "coronavirus", "sars-cov-2"},
        "sars-cov-2": {"covid-19", "covid", "coronavirus", "sars-cov-2"},
        "apollo 11": {"apollo 11", "apollo xi", "apollo-11"},
        "james webb": {"james webb", "jwst", "webb"},
        "jwst": {"james webb", "jwst", "webb"}
    }

    GENERIC_PROPOSITION_TERMS = {
        "spread", "spreads", "spreading", "transmit", "transmits", "transmission",
        "cause", "causes", "causing", "caused", "infect", "infects", "infection",
        "infections", "infectious", "disease", "diseases", "illness", "illnesses",
        "virus", "viruses", "person", "persons", "people", "human", "humans",
        "study", "studies", "report", "reports", "claim", "claims", "statement",
        "saying", "online", "image", "photo", "world", "day", "days", "year",
        "years", "time", "times", "wave", "second"
    }

    def _extract_tokens(self, text: str) -> List[str]:
        if not text:
            return []
        return re.findall(r"\b[A-Za-z0-9'-]+\b", text)

    def _extract_entities(self, text: str) -> List[str]:
        """Extracts proper nouns, acronyms, known entity phrases, and specific named entities."""
        if not text:
            return []

        text_lower = text.lower()
        res = []
        seen = set()

        # 1. Check known aliases (multi-word and specific key entities first)
        for phrase in sorted(self.ENTITY_ALIASES.keys(), key=lambda x: -len(x)):
            if re.search(rf"\b{re.escape(phrase)}\b", text_lower):
                if phrase not in seen:
                    seen.add(phrase)
                    for w in phrase.split():
                        seen.add(w)
                    if len(phrase) <= 6 and " " not in phrase:
                        res.append(phrase.upper())
                    else:
                        res.append(phrase.title())

        # Collect action verbs and low-info words to exclude from entities
        excluded_words = set(self.STOPWORDS)
        excluded_words.update(self.MONTHS_AND_DAYS)
        for g in self.ACTION_VERB_GROUPS:
            excluded_words.update(g)
        excluded_words.update({
            "vaccine", "vaccines", "contain", "contains", "containing", "injectable", "microchip", "microchips",
            "chemical", "composition", "consists", "consist", "consisting", "water", "molecule", "molecules",
            "car", "cars", "vehicle", "vehicles", "engine", "engines", "combustion", "internal",
            "photo", "photos", "photograph", "photographs", "image", "images", "star", "stars",
            "law", "laws", "emergency", "passed", "passes", "passing", "mandating", "mandate",
            "disinfectant", "disinfectants", "clean", "cleans", "cleaning", "pathogen", "pathogens",
            "cancer", "cures", "curing", "tumor", "tumors", "shark", "sharks", "cartilage",
            "night", "vision", "myopia", "carrots", "eating", "eat", "human", "humans",
            "drinking", "drink", "drinks", "consuming", "consume", "taking", "take", "using", "use",
            "lemon", "lemons", "garlic", "ginger", "salt", "sugar",
            "voting", "machine", "machines", "software", "algorithm", "switched", "millions", "votes", "election",
            "every", "around", "stationary", "enacts", "percent", "major", "all", "hours", "five", "year", "years",
            "study", "proves", "proven", "reported", "reports", "claimed", "claims", "network", "device", "inventor",
            "officially", "declared", "best", "anthem", "world", "revolves", "cause", "transmit", "viral",
            "captures", "deepest", "infrared", "early", "universe", "first", "landed"
        })

        # 2. Extract acronyms & alphanumeric codes (e.g. NASA, EU, WHO, UNESCO, 5G, CRISPR, LHC, COVID-19, UK, US)
        acronyms = re.findall(r"\b[A-Z0-9-]*[A-Z]{2,}[A-Z0-9-]*\b|\b[0-9]+[A-Za-z]+\b|\b[A-Za-z]+[0-9]+\b|\b[A-Za-z]+-[0-9]+\b|\bUK\b|\bUS\b|\bUSA\b|\bEU\b", text)
        for ac in acronyms:
            ac_lower = ac.lower()
            if ac_lower not in seen and ac_lower not in excluded_words and len(ac) > 1:
                seen.add(ac_lower)
                res.append(ac)

        # 3. Generic numbered named entities (e.g. Apollo 11, Voyager 1, Falcon 9, Boeing 737)
        numbered_entities = re.findall(r"\b[A-Z][a-z0-9'-]+\s*(?:-\s*)?\d+\b", text)
        for ne in numbered_entities:
            ne_clean = re.sub(r"\s+", " ", ne).strip().title()
            ne_lower = ne_clean.lower()
            if ne_lower and ne_lower not in seen:
                seen.add(ne_lower)
                for w in ne_lower.split():
                    seen.add(w)
                res.append(ne_clean)

        # 4. Extract capitalized proper nouns if not excluded
        tokens = re.findall(r"\b[A-Z][a-z0-9'-]+\b", text)
        for t in tokens:
            t_lower = t.lower()
            if (
                t_lower not in excluded_words
                and t_lower not in seen
                and len(t) > 1
            ):
                seen.add(t_lower)
                res.append(t)

        return res

    def _extract_numbers(self, text: str) -> List[str]:
        if not text:
            return []
        return re.findall(r"\b\d+(?:\.\d+)?%?\b", text)

    def _extract_dates(self, text: str) -> List[str]:
        if not text:
            return []
        months = r"(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
        dates = re.findall(rf"\b{months}\s+\d{{1,2}}\b|\b\d{{4}}\b", text, flags=re.IGNORECASE)
        return [d.lower() for d in dates]

    def _has_negation(self, text: str) -> bool:
        if not text:
            return False
        tokens = [t.lower() for t in self._extract_tokens(text)]
        for t in tokens:
            if t in self.NEGATION_WORDS or t.endswith("n't"):
                return True
        return False

    def _get_action_group_id(self, word: str) -> Optional[int]:
        w_lower = word.lower()
        for idx, group in enumerate(self.ACTION_VERB_GROUPS):
            if w_lower in group:
                return idx
        return None

    def _get_target_text(self, item: EvidenceItem) -> str:
        """Extracts the most representative claim text from an EvidenceItem."""
        if item.claim_reviewed and item.claim_reviewed.strip():
            return item.claim_reviewed.strip()
        # If claim_reviewed is missing, check snippet for formatted 'Reviewed Claim:' or 'Claim:'
        if item.snippet:
            m = re.search(r"Reviewed Claim:\s*['\"]?(.*?)['\"]?\s*\|\s*Rating:", item.snippet, flags=re.IGNORECASE)
            if m and m.group(1).strip():
                return m.group(1).strip()
            m2 = re.search(r"Reviewed Claim:\s*['\"]?(.*?)['\"]?$", item.snippet, flags=re.IGNORECASE)
            if m2 and m2.group(1).strip():
                return m2.group(1).strip()
            m3 = re.search(r"Claim:\s*['\"]?(.*?)['\"]?\s*\|\s*Rating:", item.snippet, flags=re.IGNORECASE)
            if m3 and m3.group(1).strip():
                return m3.group(1).strip()
            m4 = re.search(r"Claim:\s*['\"]?(.*?)(?:\.\s*Rating:|$)", item.snippet, flags=re.IGNORECASE)
            if m4 and m4.group(1).strip():
                return m4.group(1).strip()
        return f"{item.title or ''} {item.snippet or ''}".strip()

    def _entities_match(self, claim_entities: List[str], target_text: str) -> Tuple[List[str], bool]:
        """Checks if claim entities match in target text directly or through known aliases."""
        if not claim_entities:
            return [], True

        target_lower = target_text.lower()
        matched = []

        for entity in claim_entities:
            e_lower = entity.lower()
            # 1. Direct word or substring match
            if re.search(rf"\b{re.escape(e_lower)}\b", target_lower) or e_lower in target_lower:
                matched.append(entity)
                continue

            # 2. Alias / expansion match
            if e_lower in self.ENTITY_ALIASES:
                aliases = self.ENTITY_ALIASES[e_lower]
                if any(re.search(rf"\b{re.escape(alias)}\b", target_lower) or alias in target_lower for alias in aliases):
                    matched.append(entity)

        is_entity_aligned = len(matched) > 0

        # Protection against adjacent numbered mission entities (e.g. Apollo 11 vs Apollo 9)
        numbered_in_claim = [e for e in claim_entities if any(c.isdigit() for c in e)]
        if numbered_in_claim and is_entity_aligned:
            has_num_match = any(
                any(c.isdigit() for c in m_ent) or any(num in target_lower for num in re.findall(r"\d+", e))
                for m_ent in matched for e in numbered_in_claim
            )
            if not has_num_match:
                is_entity_aligned = False

        return matched, is_entity_aligned

    def match_evidence(self, claim: ExtractedClaim, item: EvidenceItem) -> EvidenceMatchResult:
        """Evaluates whether an evidence item is genuinely relevant to an extracted claim and determines stance.

        Prevents adjacent-claim matches by evaluating entities, action predicates, and core objects.
        """
        if not claim or not claim.text or not item:
            return EvidenceMatchResult(
                relevance=RelevanceClassification.IRRELEVANT,
                stance=StanceType.NEUTRAL,
                matching_explanation="Empty claim or evidence item."
            )

        claim_text = claim.text.strip()
        # For Fact Checks, prioritize claimReviewed (what was reviewed) over general article title
        if item.source_type == EvidenceSourceType.FACT_CHECK_API:
            target_text = self._get_target_text(item)
        else:
            target_text = f"{item.title or ''} {item.snippet or ''}".strip()

        if not target_text:
            return EvidenceMatchResult(
                relevance=RelevanceClassification.IRRELEVANT,
                stance=StanceType.NEUTRAL,
                matching_explanation="No target claim text or title available in evidence item."
            )

        # Tokens
        claim_tokens = [t.lower() for t in self._extract_tokens(claim_text)]
        target_tokens = [t.lower() for t in self._extract_tokens(target_text)]

        # Substantive non-date, non-stopword tokens
        substantive_claim = set(
            t for t in claim_tokens
            if t not in self.STOPWORDS and t not in self.MONTHS_AND_DAYS and not t.isdigit() and len(t) > 2
        )
        substantive_target = set(
            t for t in target_tokens
            if t not in self.STOPWORDS and t not in self.MONTHS_AND_DAYS and not t.isdigit() and len(t) > 2
        )

        token_overlap = substantive_claim.intersection(substantive_target)
        overlap_count = len(token_overlap)
        overlap_ratio = overlap_count / max(len(substantive_claim), 1)

        # Entities
        claim_entities = self._extract_entities(claim_text)
        matched_entities, entity_aligned = self._entities_match(claim_entities, target_text)

        # Numbers
        claim_numbers = self._extract_numbers(claim_text)
        target_numbers_set = set(self._extract_numbers(target_text))
        matched_numbers = [n for n in claim_numbers if n in target_numbers_set]

        # Dates & Years
        claim_dates = self._extract_dates(claim_text)
        target_dates_set = set(self._extract_dates(target_text))
        matched_dates = [d for d in claim_dates if d in target_dates_set]

        claim_years = {d for d in claim_dates if d.isdigit() and len(d) == 4}
        target_years = {d for d in target_dates_set if d.isdigit() and len(d) == 4}
        year_mismatch = (len(claim_years) > 0 and len(target_years) > 0 and claim_years.isdisjoint(target_years))

        # Negations
        claim_negated = self._has_negation(claim_text)
        target_negated = self._has_negation(target_text)
        negation_mismatch = (claim_negated != target_negated)

        # Actions / Predicates
        claim_action_ids = {self._get_action_group_id(t) for t in claim_tokens if self._get_action_group_id(t) is not None}
        target_action_ids = {self._get_action_group_id(t) for t in target_tokens if self._get_action_group_id(t) is not None}
        action_match = len(claim_action_ids.intersection(target_action_ids)) > 0

        # Debunk check in target (fact check reviewing a conspiracy/hoax about the topic)
        has_debunk_marker = any(t in self.DEBUNK_MARKERS for t in target_tokens)

        # Substantive Proposition (Non-Matched-Entity) Terms
        matched_entity_tokens = set()
        for me in matched_entities:
            for word in me.lower().split():
                if len(word) > 1:
                    matched_entity_tokens.add(word)

        matched_action_tokens = set()
        for idx in claim_action_ids.intersection(target_action_ids):
            matched_action_tokens.update(self.ACTION_VERB_GROUPS[idx])

        proposition_terms_claim = substantive_claim - matched_entity_tokens
        proposition_terms_target = substantive_target - matched_entity_tokens
        unmatched_proposition_claim = proposition_terms_claim - matched_action_tokens

        proposition_overlap = proposition_terms_claim.intersection(proposition_terms_target)
        proposition_overlap_count = len(proposition_overlap)

        generic_media_terms = {
            "image", "images", "photo", "photos", "picture", "pictures", "video", "videos",
            "post", "posts", "article", "articles", "report", "reports", "statement", "statements",
            "page", "pages", "front"
        }
        specific_proposition_overlap = proposition_overlap - generic_media_terms - self.GENERIC_PROPOSITION_TERMS
        specific_proposition_overlap_count = len(specific_proposition_overlap)

        # -------------------------------------------------------------
        # 1. DETERMINISTIC RELEVANCE CLASSIFICATION
        # -------------------------------------------------------------
        is_relevant = False
        relevance_reason = ""

        # Temporal Event Guardrail: Explicit distinct year mismatch
        if year_mismatch:
            is_relevant = False
            relevance_reason = f"Rejected: Temporal event mismatch between claim year(s) ({', '.join(claim_years)}) and evidence year(s) ({', '.join(target_years)})."

        elif item.source_type == EvidenceSourceType.FACT_CHECK_API:
            # FACT-CHECK SPECIFIC EXACT-CLAIM / PROPOSITION MATCHING:
            # Identify core known entities in claim (from ENTITY_ALIASES, numbered entities, or acronyms)
            core_known_entities_in_claim = []
            seen_core = set()
            for ent in claim_entities:
                ent_lower = ent.lower()
                # Find canonical group
                canon = ent_lower
                if ent_lower in self.ENTITY_ALIASES:
                    canon = sorted(list(self.ENTITY_ALIASES[ent_lower]))[0]
                if (
                    ent_lower in self.ENTITY_ALIASES
                    or any(c.isdigit() for c in ent)
                    or ent.isupper()
                ):
                    if canon not in seen_core:
                        seen_core.add(canon)
                        core_known_entities_in_claim.append(ent)

            unmatched_core_entities = [
                ent for ent in core_known_entities_in_claim
                if ent not in matched_entities
            ]

            # Specific numbered mission/model entity matched in claim (e.g. Apollo 11, Falcon 9)
            numbered_matched = any(
                bool(re.search(r"\b[A-Z][a-z0-9'-]+\s+\d+\b", m))
                for m in matched_entities
            )

            # 1. If claim entities exist but none matched: reject
            if claim_entities and not entity_aligned:
                is_relevant = False
                relevance_reason = f"Rejected: Claim entities ({', '.join(claim_entities)}) not found in reviewed claim."

            # 2. Multi-core-entity claim where a primary core entity is missing (e.g. 5G in 5G+COVID claim vs COVID-only fact check)
            elif len(core_known_entities_in_claim) >= 2 and len(unmatched_core_entities) >= 1 and not (numbered_matched and action_match):
                is_relevant = False
                relevance_reason = f"Rejected adjacent fact-check: Entity ({', '.join(matched_entities)}) matched, but primary core entity ({', '.join(unmatched_core_entities)}) was absent in reviewed claim."

            # 3. Entity matched, but proposition objects and action predicate are absent
            elif (
                len(core_known_entities_in_claim) <= 1
                and len(unmatched_proposition_claim) >= 2
                and specific_proposition_overlap_count == 0
                and not has_debunk_marker
            ):
                is_relevant = False
                relevance_reason = f"Rejected adjacent fact-check: Entity ({', '.join(matched_entities)}) matched, but claim proposition objects ({', '.join(list(unmatched_proposition_claim)[:3])}) were absent in reviewed claim."

            elif len(unmatched_proposition_claim) >= 2 and specific_proposition_overlap_count == 0 and not action_match:
                is_relevant = False
                relevance_reason = f"Rejected adjacent fact-check: Entity ({', '.join(matched_entities)}) matched, but claim proposition objects ({', '.join(list(unmatched_proposition_claim)[:3])}) and action predicate were absent in reviewed claim."

            # 4. Proposition-aligned matches:
            # Action match + entity alignment
            elif entity_aligned and action_match:
                is_relevant = True
                relevance_reason = f"Matched entities ({', '.join(matched_entities)}) and action predicate."

            # Debunk marker + entity alignment
            elif entity_aligned and has_debunk_marker and (specific_proposition_overlap_count >= 1 or overlap_ratio >= 0.20):
                is_relevant = True
                relevance_reason = f"Aligned claim: Matched entity ({', '.join(matched_entities)}) and debunk marker in reviewed claim."

            # Entity + specific proposition objects
            elif entity_aligned and specific_proposition_overlap_count >= 1:
                is_relevant = True
                relevance_reason = f"Matched entities ({', '.join(matched_entities)}) and object terms ({', '.join(specific_proposition_overlap)})."

            # Claims without core entities but with high substantive token overlap
            elif not claim_entities and overlap_ratio >= 0.35:
                is_relevant = True
                relevance_reason = f"Generic claim match: Substantive overlap {overlap_ratio:.2f}."

            else:
                is_relevant = False
                relevance_reason = f"Rejected: Insufficient claim-specific predicate/object alignment with reviewed claim."

        else:
            # LIVE NEWS & GENERAL REFERENCE SEARCH MATCHING:
            if claim_entities and not entity_aligned and overlap_ratio < 0.50:
                is_relevant = False
                relevance_reason = f"Rejected: Claim entities ({', '.join(claim_entities)}) not found in reference/news."
            elif claim_entities and entity_aligned and len(unmatched_proposition_claim) >= 3 and proposition_overlap_count == 0 and not action_match:
                is_relevant = False
                relevance_reason = f"Rejected topical match: Entity ({', '.join(matched_entities)}) matched, but zero proposition object or action predicate overlap."
            elif entity_aligned and (proposition_overlap_count >= 1 or action_match or overlap_ratio >= 0.25):
                is_relevant = True
                relevance_reason = f"Matched entities ({', '.join(matched_entities)}) and proposition/action reporting terms."
            elif not claim_entities and overlap_ratio >= 0.30:
                is_relevant = True
                relevance_reason = f"Substantive proposition overlap ratio {overlap_ratio:.2f}."
            else:
                is_relevant = False
                relevance_reason = "Insufficient entity or reporting overlap in live news/reference."

        if not is_relevant:
            return EvidenceMatchResult(
                relevance=RelevanceClassification.IRRELEVANT,
                stance=StanceType.NEUTRAL,
                token_overlap_count=overlap_count,
                token_overlap_ratio=round(overlap_ratio, 3),
                entity_overlap=matched_entities,
                number_overlap=matched_numbers,
                date_overlap=matched_dates,
                negation_mismatch=negation_mismatch,
                matching_explanation=relevance_reason
            )

        # -------------------------------------------------------------
        # 2. DETERMINISTIC STANCE DETERMINATION (SUPPORTS / CONTRADICTS / NEUTRAL)
        # -------------------------------------------------------------
        final_stance = StanceType.NEUTRAL
        stance_explanation = ""

        if item.source_type == EvidenceSourceType.FACT_CHECK_API:
            raw_stance = item.stance

            if claim_negated and raw_stance == StanceType.CONTRADICTS:
                final_stance = StanceType.SUPPORTS
                stance_explanation = "Fact check refuted the positive claim, supporting the negated claim."
            elif claim_negated and raw_stance == StanceType.SUPPORTS:
                final_stance = StanceType.CONTRADICTS
                stance_explanation = "Fact check verified positive claim, contradicting the negated claim."
            else:
                final_stance = raw_stance
                stance_explanation = f"Fact check provider rating ({item.raw_rating}) determined stance."

        elif item.source_type == EvidenceSourceType.LIVE_NEWS_SEARCH:
            if negation_mismatch:
                final_stance = StanceType.CONTRADICTS
                stance_explanation = "Negation mismatch between claim and live news article."
            elif action_match and entity_aligned and not claim_negated:
                final_stance = StanceType.SUPPORTS
                stance_explanation = f"Live news reports aligned action and entity."
            else:
                final_stance = StanceType.NEUTRAL
                stance_explanation = "Live news provides reporting context; stance remains neutral."
        elif item.source_type == EvidenceSourceType.GENERAL_REFERENCE:
            final_stance = StanceType.NEUTRAL
            stance_explanation = "General reference provides encyclopedic background context; stance remains neutral."
        else:
            final_stance = StanceType.NEUTRAL
            stance_explanation = "General source context; stance remains neutral."

        return EvidenceMatchResult(
            relevance=RelevanceClassification.RELEVANT,
            stance=final_stance,
            token_overlap_count=overlap_count,
            token_overlap_ratio=round(overlap_ratio, 3),
            entity_overlap=matched_entities,
            number_overlap=matched_numbers,
            date_overlap=matched_dates,
            negation_mismatch=negation_mismatch,
            matching_explanation=f"{relevance_reason} Stance: {final_stance.value} ({stance_explanation})"
        )

    def process_claim_evidence(
        self, claim: ExtractedClaim, evidence_items: List[EvidenceItem]
    ) -> List[EvidenceItem]:
        """Filters out irrelevant evidence items and updates stances for relevant items."""
        if not claim or not evidence_items:
            return []

        processed: List[EvidenceItem] = []

        for item in evidence_items:
            match_res = self.match_evidence(claim, item)
            if match_res.relevance == RelevanceClassification.RELEVANT:
                # Update item stance and relevance score based on matcher evaluation
                item_copy = item.model_copy(update={
                    "stance": match_res.stance,
                    "relevance_score": match_res.token_overlap_ratio
                })
                processed.append(item_copy)

        return processed


_evidence_matcher_instance = None


def get_evidence_matcher() -> EvidenceMatcher:
    global _evidence_matcher_instance
    if _evidence_matcher_instance is None:
        _evidence_matcher_instance = EvidenceMatcher()
    return _evidence_matcher_instance
