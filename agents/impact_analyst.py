"""
Agent 3 — Impact Analyst
Model: Gemini 2.5 Pro (highest reasoning — accuracy is paramount here)
Role: Multi-hop reasoning over the Knowledge Graph to assess organizational impact.
      Also fetches active CVEs from NVD/CISA and maps them to compliance obligations.
"""
import asyncio
import structlog
import vertexai
from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_neo4j import Neo4jGraph
from langchain_neo4j import GraphCypherQAChain

from agents.state import ComplianceWorkflowState, ImpactGap, SecurityAdvisory
from knowledge.graph.neo4j_client import Neo4jClient
from knowledge.vectors.qdrant_store import RegulatoryVectorStore
from knowledge.security.cve_control_mapper import map_cves_to_compliance, format_for_agent
from ingestion.connectors.nvd import fetch_nvd_cves, fetch_cisa_kev
from config import settings

logger = structlog.get_logger()

vertexai.init(project=settings.vertex_project, location=settings.vertex_location)

IMPACT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a Chief Compliance Officer and CISO performing deep regulatory and security impact analysis.

Given:
1. New regulatory obligations extracted from a document
2. Organization's existing compliance controls (from Knowledge Graph)
3. Related regulations already in your system
4. Active security advisories (CVEs) relevant to this sector with compliance implications

Your job:
- Determine WHICH business units are affected (regulatory + security)
- For EACH obligation AND each security advisory: identify existing controls, calculate coverage %, identify gaps
- If a CVE affects a compliance control (e.g. an encryption CVE affects PCI-DSS): create a gap for it
- Calculate overall compliance risk score (1=low, 10=critical) — active exploited CVEs raise this score
- Identify conflicts with other jurisdictions
- Provide clear impact summary that includes both regulatory and security risks

Return JSON:
{{
  "affected_business_units": ["list of business units"],
  "gaps": [
    {{
      "obligation_id": "OBL-xxx or CVE-xxx",
      "gap_description": "what is missing — include regulatory citation or CVE ID",
      "existing_controls": ["control IDs"],
      "coverage_pct": 0.0-100.0,
      "risk_score": 1-10
    }}
  ],
  "overall_risk_score": 1-10,
  "jurisdiction_conflicts": ["describe any cross-jurisdiction conflicts"],
  "impact_summary": "executive summary in 2-3 sentences covering both regulatory obligations and active security risks"
}}"""),
    ("human", """NEW OBLIGATIONS:
{obligations}

EXISTING CONTROLS FROM KNOWLEDGE GRAPH:
{kg_context}

SIMILAR REGULATIONS ALREADY IN SYSTEM:
{similar_regulations}

ORGANIZATION PROFILE:
{org_profile}

ACTIVE SECURITY ADVISORIES (CVEs with compliance impact):
{security_context}

Perform impact analysis covering both regulatory compliance gaps and security vulnerability compliance obligations."""),
])


class ImpactAnalystAgent:
    """
    Agent 3: Deep reasoning using Gemini 2.5 Pro.
    Combines LangChain GraphCypherQAChain for KG traversal
    with vector store for similar regulation retrieval.
    """

    def __init__(self):
        self._llm = ChatVertexAI(
            model_name=settings.gemini_pro_model,
            project=settings.vertex_project,
            location=settings.vertex_location,
            temperature=0.1,
            max_output_tokens=8192,
        )
        self._parser = JsonOutputParser()
        self._chain = IMPACT_PROMPT | self._llm | self._parser
        self._neo4j = Neo4jClient()
        self._vector_store = RegulatoryVectorStore()

        # LangChain GraphCypherQAChain for natural language → Cypher
        try:
            self._graph = Neo4jGraph(
                url=settings.neo4j_uri,
                username=settings.neo4j_username,
                password=settings.neo4j_password,
            )
            self._cypher_chain = GraphCypherQAChain.from_llm(
                llm=self._llm,
                graph=self._graph,
                verbose=False,
                allow_dangerous_requests=True,
            )
        except Exception as e:
            logger.warning("cypher_chain_init_failed", error=str(e))
            self._cypher_chain = None

    def run(self, state: ComplianceWorkflowState) -> ComplianceWorkflowState:
        logger.info("impact_analyst_start", document_id=state.document_id)

        try:
            # Step 1: Get KG context for this jurisdiction
            kg_context = self._get_kg_context(state)

            # Step 2: Find similar regulations via vector search
            similar_regs = self._get_similar_regulations(state)

            # Step 3: Get organization profile
            org_profile = self._get_org_profile(state)

            # Step 4: Fetch active CVEs from NVD + CISA and map to compliance
            security_advisories, security_context = self._get_security_context(state)
            state.security_advisories = security_advisories

            # Step 5: Run impact analysis with Gemini 2.5 Pro
            obligations_text = "\n".join([
                f"- [{o.obligation_id}] WHO: {o.who_must_comply} | WHAT: {o.what} "
                f"| DEADLINE: {o.deadline or 'Not specified'} | PENALTY: {o.penalty or 'Not specified'}"
                for o in state.obligations
            ])

            result = self._chain.invoke({
                "obligations": obligations_text,
                "kg_context": kg_context,
                "similar_regulations": similar_regs,
                "org_profile": org_profile,
                "security_context": security_context,
            })

            state.affected_business_units = result.get("affected_business_units", [])
            state.gaps = [ImpactGap(**g) for g in result.get("gaps", [])]
            state.overall_risk_score = result.get("overall_risk_score", 5)
            state.jurisdiction_conflicts = result.get("jurisdiction_conflicts", [])
            state.impact_summary = result.get("impact_summary", "")

            logger.info(
                "impact_analyst_done",
                document_id=state.document_id,
                gaps=len(state.gaps),
                risk_score=state.overall_risk_score,
                business_units=len(state.affected_business_units),
            )

        except Exception as e:
            logger.error("impact_analyst_failed", error=str(e))
            state.error = f"Impact analysis failed: {str(e)}"

        return state

    def _get_kg_context(self, state: ComplianceWorkflowState) -> str:
        try:
            context = self._neo4j.get_org_impact_context(
                jurisdiction=state.jurisdiction,
                sectors=[state.sector],
            )
            if not context["obligations"]:
                return "No existing obligations found for this jurisdiction in Knowledge Graph."

            lines = []
            for item in context["obligations"][:20]:  # limit context
                lines.append(
                    f"Regulation: {item.get('reg_title', 'Unknown')} | "
                    f"Obligation: {item.get('obligation', {}).get('what', '')} | "
                    f"Controls: {[c.get('control', {}).get('name', '') for c in item.get('controls', [])]}"
                )
            return "\n".join(lines)
        except Exception as e:
            logger.warning("kg_context_failed", error=str(e))
            return "Knowledge Graph context unavailable."

    def _get_similar_regulations(self, state: ComplianceWorkflowState) -> str:
        try:
            query = f"{state.jurisdiction} {state.sector} {state.document_type} compliance obligations"
            results = self._vector_store.search(
                query=query,
                limit=5,
                filters={"jurisdiction": state.jurisdiction},
            )
            if not results:
                return "No similar regulations found."
            return "\n".join([
                f"- {r.get('section_title', 'Unknown')}: {r.get('text', '')[:200]}"
                for r in results
            ])
        except Exception as e:
            logger.warning("similar_regs_search_failed", error=str(e))
            return "Similar regulation search unavailable."

    def _get_security_context(
        self, state: ComplianceWorkflowState
    ) -> tuple[list[SecurityAdvisory], str]:
        """Fetch CVEs from NVD + CISA KEV, map to compliance controls, return (advisories, text)."""
        try:
            sector = state.sector or "financial services"

            # Run async fetch in sync context
            loop = asyncio.new_event_loop()
            try:
                nvd_cves, kev_cves = loop.run_until_complete(asyncio.gather(
                    fetch_nvd_cves(sector, cvss_min=7.0, limit=6),
                    fetch_cisa_kev(limit=3),
                ))
            finally:
                loop.close()

            all_cves = kev_cves + nvd_cves  # KEVs first (actively exploited)
            mapped = map_cves_to_compliance(all_cves)

            advisories = [
                SecurityAdvisory(
                    cve_id=m["cve_id"],
                    cvss_score=m["cvss_score"],
                    severity=m["severity"],
                    description=m["description"],
                    category=m["category"],
                    cwes=m.get("cwes", []),
                    compliance_controls=m["compliance_controls"],
                    compliance_impact=m["compliance_impact"],
                    remediation_steps=m["remediation_steps"],
                    priority=m["priority"],
                    is_kev=m.get("is_kev", False),
                )
                for m in mapped
            ]

            context_text = format_for_agent(mapped)
            logger.info(
                "security_context_fetched",
                nvd_count=len(nvd_cves),
                kev_count=len(kev_cves),
                mapped_count=len(mapped),
            )
            return advisories, context_text

        except Exception as e:
            logger.warning("security_context_failed", error=str(e))
            return [], "Security advisory fetch unavailable — proceeding with regulatory analysis only."

    def _get_org_profile(self, state: ComplianceWorkflowState) -> str:
        # In production this comes from org_context PostgreSQL
        # For now return a structured placeholder
        return """
        Organization: Mid-market financial services firm
        Jurisdictions: US Federal, EU, India
        Business Units: Retail Banking, Corporate Finance, Technology, Compliance, Legal
        Frameworks: SOC2, ISO27001, GDPR, PCI-DSS
        Active Controls: 147 controls across all frameworks
        Recent Audit Findings: 3 medium-risk gaps in data retention
        """


def impact_analyst_node(state: ComplianceWorkflowState) -> ComplianceWorkflowState:
    """LangGraph node wrapper for the Impact Analyst Agent."""
    agent = ImpactAnalystAgent()
    return agent.run(state)
