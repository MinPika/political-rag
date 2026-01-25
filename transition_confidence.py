"""Transition Confidence Scoring (TCS).

Scalable across many roles (PM, Consulting, Data, Marketing, Policy-Tech, etc.).
Pure Python, no external dependencies.
"""

from dataclasses import dataclass
from typing import Any, Dict, List


# =========================
# Step 1) Data structures
# =========================


@dataclass(frozen=True)
class RoleProfile:
    name: str
    # competency -> weight (sum to 1.0)
    weights: Dict[str, float]
    # competency -> required level (0-100)
    thresholds: Dict[str, int]


# =========================
# Step 2) Role library
# =========================

ROLE_PROFILES: List[RoleProfile] = [
    RoleProfile(
        name="Product Management (Associate)",
        weights={
            "problem_structuring": 0.25,
            "communication": 0.20,
            "execution_ownership": 0.20,
            "data_literacy": 0.15,
            "stakeholder_mgmt": 0.10,
            "domain_understanding": 0.10,
        },
        thresholds={
            "problem_structuring": 65,
            "communication": 60,
            "execution_ownership": 55,
            "data_literacy": 55,
            "stakeholder_mgmt": 50,
            "domain_understanding": 45,
        },
    ),
    RoleProfile(
        name="Consulting (Analyst)",
        weights={
            "problem_structuring": 0.30,
            "communication": 0.20,
            "quant_reasoning": 0.20,
            "research_writing": 0.15,
            "execution_ownership": 0.10,
            "stakeholder_mgmt": 0.05,
        },
        thresholds={
            "problem_structuring": 70,
            "communication": 60,
            "quant_reasoning": 60,
            "research_writing": 55,
            "execution_ownership": 50,
            "stakeholder_mgmt": 45,
        },
    ),
    RoleProfile(
        name="Data Analyst",
        weights={
            "data_literacy": 0.30,
            "sql": 0.20,
            "analysis_storytelling": 0.20,
            "problem_structuring": 0.15,
            "execution_ownership": 0.10,
            "communication": 0.05,
        },
        thresholds={
            "data_literacy": 65,
            "sql": 60,
            "analysis_storytelling": 55,
            "problem_structuring": 55,
            "execution_ownership": 50,
            "communication": 45,
        },
    ),
    RoleProfile(
        name="Digital Marketing (Performance)",
        weights={
            "communication": 0.15,
            "execution_ownership": 0.20,
            "analytics_marketing": 0.25,
            "creativity_copy": 0.15,
            "experimentation": 0.15,
            "stakeholder_mgmt": 0.10,
        },
        thresholds={
            "communication": 55,
            "execution_ownership": 55,
            "analytics_marketing": 60,
            "creativity_copy": 50,
            "experimentation": 55,
            "stakeholder_mgmt": 45,
        },
    ),
    RoleProfile(
        name="Policy-Tech / GovTech (Associate)",
        weights={
            "problem_structuring": 0.20,
            "research_writing": 0.20,
            "domain_understanding": 0.20,
            "data_literacy": 0.15,
            "execution_ownership": 0.15,
            "stakeholder_mgmt": 0.10,
        },
        thresholds={
            "problem_structuring": 60,
            "research_writing": 60,
            "domain_understanding": 65,
            "data_literacy": 50,
            "execution_ownership": 55,
            "stakeholder_mgmt": 50,
        },
    ),
]


# =========================
# Step 3) Core scoring
# =========================


def _get(user: Dict[str, float], key: str, default: float = 0.0) -> float:
    value = float(user.get(key, default))
    return 0.0 if value < 0 else 100.0 if value > 100 else value


def role_fit_score(user: Dict[str, float], role: RoleProfile) -> Dict[str, Any]:
    """
    Returns:
      - fit_score: 0..100 (weighted capability)
      - readiness: "ready" / "near-ready" / "not-ready"
      - deltas: competency -> (required - current)+
      - gaps_ranked: list of (competency, delta) desc
      - satisfied_thresholds_ratio: 0..1
    """
    fit = sum(w * _get(user, comp) for comp, w in role.weights.items())

    deltas: Dict[str, float] = {}
    satisfied = 0
    for comp, req in role.thresholds.items():
        cur = _get(user, comp)
        delta = max(0.0, req - cur)
        deltas[comp] = delta
        if delta == 0:
            satisfied += 1

    satisfied_ratio = satisfied / max(1, len(role.thresholds))

    if satisfied_ratio >= 0.85 and fit >= 65:
        readiness = "ready"
    elif satisfied_ratio >= 0.60 and fit >= 55:
        readiness = "near-ready"
    else:
        readiness = "not-ready"

    gaps_ranked = sorted(
        ((c, d) for c, d in deltas.items() if d > 0),
        key=lambda x: x[1],
        reverse=True,
    )

    return {
        "role": role.name,
        "fit_score": round(fit, 2),
        "readiness": readiness,
        "deltas": deltas,
        "gaps_ranked": gaps_ranked,
        "satisfied_thresholds_ratio": round(satisfied_ratio, 2),
    }


def score_user_against_roles(
    user: Dict[str, float],
    roles: List[RoleProfile] | None = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    roles = roles or ROLE_PROFILES
    results = [role_fit_score(user, role) for role in roles]
    bucket_rank = {"ready": 2, "near-ready": 1, "not-ready": 0}
    results.sort(
        key=lambda x: (bucket_rank[x["readiness"]], x["fit_score"]),
        reverse=True,
    )
    return results[:top_k]


# =========================
# Step 4) Pattern extraction
# =========================


def extract_pattern(user: Dict[str, float]) -> Dict[str, Any]:
    """Turn raw competency scores into a short diagnostic pattern."""
    strengths = [k for k, v in user.items() if v >= 70]
    weaknesses = [k for k, v in user.items() if v <= 45]

    tags: List[str] = []
    if _get(user, "execution_ownership") <= 45 and (
        _get(user, "problem_structuring") >= 65
        or _get(user, "research_writing") >= 65
    ):
        tags.append("Thinker-heavy, execution-light")
    if _get(user, "communication") <= 50 and _get(user, "problem_structuring") >= 65:
        tags.append("Strong analysis, weak articulation")
    if _get(user, "data_literacy") <= 50 and _get(user, "sql") <= 40:
        tags.append("Data foundation gap")
    if _get(user, "stakeholder_mgmt") <= 45 and _get(user, "communication") >= 60:
        tags.append("Communication ok, stakeholder handling gap")

    return {
        "strengths": strengths[:6],
        "weaknesses": weaknesses[:6],
        "tags": tags[:4],
    }


# =========================
# Step 5) Example run
# =========================


if __name__ == "__main__":
    user_signals = {
        "problem_structuring": 78,
        "communication": 62,
        "research_writing": 74,
        "domain_understanding": 70,
        "execution_ownership": 45,
        "stakeholder_mgmt": 50,
        "data_literacy": 48,
        "sql": 30,
        "quant_reasoning": 55,
        "analysis_storytelling": 52,
        "analytics_marketing": 20,
        "experimentation": 35,
        "creativity_copy": 40,
    }

    print("Pattern:", extract_pattern(user_signals))
    print("\nTop role fits:")
    for result in score_user_against_roles(user_signals, top_k=5):
        print(
            f"- {result['role']} | fit={result['fit_score']} |"
            f" {result['readiness']} | top gaps={result['gaps_ranked'][:3]}"
        )
