import time
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class SemanticRelation(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    NEUTRAL = "NEUTRAL"


class SemanticVerificationPrediction(BaseModel):
    premise: str
    hypothesis: str
    raw_label: str
    semantic_relation: SemanticRelation
    logits: Dict[str, float] = Field(default_factory=dict)
    probabilities: Dict[str, float] = Field(default_factory=dict)
    latency_ms: float = 0.0


class SemanticVerifierPrototype:
    """Isolated prototype for semantic textual verification using a pretrained NLI cross-encoder.

    Evaluates whether an evidence premise text logically entails, contradicts, or remains neutral
    with respect to a candidate claim hypothesis.
    """

    MODEL_NAME = "cross-encoder/nli-distilroberta-base"

    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("PyTorch and Hugging Face Transformers are required for SemanticVerifierPrototype.")

        self.model_name = model_name or self.MODEL_NAME
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        start_load = time.time()
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()
        self.load_time_ms = (time.time() - start_load) * 1000

        # Output label mapping:
        # id2label for nli-distilroberta-base is {0: 'contradiction', 1: 'entailment', 2: 'neutral'}
        self.id2label = self.model.config.id2label

    def verify_pair(self, premise: str, hypothesis: str) -> SemanticVerificationPrediction:
        """Verifies semantic relation between premise (evidence text) and hypothesis (claim)."""
        if not premise or not hypothesis:
            return SemanticVerificationPrediction(
                premise=premise or "",
                hypothesis=hypothesis or "",
                raw_label="neutral",
                semantic_relation=SemanticRelation.NEUTRAL,
                logits={"contradiction": 0.0, "entailment": 0.0, "neutral": 0.0},
                probabilities={"contradiction": 0.333, "entailment": 0.333, "neutral": 0.334},
                latency_ms=0.0
            )

        start_time = time.time()

        inputs = self.tokenizer(
            premise.strip(),
            hypothesis.strip(),
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits[0]
            probs = torch.softmax(logits, dim=-1)

        pred_idx = torch.argmax(logits).item()
        raw_label = self.id2label.get(pred_idx, "neutral").lower()

        # Deterministic label normalization
        if "entail" in raw_label:
            relation = SemanticRelation.SUPPORTS
        elif "contradict" in raw_label:
            relation = SemanticRelation.CONTRADICTS
        else:
            relation = SemanticRelation.NEUTRAL

        elapsed_ms = (time.time() - start_time) * 1000

        logits_dict = {
            self.id2label.get(i, str(i)).lower(): round(float(logits[i]), 4)
            for i in range(len(logits))
        }
        probs_dict = {
            self.id2label.get(i, str(i)).lower(): round(float(probs[i]), 4)
            for i in range(len(probs))
        }

        return SemanticVerificationPrediction(
            premise=premise,
            hypothesis=hypothesis,
            raw_label=raw_label,
            semantic_relation=relation,
            logits=logits_dict,
            probabilities=probs_dict,
            latency_ms=round(elapsed_ms, 2)
        )

    def verify_batch(self, pairs: List[Tuple[str, str]]) -> List[SemanticVerificationPrediction]:
        """Batch evaluates multiple premise-hypothesis pairs."""
        return [self.verify_pair(p, h) for p, h in pairs]


# 24-Case Controlled Test Set Definition
CONTROLLED_TEST_SET = [
    # --- 8 CLEAR ENTAILMENT / SUPPORTS ---
    {
        "id": "supp_01",
        "category": "Stage 34A Chemical Fact (real_05)",
        "premise": "Water is a chemical compound consisting of two hydrogen atoms and one oxygen atom (H2O).",
        "hypothesis": "Water Molecule Chemical Composition Consists of Hydrogen and Oxygen",
        "ground_truth": SemanticRelation.SUPPORTS
    },
    {
        "id": "supp_02",
        "category": "Stage 34A International Treaty (real_07)",
        "premise": "The Paris Agreement is an international treaty on climate change adopted by international consensus in 2015 and signed in 2016.",
        "hypothesis": "Paris Agreement on Climate Change Adopted by International Consensus",
        "ground_truth": SemanticRelation.SUPPORTS
    },
    {
        "id": "supp_03",
        "category": "Task 4 Historical Fact Check (real_04 Apollo)",
        "premise": "Fact Check: The Apollo 11 moon landing was not staged. Neil Armstrong and Buzz Aldrin successfully landed the Apollo 11 Lunar Module on the Moon in July 1969.",
        "hypothesis": "Apollo 11 Astronauts Landed on Moon in July 1969",
        "ground_truth": SemanticRelation.SUPPORTS
    },
    {
        "id": "supp_04",
        "category": "Task 4 Legislation Fact Check (fc_05 EU Cars)",
        "premise": "The European Parliament and EU member states have officially approved legislation mandating zero emissions for new cars, banning new internal combustion engine cars from 2035.",
        "hypothesis": "European Union Bans Internal Combustion Engine Cars by 2035",
        "ground_truth": SemanticRelation.SUPPORTS
    },
    {
        "id": "supp_05",
        "category": "Stage 34A Astronomical Milestone (real_02 JWST SMACS)",
        "premise": "SMACS 0723 was the target of the first full-color image unveiled by the James Webb Space Telescope, revealing the deepest infrared view of the universe to date.",
        "hypothesis": "James Webb Space Telescope Unveils Deepest Infrared Image of Universe",
        "ground_truth": SemanticRelation.SUPPORTS
    },
    {
        "id": "supp_06",
        "category": "Institutional AI Act (news_06)",
        "premise": "The European Parliament passed the landmark EU Artificial Intelligence Act, establishing comprehensive global regulation for artificial intelligence.",
        "hypothesis": "European Parliament Passed EU Artificial Intelligence Act",
        "ground_truth": SemanticRelation.SUPPORTS
    },
    {
        "id": "supp_07",
        "category": "Human Genome Project (real_06)",
        "premise": "The Human Genome Project was an international scientific research project with the goal of determining the base pairs that make up human DNA.",
        "hypothesis": "Human Genome Project Sequenced the Complete Human Genome",
        "ground_truth": SemanticRelation.SUPPORTS
    },
    {
        "id": "supp_08",
        "category": "Scientific Milestone (real_03 LHC)",
        "premise": "Physicists at CERN's Large Hadron Collider discovered the Higgs boson particle in July 2012, confirming the mechanism that gives mass to fundamental particles.",
        "hypothesis": "CERN Large Hadron Collider Discovered the Higgs Boson Particle",
        "ground_truth": SemanticRelation.SUPPORTS
    },

    # --- 8 CLEAR CONTRADICTION / CONTRADICTS ---
    {
        "id": "contra_01",
        "category": "Stage 34A Anti-Scientific Myth (false_04 Flat Earth)",
        "premise": "Modern scientific consensus and satellite photographs confirm Earth is an oblate spheroid. Claims that Earth is a flat disk are false and rejected by science.",
        "hypothesis": "Earth Is Flat Disk and NASA Edits All Satellite Photographs",
        "ground_truth": SemanticRelation.CONTRADICTS
    },
    {
        "id": "contra_02",
        "category": "Stage 34A Geocentric Myth (false_08 Geocentric)",
        "premise": "Astronomical observation confirms that Earth rotates on its axis and orbits the Sun. The Sun does not revolve around a stationary Earth.",
        "hypothesis": "Sun Revolves Around Stationary Earth Every 24 Hours",
        "ground_truth": SemanticRelation.CONTRADICTS
    },
    {
        "id": "contra_03",
        "category": "Medical Oncology Misconception (fc_07 Shark Cancer)",
        "premise": "Scientific studies have documented that sharks do develop cancer and benign tumors, disproving the myth that shark cartilage cures cancer.",
        "hypothesis": "Sharks Do Not Suffer from Cancer and Shark Cartilage Cures Malignant Tumors",
        "ground_truth": SemanticRelation.CONTRADICTS
    },
    {
        "id": "contra_04",
        "category": "Viral Conspiracy (false_05 5G Microchips)",
        "premise": "Public health agencies confirm COVID-19 vaccines contain mRNA or viral vectors without microchips, 5G tracking hardware, or electronic devices.",
        "hypothesis": "COVID-19 Vaccines Contain Injectable 5G Microchips for Digital Surveillance",
        "ground_truth": SemanticRelation.CONTRADICTS
    },
    {
        "id": "contra_05",
        "category": "Hazardous Ingestion Hoax (false_07 Bleach)",
        "premise": "Health authorities warn that drinking household chemical disinfectants like bleach is highly toxic and does not safely treat viral infections.",
        "hypothesis": "Drinking Household Chemical Disinfectant Safely Cleans Viral Pathogens",
        "ground_truth": SemanticRelation.CONTRADICTS
    },
    {
        "id": "contra_06",
        "category": "Physiological Myth (fc_06 Carrots)",
        "premise": "Eating carrots does not grant humans night vision and cannot cure structural eye disorders such as myopia.",
        "hypothesis": "Eating Carrots Gives Humans Night Vision and Cures Myopia",
        "ground_truth": SemanticRelation.CONTRADICTS
    },
    {
        "id": "contra_07",
        "category": "Synthetic Hoax (synth_01 RFID Law)",
        "premise": "The European Union has never passed any directive or legislation requiring citizens to receive RFID microchip implants.",
        "hypothesis": "European Union Passes Emergency Law Mandating RFID Microchip Implants",
        "ground_truth": SemanticRelation.CONTRADICTS
    },
    {
        "id": "contra_08",
        "category": "Electoral Falsification (fc_08 Election Fraud)",
        "premise": "Audits and court rulings confirmed the voting tabulators operated accurately and no software algorithm switched votes.",
        "hypothesis": "Voting Machine Software Algorithm Switched Millions of Votes in Election",
        "ground_truth": SemanticRelation.CONTRADICTS
    },

    # --- 8 NEUTRAL / ADJACENT / INSUFFICIENT ---
    {
        "id": "neut_01",
        "category": "Task 4 Real Failure (real_02 JWST Chorizo Hoax)",
        "premise": "A viral photograph claiming to show the first star image captured by the James Webb Space Telescope was actually a slice of Spanish chorizo sausage on a black background.",
        "hypothesis": "James Webb Space Telescope Unveils Deepest Infrared Image of Universe",
        "ground_truth": SemanticRelation.NEUTRAL
    },
    {
        "id": "neut_02",
        "category": "Task 4 Real Failure (real_08 CRISPR Vaccine Debunk)",
        "premise": "Fact Check: COVID-19 mRNA vaccines do not contain CRISPR-Cas9 gene editing tools and do not permanently modify human DNA.",
        "hypothesis": "CRISPR-Cas9 gene editing technology was developed by Emmanuelle Charpentier and Jennifer Doudna",
        "ground_truth": SemanticRelation.NEUTRAL
    },
    {
        "id": "neut_03",
        "category": "Same Entity Different Claim (real_01 Voyager 1 Topic)",
        "premise": "NASA's Voyager 1 spacecraft experienced a thruster glitch in 2024 and engineers switched to a backup thruster branch to maintain communication.",
        "hypothesis": "NASA Voyager 1 Reached Interstellar Space in August 2012",
        "ground_truth": SemanticRelation.NEUTRAL
    },
    {
        "id": "neut_04",
        "category": "Same Topic Different Proposition (news_03 Climate)",
        "premise": "Meteorologists report unseasonable snowfall in parts of the southern hemisphere during July.",
        "hypothesis": "Global Average Temperatures in 2023 Exceeded Previous Instrumental Records",
        "ground_truth": SemanticRelation.NEUTRAL
    },
    {
        "id": "neut_05",
        "category": "Unverified Niche Claim (unver_07 Coolidge Coin)",
        "premise": "Calvin Coolidge served as the 30th President of the United States from 1923 to 1929 and oversaw a period of rapid economic growth.",
        "hypothesis": "Coin Collector Claims Finding 1923 Silver Dollar Hand-Signed by President Coolidge",
        "ground_truth": SemanticRelation.NEUTRAL
    },
    {
        "id": "neut_06",
        "category": "Generic Background Context (unver_02 Quantum Tech)",
        "premise": "Quantum computing is a rapidly developing field of computer science utilizing quantum superposition and entanglement.",
        "hypothesis": "Tech Startup Announces Commercial 100000 Qubit Quantum Processor Available Next Month",
        "ground_truth": SemanticRelation.NEUTRAL
    },
    {
        "id": "neut_07",
        "category": "Adjacent Hoax Debunk (real_01 Voyager Death Hoax)",
        "premise": "Viral posts falsely claiming that Voyager 1 has permanently shut down and crashed into an asteroid are false; NASA confirms it remains in communication.",
        "hypothesis": "NASA Voyager 1 Spacecraft Traveled Beyond the Heliosphere",
        "ground_truth": SemanticRelation.NEUTRAL
    },
    {
        "id": "neut_08",
        "category": "Topical Mention with No Action Confirmation (news_01 Pass)",
        "premise": "Lawmakers debated the draft provisions of the immigration reform bill during a lengthy parliamentary committee hearing.",
        "hypothesis": "Parliament Officially Passed the Comprehensive Immigration Reform Act",
        "ground_truth": SemanticRelation.NEUTRAL
    }
]
