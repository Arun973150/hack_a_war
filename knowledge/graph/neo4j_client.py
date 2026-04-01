import structlog
from contextlib import contextmanager
from neo4j import GraphDatabase, Driver
from config import settings

logger = structlog.get_logger()


class Neo4jClient:
    """Neo4j client with schema initialization for regulatory knowledge graph."""

    def __init__(self):
        self._driver: Driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )
        self._initialize_schema()

    @contextmanager
    def session(self):
        with self._driver.session() as s:
            yield s

    def _initialize_schema(self):
        """Create constraints and indexes for regulatory graph schema."""
        constraints = [
            # Nodes
            "CREATE CONSTRAINT reg_unique IF NOT EXISTS FOR (r:Regulation) REQUIRE r.id IS UNIQUE",
            "CREATE CONSTRAINT obligation_unique IF NOT EXISTS FOR (o:Obligation) REQUIRE o.id IS UNIQUE",
            "CREATE CONSTRAINT control_unique IF NOT EXISTS FOR (c:ComplianceControl) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT reg_body_unique IF NOT EXISTS FOR (b:RegulatoryBody) REQUIRE b.name IS UNIQUE",
            "CREATE CONSTRAINT org_unit_unique IF NOT EXISTS FOR (u:OrganizationUnit) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT jurisdiction_unique IF NOT EXISTS FOR (j:Jurisdiction) REQUIRE j.code IS UNIQUE",
            # Indexes
            "CREATE INDEX reg_effective_date IF NOT EXISTS FOR (r:Regulation) ON (r.effective_date)",
            "CREATE INDEX reg_jurisdiction IF NOT EXISTS FOR (r:Regulation) ON (r.jurisdiction)",
            "CREATE INDEX obligation_deadline IF NOT EXISTS FOR (o:Obligation) ON (o.deadline)",
        ]
        with self.session() as s:
            for constraint in constraints:
                try:
                    s.run(constraint)
                except Exception as e:
                    logger.debug("schema_init_skip", constraint=constraint[:60], reason=str(e))
        logger.info("neo4j_schema_initialized")

    def close(self):
        self._driver.close()

    # ─── Node Operations ─────────────────────────────────────────────────────

    def upsert_regulation(self, reg: dict) -> str:
        """Create or update a Regulation node. Returns regulation ID."""
        query = """
        MERGE (r:Regulation {id: $id})
        SET r.title = $title,
            r.jurisdiction = $jurisdiction,
            r.regulatory_body = $regulatory_body,
            r.document_type = $document_type,
            r.published_date = $published_date,
            r.effective_date = $effective_date,
            r.source_url = $source_url,
            r.summary = $summary,
            r.updated_at = datetime()
        WITH r
        MERGE (j:Jurisdiction {code: $jurisdiction})
        SET j.name = $jurisdiction
        MERGE (r)-[:FALLS_UNDER]->(j)
        WITH r
        MERGE (b:RegulatoryBody {name: $regulatory_body})
        MERGE (b)-[:ISSUED]->(r)
        RETURN r.id AS id
        """
        with self.session() as s:
            result = s.run(query, **reg)
            return result.single()["id"]

    def upsert_obligation(self, obligation: dict, regulation_id: str) -> str:
        """Create or update an Obligation node linked to a Regulation."""
        query = """
        MERGE (o:Obligation {id: $id})
        SET o.text = $text,
            o.who_must_comply = $who_must_comply,
            o.what = $what,
            o.deadline = $deadline,
            o.conditions = $conditions,
            o.penalty = $penalty,
            o.updated_at = datetime()
        WITH o
        MATCH (r:Regulation {id: $regulation_id})
        MERGE (r)-[:HAS_OBLIGATION]->(o)
        RETURN o.id AS id
        """
        with self.session() as s:
            result = s.run(query, regulation_id=regulation_id, **obligation)
            return result.single()["id"]

    def upsert_control(self, control: dict) -> str:
        """Create or update a ComplianceControl node."""
        query = """
        MERGE (c:ComplianceControl {id: $id})
        SET c.name = $name,
            c.description = $description,
            c.owner_team = $owner_team,
            c.framework = $framework,
            c.coverage_score = $coverage_score,
            c.updated_at = datetime()
        RETURN c.id AS id
        """
        with self.session() as s:
            result = s.run(query, **control)
            return result.single()["id"]

    def link_control_to_obligation(
        self, control_id: str, obligation_id: str, coverage_pct: float
    ):
        """Link a compliance control to an obligation with coverage percentage."""
        query = """
        MATCH (c:ComplianceControl {id: $control_id})
        MATCH (o:Obligation {id: $obligation_id})
        MERGE (c)-[r:ADDRESSES]->(o)
        SET r.coverage_pct = $coverage_pct,
            r.updated_at = datetime()
        """
        with self.session() as s:
            s.run(query, control_id=control_id,
                  obligation_id=obligation_id, coverage_pct=coverage_pct)

    def link_regulation_amends(self, new_reg_id: str, amended_reg_id: str):
        """Create an AMENDS relationship between regulations."""
        query = """
        MATCH (new:Regulation {id: $new_reg_id})
        MATCH (old:Regulation {id: $amended_reg_id})
        MERGE (new)-[:AMENDS]->(old)
        """
        with self.session() as s:
            s.run(query, new_reg_id=new_reg_id, amended_reg_id=amended_reg_id)

    # ─── Query Operations ────────────────────────────────────────────────────

    def get_obligations_for_regulation(self, regulation_id: str) -> list[dict]:
        query = """
        MATCH (r:Regulation {id: $regulation_id})-[:HAS_OBLIGATION]->(o:Obligation)
        RETURN o {.*} AS obligation
        """
        with self.session() as s:
            return [r["obligation"] for r in s.run(query, regulation_id=regulation_id)]

    def get_controls_covering_obligation(self, obligation_id: str) -> list[dict]:
        query = """
        MATCH (c:ComplianceControl)-[r:ADDRESSES]->(o:Obligation {id: $obligation_id})
        RETURN c {.*, coverage_pct: r.coverage_pct} AS control
        ORDER BY r.coverage_pct DESC
        """
        with self.session() as s:
            return [r["control"] for r in s.run(query, obligation_id=obligation_id)]

    def get_amendment_chain(self, regulation_id: str) -> list[dict]:
        """Traverse the full amendment chain for a regulation."""
        query = """
        MATCH path = (r:Regulation {id: $regulation_id})-[:AMENDS*]->(ancestor:Regulation)
        RETURN [n IN nodes(path) | n {.*}] AS chain
        ORDER BY length(path) ASC
        LIMIT 1
        """
        with self.session() as s:
            result = s.run(query, regulation_id=regulation_id)
            record = result.single()
            return record["chain"] if record else []

    def get_org_impact_context(self, jurisdiction: str, sectors: list[str]) -> dict:
        """
        Get all obligations + controls for a jurisdiction/sector combo.
        Used by the Impact Analyst agent.
        """
        query = """
        MATCH (j:Jurisdiction {code: $jurisdiction})<-[:FALLS_UNDER]-(r:Regulation)
        MATCH (r)-[:HAS_OBLIGATION]->(o:Obligation)
        OPTIONAL MATCH (c:ComplianceControl)-[addr:ADDRESSES]->(o)
        RETURN r.id AS reg_id,
               r.title AS reg_title,
               o {.*} AS obligation,
               collect({control: c {.*}, coverage: addr.coverage_pct}) AS controls
        """
        with self.session() as s:
            results = s.run(query, jurisdiction=jurisdiction, sectors=sectors)
            return {"obligations": [dict(r) for r in results]}

    def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        """Execute arbitrary Cypher query (used by LangChain GraphCypherQAChain)."""
        with self.session() as s:
            return [dict(r) for r in s.run(query, **(params or {}))]
