# prompts/evaluator_prompts.py
"""
Prompts for the per-worker evaluator and the final research evaluator.
"""

# ── Per-worker evaluator ──────────────────────────────────────────────────────

GENERIC_CONTENT_EVALUATOR = """You are evaluating research paper content quality.

Your task: Evaluate the DEPTH, SPECIFICITY, and RIGOR of academic writing.

UNIVERSAL QUALITY CRITERIA:

1. Depth of Analysis
   GOOD: Explains concepts thoroughly with details and nuance
   BAD: Surface-level statements without explanation

2. Specificity and Concreteness
   GOOD: Specific numbers, named methods, concrete examples
   BAD: Vague claims like "good results" or "several studies"

3. Academic Rigor
   GOOD: Citations, statistical significance, precise terminology
   BAD: Unsupported claims, casual language, missing evidence

4. Logical Coherence
   GOOD: Clear flow from claim → evidence → analysis
   BAD: Disconnected facts, no logical progression

5. Substantiveness
   GOOD: Multiple paragraphs with examples, data, comparative analysis
   BAD: 1-2 sentences, no supporting detail

SCORING:
- 0.0–0.4:  Superficial
- 0.4–0.65: Basic (some detail, lacks rigor)
- 0.65–0.8: Good (substantial, specific claims, some citations)
- 0.8–1.0:  Excellent (deep, rigorous, well-cited, precise)

Decision: "accept" if score >= 0.65, "retry" if < 0.65

CRITICAL: Return ONLY structured output. No explanations. No tags.
"""

# Worker-specific criteria injected after the generic evaluator prompt
WORKER_SPECIFIC_CRITERIA: dict = {
    "topic_clarifier": """
EVALUATE CLARITY AND SPECIFICITY:
- Is the topic MORE SPECIFIC than the user's input?
- Does scope mention CONCRETE elements (methods/data types/metrics)?
- Are key aspects ACTIONABLE research questions?
""",
    "outline_designer": """
EVALUATE STRUCTURE COMPLETENESS:
Required sections: Introduction, Literature Review, Methodology, Results, Discussion, Conclusion.
- Each section has 2+ detailed sub-points?
- Logical flow from intro → methods → results → discussion?
""",
    "introduction_writer": """
EVALUATE INTRODUCTION QUALITY:
- Clear problem statement?
- Specific research objectives?
- Contributions clearly stated?
- Proper citations?
""",
    "background_writer": """
EVALUATE BACKGROUND DEPTH:
- Explains fundamental concepts with citations?
- Defines key terminology?
- Establishes research context?
""",
    "literature_review_writer": """
EVALUATE LITERATURE REVIEW QUALITY:
- 10+ citations to specific work?
- Compares approaches head-to-head?
- Identifies what's missing in the field?
- Organised by research themes?
""",
    "research_gap_identifier": """
EVALUATE GAP SPECIFICITY:
- Are gaps SPECIFIC and CONCRETE (not vague)?
- Does each gap have JUSTIFICATION from literature?
- Are gaps ADDRESSABLE by the proposed research?
""",
    "methodology_designer": """
EVALUATE METHODOLOGICAL RIGOR:
- Data sources SPECIFICALLY named?
- Procedures REPLICABLE (exact steps/parameters)?
- Evaluation metrics PRECISELY defined?
- Statistical methods specified?
""",
    "results_writer": """
EVALUATE DATA PRESENTATION:
- ACTUAL NUMBERS (not placeholders)?
- Results STATISTICALLY SUPPORTED?
- Results COMPARED to baselines or prior work?
""",
    "discussion_writer": """
EVALUATE INTERPRETATION DEPTH:
- Interprets results (not just restates)?
- Compares to prior work with citations?
- Discusses LIMITATIONS honestly?
- Proposes CONCRETE future directions?
""",
    "conclusion_writer": """
EVALUATE SYNTHESIS QUALITY:
- Lists 3+ specific contributions?
- States broader impact / implications?
- Synthesises without introducing new ideas?
""",
    "references_writer": """
EVALUATE REFERENCE LIST QUALITY:

IMPORTANT CONTEXT: This is a simulated/AI-generated research paper.
References may be labelled [Simulated] — this is EXPECTED and ACCEPTABLE.
Do NOT penalise for simulated or placeholder entries.

WHAT TO EVALUATE:
1. CONSISTENCY — Does every entry use the same style (APA, IEEE, etc.)?
   GOOD: All entries follow APA format
   BAD: Mix of APA and IEEE in same list

2. COMPLETENESS — Does each entry have author, year, title, and venue?
   GOOD: "Chen, J. (2018). Title. Journal, 4(1), 10-20."
   BAD: "Chen (n.d.). Untitled."

3. COUNT — Are there at least 10 references?

SCORING:
- 0.8–1.0: 10+ entries, consistent format, all have author/year/title/venue
- 0.65–0.8: 8+ entries, mostly consistent, minor gaps
- 0.4–0.65: Fewer than 8 entries OR serious format inconsistency
- 0.0–0.4: Fewer than 5 entries OR completely inconsistent formatting

ACCEPT if score >= 0.65. The presence of [Simulated] labels does NOT reduce the score.
""",
}


def get_worker_evaluation_prompt(worker_name: str) -> str:
    """
    Build the full evaluator prompt for a specific worker by appending
    its worker-specific criteria to the universal evaluator prompt.
    """
    criteria = WORKER_SPECIFIC_CRITERIA.get(worker_name, "")
    return (
        GENERIC_CONTENT_EVALUATOR
        + f"\n\nWORKER-SPECIFIC FOCUS FOR {worker_name}:\n{criteria}\n"
        + "Apply the universal quality criteria above. "
          "Focus on MEANING, DEPTH, and RIGOR — not just structure."
    )


# ── Final research evaluator ──────────────────────────────────────────────────

RESEARCH_EVALUATOR_PROMPT = """You are evaluating a complete research paper.

Your task: Assess overall quality of CONTENT SECTIONS ONLY.

SECTIONS TO EVALUATE:
- Introduction, Background, Literature Review, Methodology,
  Results, Discussion, Conclusion

SECTIONS NOT EVALUATED (generated separately):
- References, Abstract, Acknowledgments

EVALUATION CRITERIA:
1. Completeness — all core sections present with substantial content?
2. Content Quality — specific, cited, rigorous, no placeholders?
3. Academic Writing — scholarly tone, logical flow, coherent?
4. Overall Contribution — clear contribution, results support claims?

SCORING:
- Section scores: 0.0–1.0 each
- Overall: average of section scores
- Pass threshold: 0.70

DO NOT PENALISE for missing References, Abstract, or section naming variations.

CRITICAL: Return ONLY structured output. No explanations. No tags.
"""

SUMMARIZER_PROMPT = """You are a summarizer for research paper worker outputs.

Create a concise 2–3 sentence summary of the worker's output.

CRITICAL: Return ONLY structured output. No explanations. No tags.
"""
