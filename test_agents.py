"""
Quick agent test — runs without Qdrant/Neo4j/PostgreSQL.
Tests Vertex AI connection + each agent individually.
"""
import os
import sys

# ── make sure .env is loaded ──────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

SAMPLE_REGULATORY_TEXT = """
FEDERAL REGISTER / Vol. 89, No. 45 / March 2026

DEPARTMENT OF HEALTH AND HUMAN SERVICES
Food and Drug Administration

AI-Enabled Medical Device Software — Final Guidance

Section 1. Purpose
This guidance establishes requirements for manufacturers of AI-enabled medical devices
submitting pre-market notifications under section 510(k) of the Federal Food, Drug,
and Cosmetic Act.

Section 2. Requirements
2.1 All manufacturers of AI-enabled medical devices must submit algorithm validation
documentation including training data descriptions, performance metrics, and bias
mitigation strategies by December 31, 2026.

2.2 Manufacturers must establish a post-market monitoring plan for AI algorithm
performance drift within 90 days of device clearance.

2.3 Any significant algorithm change (defined as >5% change in sensitivity or
specificity) must be reported to FDA within 30 days of detection.

Section 3. Penalties
Non-compliance may result in civil monetary penalties up to $15,000 per violation
per day under 21 U.S.C. 333.

Effective Date: January 1, 2027
"""


def test_vertex_connection():
    print("\n" + "="*50)
    print("TEST 1: Vertex AI Connection")
    print("="*50)
    try:
        import vertexai
        from langchain_google_vertexai import ChatVertexAI
        from config import settings

        vertexai.init(project=settings.vertex_project, location=settings.vertex_location)
        llm = ChatVertexAI(
            model_name=settings.vertex_model,
            project=settings.vertex_project,
            location=settings.vertex_location,
            max_output_tokens=50,
        )
        response = llm.invoke("Say: Vertex AI connected successfully")
        print(f"PASS — {response.content}")
        return True
    except Exception as e:
        print(f"FAIL — {e}")
        return False


def test_scanner_agent():
    print("\n" + "="*50)
    print("TEST 2: Scanner Agent (Gemini 2.0 Flash-Lite)")
    print("="*50)
    try:
        # Patch out Neo4j/Qdrant dependencies before import
        from agents.state import ComplianceWorkflowState
        from agents.scanner import ScannerAgent

        state = ComplianceWorkflowState(
            document_id="FDA-2026-TEST-001",
            raw_text=SAMPLE_REGULATORY_TEXT,
            source_url="https://federalregister.gov/test",
            jurisdiction="US_FEDERAL",
            regulatory_body="FDA",
            document_type="GUIDANCE",
            published_date="2026-03-01",
        )

        agent = ScannerAgent()
        result = agent.run(state)

        print(f"  is_relevant     : {result.is_relevant}")
        print(f"  relevance_score : {result.relevance_score:.2f}")
        print(f"  sector          : {result.sector}")
        print(f"  jurisdiction    : {result.jurisdiction}")
        print(f"  reasoning       : {result.scan_reasoning[:100]}")
        print(f"PASS" if result.is_relevant else "WARN — marked as not relevant")
        return result
    except Exception as e:
        print(f"FAIL — {e}")
        return None


def test_extractor_agent(state):
    print("\n" + "="*50)
    print("TEST 3: Extractor Agent (Gemini 2.0 Flash)")
    print("="*50)
    try:
        import unittest.mock as mock
        import agents.extractor as extractor_module
        # Mock vector store to avoid Qdrant dependency
        with mock.patch.object(extractor_module, "RegulatoryVectorStore"):
            agent = extractor_module.ExtractorAgent()
            result = agent.run(state)

        print(f"  obligations found : {len(result.obligations)}")
        print(f"  confidence        : {result.extraction_confidence:.2f}")
        for obs in result.obligations:
            print(f"\n  [{obs.obligation_id}]")
            print(f"    WHO      : {obs.who_must_comply}")
            print(f"    WHAT     : {obs.what[:80]}")
            print(f"    DEADLINE : {obs.deadline}")
            print(f"    PENALTY  : {obs.penalty}")
        print(f"\nPASS" if result.obligations else "WARN — no obligations extracted")
        return result
    except Exception as e:
        print(f"FAIL — {e}")
        return state


def test_action_planner_agent(state):
    print("\n" + "="*50)
    print("TEST 4: Action Planner Agent (Gemini 2.0 Flash)")
    print("="*50)
    try:
        from agents.action_planner import ActionPlannerAgent

        # Give state some mock gaps so planner has something to work with
        from agents.state import ImpactGap
        state.gaps = [
            ImpactGap(
                obligation_id="OBL-001",
                gap_description="No bias mitigation documentation process exists",
                existing_controls=["CTL-PM-001"],
                coverage_pct=30.0,
                risk_score=8,
            )
        ]
        state.affected_business_units = ["Regulatory Affairs", "ML Engineering"]
        state.overall_risk_score = 8
        state.impact_summary = "New FDA AI guidance requires bias documentation not covered by existing controls."

        agent = ActionPlannerAgent()
        result = agent.run(state)

        print(f"  action items generated : {len(result.action_items)}")
        for action in result.action_items:
            print(f"\n  [{action.action_id}] {action.title}")
            print(f"    Owner    : {action.owner}")
            print(f"    Priority : {action.priority}")
            print(f"    Deadline : {action.deadline}")
            print(f"    Effort   : {action.effort_days} days")
            print(f"    Risk     : {action.compliance_risk_score}/10")
        print(f"\nPASS" if result.action_items else "WARN — no action items generated")
        return result
    except Exception as e:
        print(f"FAIL — {e}")
        return state


def test_validator_agent(state):
    print("\n" + "="*50)
    print("TEST 5: Validator Agent (Gemini 2.0 Flash)")
    print("="*50)
    try:
        from agents.validator import ValidatorAgent

        agent = ValidatorAgent()
        result = agent.run(state)

        print(f"  valid      : {result.validation.valid}")
        print(f"  confidence : {result.validation.confidence:.2f}")
        print(f"  issues     : {result.validation.issues}")
        print(f"  hallucinated obligations : {result.validation.hallucinated_obligations}")
        print(f"\nPASS")
        return result
    except Exception as e:
        print(f"FAIL — {e}")
        return state


if __name__ == "__main__":
    print("\nRED FORGE — Agent Test Suite")
    print("Testing Vertex AI agents without infrastructure dependencies\n")

    # Test 1: Vertex AI connection
    connected = test_vertex_connection()
    if not connected:
        print("\nVertex AI connection failed. Check your credentials and project ID.")
        print("Run: gcloud auth application-default login")
        sys.exit(1)

    # Test 2: Scanner
    state = test_scanner_agent()
    if not state:
        sys.exit(1)

    # Test 3: Extractor
    state = test_extractor_agent(state)

    # Test 4: Action Planner
    state = test_action_planner_agent(state)

    # Test 5: Validator
    state = test_validator_agent(state)

    print("\n" + "="*50)
    print("ALL TESTS COMPLETE")
    print("="*50)
