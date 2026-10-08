import re
from enum import Enum
from typing import List, Set, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
from backend.app.v2.schemas import (
    ExtractedClaim,
    EvidenceItem,
    EvidenceSourceType,
    StanceType,
    ClaimProposition
)


class RelevanceClassification(str, Enum):
    RELEVANT = "RELEVANT"
    IRRELEVANT = "IRRELEVANT"


class EvidenceMatchResult(BaseModel):
    relevance: RelevanceClassification
    stance: StanceType
    claim_proposition: Optional[ClaimProposition] = None
    evidence_proposition: Optional[ClaimProposition] = None
    subject_match: bool = False
    predicate_match: bool = False
    object_match: bool = False
    numeric_match: bool = True
    temporal_match: bool = True
    negation_conflict: bool = False
    object_conflict: bool = False
    numeric_conflict: bool = False
    modality_conflict: bool = False
    strong_direct_match: bool = False
    token_overlap_count: int = 0
    token_overlap_ratio: float = 0.0
    entity_overlap: List[str] = Field(default_factory=list)
    number_overlap: List[str] = Field(default_factory=list)
    date_overlap: List[str] = Field(default_factory=list)
    action_match: bool = False
    specific_proposition_overlap_count: int = 0
    negation_mismatch: bool = False
    matching_explanation: str = ""
    diagnostic: Dict[str, Any] = Field(default_factory=dict)
    proposition_diagnostic: Dict[str, Any] = Field(default_factory=dict)


class EvidenceMatcher:
    """Structured-proposition alignment and deterministic claim-to-evidence matching engine.

    Extracts canonical (Subject, Predicate, Object, Numeric, Temporal, Negation, Modality)
    proposition representations and performs structural alignment and conflict detection
    prior to NLI semantic verification.
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
        "claim", "claims", "statement", "saying", "online", "image", "photo",
        "regarding", "concerning", "during", "their", "they", "them", "his", "her"
    }

    MONTHS_AND_DAYS = {
        "january", "february", "march", "april", "may", "june", "july", "august",
        "september", "october", "november", "december", "jan", "feb", "mar", "apr",
        "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "q1", "q2", "q3", "q4"
    }

    NEGATION_WORDS = {
        "not", "no", "never", "cannot", "cant", "wont", "dont", "doesnt",
        "didnt", "isnt", "arent", "wasnt", "werent", "untrue", "false", "neither",
        "nor", "denied", "denies", "deny", "refuted", "refutes", "refute", "debunked",
        "debunks", "debunk", "myth", "hoax", "falsehood", "misleading"
    }

    DEBUNK_MARKERS = {
        "fake", "hoax", "conspiracy", "myth", "debunk", "debunked", "debunks",
        "staged", "fabricate", "fabricated", "falsified", "faked", "rumor",
        "rumour", "untrue", "falsehood", "misleading", "scam"
    }

    # Semantic predicate classes mapping common verb variations to canonical root concepts
    PREDICATE_CLASSES = {
        "REPORT": {
            "report", "reports", "reported", "reporting", "post", "posted", "posts", "posting",
            "state", "stated", "states", "stating", "record", "recorded", "records", "recording",
            "announce", "announced", "announces", "announcing", "publish", "published", "release",
            "released", "disclose", "disclosed", "confirm", "confirmed"
        },
        "GROW_RISE": {
            "rise", "rises", "rose", "risen", "rising", "grow", "grows", "grew", "grown",
            "growth", "growing", "surge", "surged", "surges", "surging", "gain", "gained",
            "gains", "jump", "jumped", "jumps", "increase", "increased", "increases",
            "increasing", "climb", "climbed", "climbs"
        },
        "DROP_FALL": {
            "drop", "drops", "dropped", "dropping", "fall", "falls", "fell", "fallen",
            "falling", "decline", "declined", "declines", "declining", "plunge", "plunged",
            "plunges", "decrease", "decreased", "decreases", "slump", "slumped", "shrink"
        },
        "AWARD_WIN": {
            "win", "wins", "won", "winning", "award", "awards", "awarded", "awarding",
            "receive", "receives", "received", "receiving", "honor", "honored", "honors",
            "honoring", "recognize", "recognized", "recognizes", "recognition", "named",
            "bestow", "bestowed"
        },
        "ACQUIRE_BUY": {
            "acquire", "acquires", "acquired", "acquiring", "acquisition", "buy", "buys",
            "bought", "buying", "purchase", "purchased", "purchasing", "takeover", "merge",
            "merged", "merger"
        },
        "DISCOVER_FIND": {
            "discover", "discovers", "discovered", "discovering", "discovery", "discoveries",
            "find", "finds", "found", "finding", "detect", "detected", "detecting", "detection",
            "uncover", "uncovered", "uncovering", "spot", "spotted", "spotting", "observe",
            "observed", "capture", "captured"
        },
        "SPREAD_TRANSMIT": {
            "spread", "spreads", "spreading", "transmit", "transmits", "transmitted",
            "transmitting", "transmission", "cause", "causes", "caused", "causing",
            "emit", "emits", "emitted", "emitting", "induce", "induces", "induced",
            "inducing", "trigger", "triggers", "triggered", "triggering", "link",
            "linked", "linking", "originate", "originates"
        },
        "INFECT": {
            "infect", "infects", "infected", "infecting", "infection", "infections",
            "contagious", "infectious", "contract", "contracted", "catch"
        },
        "APPROVE_CLEAR": {
            "approve", "approved", "approves", "approving", "approval", "authorize",
            "authorized", "authorizes", "authorizing", "clear", "cleared", "clears",
            "pass", "passed", "passes", "passing", "sanction", "sanctioned", "endorse", "endorsed"
        },
        "BAN_RESTRICT": {
            "ban", "banned", "bans", "banning", "prohibit", "prohibited", "prohibits",
            "outlaw", "outlawed", "outlaws", "restrict", "restricted", "restricts",
            "block", "blocked", "blocks", "halt", "halted", "halts"
        },
        "LAND": {
            "land", "lands", "landed", "landing", "touchdown", "touched down"
        },
        "LAUNCH_UNVEIL": {
            "launch", "launches", "launched", "launching", "unveil", "unveiled", "unveils",
            "unveiling", "introduce", "introduced", "introduces", "introducing", "rollout"
        },
        "CURE_TREAT": {
            "cure", "cures", "cured", "curing", "treat", "treats", "treated", "treating",
            "treatment", "heal", "heals", "healed", "healing", "prevent", "prevents", "preventing"
        },
        "DIE_KILL": {
            "die", "dies", "died", "dying", "kill", "kills", "killed", "killing",
            "assassinate", "assassinated", "dead", "fatal", "fatalities"
        },
        "CONTAIN_CONSIST": {
            "contain", "contains", "contained", "containing", "consist", "consists",
            "consisted", "consisting", "comprise", "comprises", "include", "includes",
            "composed", "composition"
        },
        "DECLARE_DESIGNATE": {
            "declare", "declared", "declares", "declaring", "declaration", "designate",
            "designated", "designating", "name", "named", "names"
        }
    }

    # Entity aliases for canonical cross-reference
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

    GENERIC_TERMS = {
        "spread", "spreads", "spreading", "transmit", "transmits", "transmission",
        "cause", "causes", "causing", "caused", "infect", "infects", "infection",
        "infections", "infectious", "disease", "diseases", "illness", "illnesses",
        "virus", "viruses", "person", "persons", "people", "human", "humans",
        "study", "studies", "report", "reports", "reported", "reporting",
        "claim", "claims", "claimed", "statement", "saying", "online", "image",
        "photo", "photos", "world", "day", "days", "year", "years", "time",
        "times", "wave", "second", "news", "article", "articles", "press",
        "media", "post", "posts", "update", "updates", "story", "stories",
        "dr", "mr", "mrs", "ms", "first", "latest", "new", "discovery", "discoveries",
        "discover", "discovered", "discovers", "find", "finds", "found",
        "official", "officials", "officially", "announced", "announces", "announcement",
        "result", "results", "firm", "company", "quarter",
        "astronaut", "astronauts", "retailer", "retailers", "minister", "president",
        "scientist", "scientists", "agency", "mission", "missions",
        "billion", "million", "trillion", "thousand", "hundred", "percent", "percentage"
    }

    FUTURE_INTENT_MODALITY_TRIGGERS = [
        r"\bplans?\s+to\b", r"\bplanning\s+to\b", r"\baims?\s+to\b", r"\bproposes?\s+to\b",
        r"\bconsidering\b", r"\bscheduled\s+to\b", r"\bexpected\s+to\b", r"\bintends?\s+to\b",
        r"\bupcoming\b", r"\bwill\s+(?:acquire|buy|launch|build|open|merge)\b"
    ]

    # -------------------------------------------------------------
    # 1. STRUCTURED PROPOSITION PARSING
    # -------------------------------------------------------------
    def _extract_tokens(self, text: str) -> List[str]:
        if not text:
            return []
        return re.findall(r"\b[A-Za-z0-9'-]+\b", text)

    def _extract_entities(self, text: str) -> List[str]:
        """Extracts proper nouns, multi-word entities, acronyms, and alphanumeric names in text order."""
        if not text:
            return []

        text_lower = text.lower()
        res = []
        seen = set()

        # Exclusions for entity parsing
        excluded = set(self.STOPWORDS)
        excluded.update(self.MONTHS_AND_DAYS)
        for class_words in self.PREDICATE_CLASSES.values():
            excluded.update(class_words)
        excluded.update(self.GENERIC_TERMS)

        # 1. Known alias phrases
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

        # 2. Numbered named entities (e.g. Apollo 11, Falcon 9, Boeing 737)
        numbered = re.findall(r"\b[A-Z][a-z0-9'-]+\s*(?:-\s*)?\d+\b", text)
        for ne in numbered:
            clean = re.sub(r"\s+", " ", ne).strip().title()
            c_low = clean.lower()
            if (
                any(m in c_low.split() for m in self.MONTHS_AND_DAYS)
                or re.search(r"\b(?:19\d\d|20\d\d)\b", c_low)
            ):
                continue
            if c_low not in seen:
                seen.add(c_low)
                for w in c_low.split():
                    seen.add(w)
                res.append(clean)

        # 3. Capitalized multi-token phrases (split across verbs/predicates)
        all_pred_words = set()
        for class_words in self.PREDICATE_CLASSES.values():
            all_pred_words.update(class_words)

        capitalized_phrases = re.findall(r"\b[A-Z][a-zA-Z0-9'-]*(?:\s+[A-Z][a-zA-Z0-9'-]*)+\b", text)
        for cp in capitalized_phrases:
            words = cp.split()
            chunks = []
            curr_chunk = []
            for w in words:
                if w.lower() in all_pred_words or w.lower() in self.STOPWORDS:
                    if curr_chunk:
                        chunks.append(" ".join(curr_chunk))
                        curr_chunk = []
                else:
                    curr_chunk.append(w)
            if curr_chunk:
                chunks.append(" ".join(curr_chunk))

            for chunk in chunks:
                cp_clean = chunk.strip()
                cp_low = cp_clean.lower()
                if (
                    cp_low not in seen
                    and len(cp_clean) > 3
                    and cp_low not in excluded
                    and not any(w in self.MONTHS_AND_DAYS for w in cp_low.split())
                    and not re.search(r"\b(?:19\d\d|20\d\d)\b", cp_clean)
                ):
                    seen.add(cp_low)
                    for w in cp_low.split():
                        seen.add(w)
                    res.append(cp_clean)

        # 4. Acronyms & codes (NASA, EU, WHO, 5G, CRISPR, LHC, COVID-19, UK, US)
        acronyms = re.findall(r"\b[A-Z0-9-]*[A-Z]{2,}[A-Z0-9-]*\b|\b[0-9]+[A-Za-z]+\b|\b[A-Za-z]+[0-9]+\b|\b[A-Za-z]+-[0-9]+\b|\bUK\b|\bUS\b|\bUSA\b|\bEU\b", text)
        for ac in acronyms:
            ac_low = ac.lower()
            if ac_low not in seen and ac_low not in excluded and len(ac) > 1 and ac_low not in self.MONTHS_AND_DAYS:
                seen.add(ac_low)
                res.append(ac)

        # 5. Individual capitalized nouns
        single_caps = re.findall(r"\b[A-Z][a-z0-9'-]+\b", text)
        for sc in single_caps:
            sc_low = sc.lower()
            if (
                sc_low not in seen
                and sc_low not in excluded
                and len(sc) > 1
                and sc_low not in self.MONTHS_AND_DAYS
                and not sc.isdigit()
            ):
                seen.add(sc_low)
                res.append(sc)

        # Sort entities by their first occurrence position in text to preserve syntactic role (subject first)
        def _get_pos(entity: str) -> int:
            p = text_lower.find(entity.lower())
            return p if p != -1 else 9999

        return sorted(res, key=_get_pos)

    def _extract_numeric_constraints(self, text: str) -> List[str]:
        """Extracts and normalizes numbers, percentages, and dollar amounts."""
        if not text:
            return []

        constraints = []
        # Percentages: 23% or 23 percent
        pcts = re.findall(r"\b(\d+(?:\.\d+)?)\s*(?:%|percent|percentage)\b", text, flags=re.IGNORECASE)
        for p in pcts:
            constraints.append(f"{p}%")

        # Currency amounts: $5 billion, $5M, $100
        currencies = re.findall(r"\$\s*\d+(?:\.\d+)?(?:\s*(?:billion|million|trillion|k|m|b))?\b", text, flags=re.IGNORECASE)
        for c in currencies:
            constraints.append(re.sub(r"\s+", "", c.lower()))

        # Non-year quantities with commas or decimals (excluding 4-digit years like 2026)
        raw_nums = re.findall(r"\b\d+(?:,\d+)*(?:\.\d+)?\b", text)
        for n in raw_nums:
            clean_n = n.replace(",", "")
            if len(clean_n) == 4 and clean_n.isdigit() and (clean_n.startswith("19") or clean_n.startswith("20")):
                continue
            if clean_n not in [c.rstrip("%") for c in constraints]:
                constraints.append(clean_n)

        return sorted(list(set(constraints)))

    def _extract_temporal_constraints(self, text: str) -> List[str]:
        """Extracts explicit years and calendar constraints."""
        if not text:
            return []
        months = r"(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"
        dates = re.findall(rf"\b{months}\s*(?:-\s*{months})?\s*(?:\d{{1,2}})?\s*(?:\d{{4}})?\b|\b\d{{4}}\b|\b(?:q1|q2|q3|q4)\b", text, flags=re.IGNORECASE)
        clean = [re.sub(r"\s+", " ", d).strip().lower() for d in dates if d.strip()]
        return sorted(list(set(clean)))

    def _has_negation(self, text: str) -> bool:
        """Determines if text contains explicit denial or negation."""
        if not text:
            return False
        tokens = [t.lower() for t in self._extract_tokens(text)]
        return any(t in self.NEGATION_WORDS or t.endswith("n't") for t in tokens)

    def _detect_modality(self, text: str) -> str:
        """Detects whether text expresses completed factual assertions or future/intent modality."""
        if not text:
            return "completed"
        text_lower = text.lower()
        for trigger in self.FUTURE_INTENT_MODALITY_TRIGGERS:
            if re.search(trigger, text_lower):
                return "future_intent"
        return "completed"

    def _extract_predicates(self, text: str) -> List[str]:
        """Maps verbs and relational predicates to canonical semantic action classes."""
        if not text:
            return []
        tokens = [t.lower() for t in self._extract_tokens(text)]
        detected = []
        for class_name, word_set in self.PREDICATE_CLASSES.items():
            if any(t in word_set for t in tokens):
                detected.append(class_name)
        return detected

    def parse_proposition(self, text: str) -> ClaimProposition:
        """Deterministically extracts a structured ClaimProposition representation from text."""
        if not text:
            return ClaimProposition()

        clean_text = text.strip()
        subjects = self._extract_entities(clean_text)
        predicates = self._extract_predicates(clean_text)
        numbers = self._extract_numeric_constraints(clean_text)
        temporals = self._extract_temporal_constraints(clean_text)
        negated = self._has_negation(clean_text)
        modality = self._detect_modality(clean_text)

        # Extract substantive domain objects (non-subject, non-action, non-generic terms)
        tokens = [t.lower() for t in self._extract_tokens(clean_text)]
        substantive = set()
        subject_tokens = {w.lower() for s in subjects for w in s.split()}
        predicate_tokens = set()
        for p in predicates:
            predicate_tokens.update(self.PREDICATE_CLASSES.get(p, set()))

        for t in tokens:
            if (
                t not in self.STOPWORDS
                and t not in self.MONTHS_AND_DAYS
                and t not in subject_tokens
                and t not in predicate_tokens
                and t not in self.GENERIC_TERMS
                and not t.isdigit()
                and len(t) > 2
            ):
                substantive.add(t)

        return ClaimProposition(
            subjects=subjects,
            predicates=predicates,
            objects=sorted(list(substantive)),
            numeric_constraints=numbers,
            temporal_constraints=temporals,
            negated=negated,
            modality=modality,
            raw_text=clean_text
        )

    # -------------------------------------------------------------
    # 2. TARGET TEXT EXTRACTION
    # -------------------------------------------------------------
    def _get_target_text(self, item: EvidenceItem) -> str:
        """Extracts the focused proposition passage from an EvidenceItem."""
        if item.source_type == EvidenceSourceType.FACT_CHECK_API:
            if item.claim_reviewed and item.claim_reviewed.strip():
                return item.claim_reviewed.strip()
            if item.snippet:
                m = re.search(r"Reviewed Claim:\s*['\"]?(.*?)['\"]?\s*\|\s*Rating:", item.snippet, flags=re.IGNORECASE)
                if m and m.group(1).strip():
                    return m.group(1).strip()
            return f"{item.title or ''} {item.snippet or ''}".strip()
        else:
            parts = []
            if item.title:
                parts.append(item.title.strip())
            if item.snippet and item.snippet.strip() and item.snippet.strip().lower() != (item.title or "").strip().lower():
                parts.append(item.snippet.strip())
            if item.content and item.content.strip():
                parts.append(item.content.strip())
            return " ".join(parts).strip()

    # -------------------------------------------------------------
    # 3. STRUCTURAL PROPOSITION COMPATIBILITY GATE
    # -------------------------------------------------------------
    def match_evidence(self, claim: ExtractedClaim, item: EvidenceItem) -> EvidenceMatchResult:
        """Evaluates whether an evidence item structurally aligns with or contradicts a claim proposition."""
        if not claim or not claim.text or not item:
            return EvidenceMatchResult(
                relevance=RelevanceClassification.IRRELEVANT,
                stance=StanceType.NEUTRAL,
                matching_explanation="Empty claim or evidence item."
            )

        claim_prop = self.parse_proposition(claim.text)
        target_text = self._get_target_text(item)

        if not target_text:
            return EvidenceMatchResult(
                relevance=RelevanceClassification.IRRELEVANT,
                stance=StanceType.NEUTRAL,
                claim_proposition=claim_prop,
                matching_explanation="No target proposition text available in evidence item."
            )

        evidence_prop = self.parse_proposition(target_text)
        target_text_lower = target_text.lower()

        # --- A. Subject Alignment ---
        matched_subjects = []
        for s in claim_prop.subjects:
            s_low = s.lower()
            # Direct match
            if s_low in target_text_lower or re.search(rf"\b{re.escape(s_low)}\b", target_text_lower):
                matched_subjects.append(s)
            # Alias match
            elif s_low in self.ENTITY_ALIASES:
                aliases = self.ENTITY_ALIASES[s_low]
                if any(a in target_text_lower or re.search(rf"\b{re.escape(a)}\b", target_text_lower) for a in aliases):
                    matched_subjects.append(s)
            else:
                # Check for significant tokens (e.g. "5G" in "5G Radio Frequency Towers", "Apollo 11" in "Apollo 11 mission")
                sub_tokens = [w for w in self._extract_tokens(s) if w.lower() not in self.STOPWORDS and len(w) > 1]
                if sub_tokens:
                    # If numbered entity exists in s (e.g. Apollo 11), requires exact numbered token
                    has_num_token = [w for w in sub_tokens if any(c.isdigit() for c in w)]
                    if has_num_token:
                        if all(re.search(rf"\b{re.escape(nt.lower())}\b", target_text_lower) for nt in has_num_token):
                            matched_subjects.append(s)
                    # Acronym or uppercase entity (e.g. 5G, COVID, NASA, LHC, CRISPR)
                    elif any(w.isupper() and len(w) >= 2 and re.search(rf"\b{re.escape(w.lower())}\b", target_text_lower) for w in sub_tokens):
                        matched_subjects.append(s)
                    # Multi-word proper name (e.g. Company Beta, Karl Deisseroth) requires ALL substantive tokens
                    elif all(re.search(rf"\b{re.escape(w.lower())}\b", target_text_lower) for w in sub_tokens if w.lower() not in self.GENERIC_TERMS):
                        matched_subjects.append(s)

        # Numbered mission protection (e.g. Apollo 11 vs Apollo 9)
        numbered_missions = [s for s in claim_prop.subjects if re.match(r"^[A-Z][a-z]+\s*\d+$", s)]
        for s in numbered_missions:
            nums = re.findall(r"\d+", s)
            for n in nums:
                # If target has a conflicting number for the same entity word prefix
                prefix = re.sub(r"\d+", "", s).strip().lower()
                if prefix:
                    m_other = re.findall(rf"\b{re.escape(prefix)}\s*(\d+)\b", target_text_lower)
                    if m_other and n not in m_other:
                        matched_subjects = [ms for ms in matched_subjects if ms != s]

        primary_subject = claim_prop.subjects[0] if claim_prop.subjects else None
        # All entities required if multiple entities in claim (e.g. Company Alpha acquired Company Beta)
        if len(claim_prop.subjects) >= 2:
            subject_match = bool(
                len(matched_subjects) == len(claim_prop.subjects)
                or (
                    bool(numbered_missions)
                    and any(s in matched_subjects for s in numbered_missions)
                    and len(matched_subjects) >= len(claim_prop.subjects) - 1
                )
            )
        else:
            subject_match = bool(primary_subject in matched_subjects) if primary_subject else True

        partial_subject_match = bool(len(matched_subjects) > 0) if claim_prop.subjects else True

        # --- B. Predicate Compatibility ---
        common_predicates = set(claim_prop.predicates).intersection(set(evidence_prop.predicates))
        predicate_match = len(common_predicates) > 0 if claim_prop.predicates else True

        # --- C. Object Alignment & Conflict Detection ---
        claim_objects = set(claim_prop.objects)
        evidence_objects = set(evidence_prop.objects)
        common_objects = claim_objects.intersection(evidence_objects)
        object_match = len(common_objects) > 0

        # Object Conflict: Claim specifies a core domain object (e.g. CRISPR), but evidence specifies alternative domain objects (e.g. optogenetics)
        # Note: Only applies to Live News reporting and Fact Checks, NOT general reference encyclopedia background.
        object_conflict = False
        if (
            item.source_type != EvidenceSourceType.GENERAL_REFERENCE
            and len(claim_objects) >= 1
            and len(common_objects) == 0
            and len(evidence_objects) >= 1
            and subject_match
            and predicate_match
        ):
            object_conflict = True

        # --- D. Numeric Alignment & Conflict Detection ---
        numeric_match = True
        numeric_conflict = False
        if claim_prop.numeric_constraints:
            for nc in claim_prop.numeric_constraints:
                clean_nc = nc.lower().rstrip("%")
                # Check direct or percent representation in evidence
                if not (nc.lower() in target_text_lower or re.search(rf"\b{re.escape(clean_nc)}\s*(?:%|percent)?\b", target_text_lower)):
                    numeric_match = False
                    if evidence_prop.numeric_constraints:
                        numeric_conflict = True
                    break

        # --- E. Temporal Alignment & Modality ---
        temporal_match = True
        claim_years = set(re.findall(r"\b(19\d\d|20\d\d)\b", " ".join(claim_prop.temporal_constraints)))
        evidence_years = set(re.findall(r"\b(19\d\d|20\d\d)\b", " ".join(evidence_prop.temporal_constraints)))
        year_mismatch = (len(claim_years) > 0 and len(evidence_years) > 0 and claim_years.isdisjoint(evidence_years))

        if year_mismatch:
            temporal_match = False

        modality_conflict = (claim_prop.modality == "completed" and evidence_prop.modality == "future_intent")

        # --- F. Token Extraction & Overlap ---
        claim_tokens = [t.lower() for t in self._extract_tokens(claim.text)]
        target_tokens = [t.lower() for t in self._extract_tokens(target_text)]
        substantive_claim = set(t for t in claim_tokens if t not in self.STOPWORDS and t not in self.MONTHS_AND_DAYS and len(t) > 2)
        substantive_target = set(t for t in target_tokens if t not in self.STOPWORDS and t not in self.MONTHS_AND_DAYS and len(t) > 2)
        token_overlap = substantive_claim.intersection(substantive_target)
        overlap_count = len(token_overlap)
        overlap_ratio = overlap_count / max(len(substantive_claim), 1)

        # --- G. Negation Conflict ---
        negation_conflict = False
        effective_raw_rating = item.raw_rating
        if not effective_raw_rating and item.snippet:
            m_rating = re.search(r"\bRating:\s*([A-Za-z0-9 -]+)", item.snippet, flags=re.IGNORECASE)
            if m_rating:
                effective_raw_rating = m_rating.group(1).strip()

        if item.source_type == EvidenceSourceType.FACT_CHECK_API:
            # Fact check rating determines polarity against reviewed claim
            if effective_raw_rating:
                from backend.app.v2.fact_check_retriever import determine_stance
                fc_stance = determine_stance(effective_raw_rating)
                is_debunk_claim = any(t in self.DEBUNK_MARKERS for t in target_tokens)
                if fc_stance == StanceType.CONTRADICTS and not is_debunk_claim and not claim_prop.negated:
                    negation_conflict = True
                elif fc_stance == StanceType.SUPPORTS and claim_prop.negated:
                    negation_conflict = True
        else:
            if claim_prop.negated != evidence_prop.negated:
                negation_conflict = True

        # --- H. Relevance Gate ---
        is_relevant = False
        relevance_reason = ""

        if not temporal_match:
            is_relevant = False
            relevance_reason = "Rejected adjacent fact-check / evidence: Incompatible Temporal constraint."

        # If claim has numbered mission entities (e.g. Apollo 11), evidence MUST match the numbered entity
        elif numbered_missions and not any(s in matched_subjects for s in numbered_missions):
            is_relevant = False
            relevance_reason = f"Rejected adjacent fact-check / evidence: Core numbered entity ({', '.join(numbered_missions)}) mismatch."

        elif item.source_type == EvidenceSourceType.FACT_CHECK_API:
            if claim_prop.subjects:
                primary_matched = (
                    (primary_subject in matched_subjects)
                    or (bool(numbered_missions) and any(s in matched_subjects for s in numbered_missions))
                ) if primary_subject else False

                if not primary_matched:
                    is_relevant = False
                    relevance_reason = f"Rejected adjacent fact-check: Primary subject ({primary_subject}) absent in reviewed claim."
                elif len(claim_prop.subjects) >= 2 and len(matched_subjects) < 2 and not any(t in self.DEBUNK_MARKERS for t in target_tokens) and not (bool(numbered_missions) and any(s in matched_subjects for s in numbered_missions)):
                    is_relevant = False
                    relevance_reason = f"Rejected adjacent fact-check: Secondary subjects ({', '.join(claim_prop.subjects[1:])}) absent in reviewed claim."
                elif predicate_match or object_match or (not claim_prop.predicates and not claim_objects and overlap_ratio >= 0.25):
                    is_relevant = True
                    relevance_reason = f"Aligned fact-check: Matched subjects ({', '.join(matched_subjects)}) and proposition."
                elif any(t in self.DEBUNK_MARKERS for t in target_tokens) and overlap_ratio >= 0.30:
                    is_relevant = True
                    relevance_reason = f"Aligned debunk fact-check: Matched subjects ({', '.join(matched_subjects)}) and debunk markers."
                else:
                    is_relevant = False
                    relevance_reason = "Rejected adjacent fact-check: Insufficient proposition alignment with reviewed claim."
            elif overlap_ratio >= 0.35:
                is_relevant = True
                relevance_reason = "Generic claim substantive overlap."
            else:
                is_relevant = False
                relevance_reason = "Rejected adjacent fact-check: Insufficient proposition alignment with reviewed claim."

        else:
            # Live News & Reference
            if claim_prop.subjects and not partial_subject_match and overlap_ratio < 0.50:
                is_relevant = False
                relevance_reason = f"Rejected news/ref: Subject ({', '.join(claim_prop.subjects)}) not found."
            elif (claim_prop.predicates or claim_prop.objects) and not predicate_match and not object_match:
                # Entity matched but predicate/action and objects are completely absent (e.g. JWST discovery vs launch)
                is_relevant = False
                relevance_reason = "Rejected news/ref: Unrelated predicate action despite subject presence."
            elif partial_subject_match and (predicate_match or object_match or overlap_ratio >= 0.25):
                is_relevant = True
                relevance_reason = f"Matched subjects ({', '.join(matched_subjects)}) and reporting terms."
            elif not claim_prop.subjects and overlap_ratio >= 0.30:
                is_relevant = True
                relevance_reason = "Substantive proposition overlap."
            else:
                is_relevant = False
                relevance_reason = "Insufficient reporting overlap in live news/reference."

        # --- I. Proposition Compatibility & Strong Direct Match ---
        proposition_compatible = (
            subject_match
            and (predicate_match or object_match or (not claim_prop.predicates and not claim_objects))
            and not object_conflict
            and not numeric_conflict
            and not modality_conflict
            and not negation_conflict
            and temporal_match
        )

        strong_direct_match = False
        if is_relevant:
            if (
                subject_match
                and (predicate_match or (not claim_prop.predicates and not claim_objects))
                and (object_match or not claim_objects)
                and numeric_match
                and temporal_match
                and not negation_conflict
                and not object_conflict
                and not numeric_conflict
                and not modality_conflict
            ):
                strong_direct_match = True

        # --- J. Stance Determination ---
        final_stance = StanceType.NEUTRAL
        stance_explanation = ""

        if not is_relevant:
            final_stance = StanceType.NEUTRAL
            stance_explanation = relevance_reason
        elif item.source_type == EvidenceSourceType.FACT_CHECK_API:
            from backend.app.v2.fact_check_retriever import determine_stance
            fc_stance = determine_stance(effective_raw_rating or "")
            if claim_prop.negated and fc_stance == StanceType.CONTRADICTS:
                final_stance = StanceType.SUPPORTS
                stance_explanation = "Fact check refuted positive claim, supporting negated claim."
            elif claim_prop.negated and fc_stance == StanceType.SUPPORTS:
                final_stance = StanceType.CONTRADICTS
                stance_explanation = "Fact check verified positive claim, contradicting negated claim."
            else:
                final_stance = fc_stance
                stance_explanation = f"Fact check provider rating ({effective_raw_rating}) determined stance."

        elif item.source_type == EvidenceSourceType.LIVE_NEWS_SEARCH:
            if modality_conflict:
                final_stance = StanceType.NEUTRAL
                stance_explanation = "Modality mismatch: Future intent vs completed event."
            elif object_conflict:
                final_stance = StanceType.CONTRADICTS
                stance_explanation = "Conflicting proposition object identified for the same subject/event."
            elif numeric_conflict:
                final_stance = StanceType.CONTRADICTS
                stance_explanation = "Conflicting numeric metric reported for the same subject/event."
            elif negation_conflict:
                final_stance = StanceType.CONTRADICTS
                stance_explanation = "Negation conflict between claim and live news article."
            elif strong_direct_match and not claim_prop.negated:
                final_stance = StanceType.SUPPORTS
                stance_explanation = "Live news directly confirms proposition subject, predicate, object, and metrics."
            else:
                final_stance = StanceType.NEUTRAL
                stance_explanation = "Live news provides reporting context; stance remains neutral."
        else:
            final_stance = StanceType.NEUTRAL
            stance_explanation = "General reference provides encyclopedic background context."

        diagnostic_info = {
            "subject_match": subject_match,
            "predicate_match": predicate_match,
            "object_match": object_match,
            "numeric_match": numeric_match,
            "temporal_match": temporal_match,
            "negation_conflict": negation_conflict,
            "object_conflict": object_conflict,
            "numeric_conflict": numeric_conflict,
            "modality_conflict": modality_conflict,
            "proposition_compatible": proposition_compatible,
            "proposition_conflict": (object_conflict or numeric_conflict or negation_conflict),
            "strong_direct_match": strong_direct_match,
            "structural_result": "COMPATIBLE" if proposition_compatible else ("CONFLICT" if (object_conflict or numeric_conflict or negation_conflict) else "INCOMPATIBLE"),
            "claim_proposition": claim_prop.model_dump_json() if claim_prop else "",
            "evidence_proposition": evidence_prop.model_dump_json() if evidence_prop else "",
            "common_predicates": list(common_predicates),
            "common_objects": list(common_objects)
        }

        return EvidenceMatchResult(
            relevance=RelevanceClassification.RELEVANT if is_relevant else RelevanceClassification.IRRELEVANT,
            stance=final_stance,
            claim_proposition=claim_prop,
            evidence_proposition=evidence_prop,
            subject_match=subject_match,
            predicate_match=predicate_match,
            object_match=object_match,
            numeric_match=numeric_match,
            temporal_match=temporal_match,
            negation_conflict=negation_conflict,
            object_conflict=object_conflict,
            numeric_conflict=numeric_conflict,
            modality_conflict=modality_conflict,
            strong_direct_match=strong_direct_match,
            token_overlap_count=overlap_count,
            token_overlap_ratio=round(overlap_ratio, 3),
            entity_overlap=matched_subjects,
            number_overlap=claim_prop.numeric_constraints,
            date_overlap=claim_prop.temporal_constraints,
            action_match=predicate_match,
            specific_proposition_overlap_count=len(common_objects),
            negation_mismatch=negation_conflict,
            matching_explanation=f"{relevance_reason} Stance: {final_stance.value} ({stance_explanation})",
            diagnostic=diagnostic_info,
            proposition_diagnostic=diagnostic_info
        )

    def process_claim_evidence(
        self, claim: ExtractedClaim, evidence_items: List[EvidenceItem]
    ) -> List[EvidenceItem]:
        """Filters out irrelevant evidence items and attaches structured proposition diagnostics."""
        if not claim or not evidence_items:
            return []

        # Parse claim proposition and attach
        claim.proposition = self.parse_proposition(claim.text)
        processed: List[EvidenceItem] = []

        for item in evidence_items:
            match_res = self.match_evidence(claim, item)
            if match_res.relevance == RelevanceClassification.RELEVANT:
                item_copy = item.model_copy(update={
                    "stance": match_res.stance,
                    "relevance_score": match_res.token_overlap_ratio,
                    "proposition": match_res.evidence_proposition,
                    "proposition_diagnostic": match_res.diagnostic
                })
                processed.append(item_copy)

        return processed


_evidence_matcher_instance = None


def get_evidence_matcher() -> EvidenceMatcher:
    global _evidence_matcher_instance
    if _evidence_matcher_instance is None:
        _evidence_matcher_instance = EvidenceMatcher()
    return _evidence_matcher_instance
