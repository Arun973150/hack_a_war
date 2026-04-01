"""
CVE → Compliance Control Mapper
Maps CWE IDs and vulnerability categories to compliance obligations and remediation deadlines.

This is the bridge between security advisories and regulatory compliance:
- A CWE-311 (missing encryption) triggers RBI PA Guidelines + PCI-DSS obligations
- A CWE-287 (auth bypass) triggers PCI-DSS Req 8 + ISO 27001 A.9 obligations
- Deadlines are derived from the actual regulatory text
"""
from typing import TypedDict


class ComplianceMapping(TypedDict):
    category: str
    cwes: list[str]
    keywords: list[str]          # fallback keyword matching when CWE not available
    compliance_controls: list[str]
    regulations: list[dict]      # {name, requirement, deadline_hours, regulator}
    remediation_steps: list[str]
    default_priority: str        # CRITICAL / HIGH / MEDIUM


CVE_COMPLIANCE_MAP: list[ComplianceMapping] = [
    {
        "category": "Encryption Weakness",
        "cwes": ["CWE-311", "CWE-312", "CWE-319", "CWE-326", "CWE-327", "CWE-328"],
        "keywords": ["encryption", "tls", "ssl", "cipher", "openssl", "cryptographic"],
        "compliance_controls": ["Encryption Policy", "Data-in-Transit Protection", "Key Management"],
        "default_priority": "CRITICAL",
        "regulations": [
            {
                "name": "RBI PA Guidelines Annex 2",
                "regulator": "RBI",
                "requirement": "Implementation of PCI-DSS, PA-DSS, latest encryption standards and transport channel security is mandatory",
                "deadline_hours": 48,
                "action": "Upgrade encryption standards and submit evidence to DPSS RBI within 48 hours of discovery",
            },
            {
                "name": "PCI-DSS Requirement 3.5 & 4.1",
                "regulator": "PCI SSC",
                "requirement": "Protect cardholder data using strong cryptography during transmission over open public networks",
                "deadline_hours": 48,
                "action": "Patch encryption library, rotate keys, update PCI-DSS Attestation of Compliance",
            },
            {
                "name": "DPDP Act Section 8(7)",
                "regulator": "MeitY",
                "requirement": "Data fiduciary must protect personal data with reasonable security safeguards",
                "deadline_hours": 72,
                "action": "Patch systems, update risk register, notify Data Protection Officer",
            },
        ],
        "remediation_steps": [
            "Patch affected encryption library immediately",
            "Rotate all TLS certificates and cryptographic keys",
            "Audit all payment endpoints for affected cipher suites",
            "Update compliance documentation with new encryption standards",
            "Submit remediation evidence to internal audit team",
            "Notify RBI DPSS if payment systems are affected (within 48 hours per Annex 2)",
        ],
    },
    {
        "category": "Authentication & Access Control Failure",
        "cwes": ["CWE-287", "CWE-284", "CWE-285", "CWE-306", "CWE-798", "CWE-521"],
        "keywords": ["authentication", "authorization", "access control", "credentials", "password", "mfa", "2fa"],
        "compliance_controls": ["Access Control Policy", "Identity & Access Management", "MFA Enforcement"],
        "default_priority": "CRITICAL",
        "regulations": [
            {
                "name": "RBI PA Guidelines — Authentication",
                "regulator": "RBI",
                "requirement": "ATM PIN prohibited as card-not-present authentication. Strong authentication required for all payment transactions",
                "deadline_hours": 24,
                "action": "Disable weak authentication paths, enforce MFA, report to RBI DPSS if payment systems affected",
            },
            {
                "name": "PCI-DSS Requirement 8",
                "regulator": "PCI SSC",
                "requirement": "Identify and authenticate access to system components. MFA required for all non-console administrative access",
                "deadline_hours": 24,
                "action": "Revoke compromised credentials, enforce MFA, update access control matrix, submit to QSA",
            },
            {
                "name": "ISO 27001 A.9 — Access Control",
                "regulator": "ISO",
                "requirement": "Access to information and information processing facilities shall be restricted",
                "deadline_hours": 48,
                "action": "Review and restrict access rights, update access control policy, conduct access audit",
            },
            {
                "name": "SEBI CSCRF — Access Management",
                "regulator": "SEBI",
                "requirement": "All Market Infrastructure Institutions must enforce role-based access controls and audit all privileged access",
                "deadline_hours": 48,
                "action": "Audit privileged accounts, enforce least privilege, report to SEBI if MII systems affected",
            },
        ],
        "remediation_steps": [
            "Immediately revoke or rotate all potentially compromised credentials",
            "Enforce MFA on all administrative and payment system access",
            "Conduct access rights review — remove unnecessary privileges",
            "Audit all privileged access logs for the past 90 days",
            "Update identity & access management policy documentation",
            "Report to CERT-In within 6 hours if credentials were exfiltrated",
        ],
    },
    {
        "category": "Injection / Input Validation Failure",
        "cwes": ["CWE-89", "CWE-79", "CWE-78", "CWE-77", "CWE-94", "CWE-1321"],
        "keywords": ["injection", "sql", "xss", "cross-site", "command injection", "prototype pollution"],
        "compliance_controls": ["Application Security", "Secure SDLC", "Input Validation"],
        "default_priority": "HIGH",
        "regulations": [
            {
                "name": "PCI-DSS Requirement 6.3",
                "regulator": "PCI SSC",
                "requirement": "All web-facing applications are protected against known attacks. OWASP Top 10 must be addressed",
                "deadline_hours": 48,
                "action": "Deploy WAF rules, patch application, conduct penetration test, update PA-DSS compliance report",
            },
            {
                "name": "RBI PA Guidelines — Security Audit",
                "regulator": "RBI",
                "requirement": "Bi-annual VAPT mandatory. Application vulnerabilities must be remediated before next assessment",
                "deadline_hours": 72,
                "action": "Patch vulnerability, schedule VAPT retest, update security audit report for RBI",
            },
            {
                "name": "GDPR Article 32",
                "regulator": "EU DPA",
                "requirement": "Implementation of appropriate technical measures to ensure security appropriate to the risk",
                "deadline_hours": 72,
                "action": "Patch application, assess if personal data was exposed, notify DPA if breach occurred (72hr deadline)",
            },
        ],
        "remediation_steps": [
            "Apply input validation and parameterized queries throughout affected codebase",
            "Deploy WAF rules targeting the specific vulnerability pattern",
            "Conduct targeted penetration test on affected endpoints",
            "Review all similar code patterns in codebase for the same vulnerability class",
            "Update secure coding standards documentation",
            "If data was accessed: notify regulator per applicable breach notification requirements",
        ],
    },
    {
        "category": "Sensitive Data Exposure",
        "cwes": ["CWE-200", "CWE-201", "CWE-209", "CWE-532", "CWE-359"],
        "keywords": ["data exposure", "information disclosure", "sensitive data", "pii", "personal data", "leak"],
        "compliance_controls": ["Data Classification", "Data Loss Prevention", "Privacy Controls"],
        "default_priority": "CRITICAL",
        "regulations": [
            {
                "name": "DPDP Act 2023 — Breach Notification",
                "regulator": "MeitY",
                "requirement": "Personal data breaches must be reported to the Data Protection Board within 72 hours",
                "deadline_hours": 72,
                "action": "Assess scope of data exposure, notify DPO immediately, file breach report with DPDP Board if personal data affected",
            },
            {
                "name": "GDPR Article 33",
                "regulator": "EU DPA",
                "requirement": "Personal data breaches must be notified to supervisory authority within 72 hours of awareness",
                "deadline_hours": 72,
                "action": "Assess breach, notify supervisory authority within 72 hours, document all actions taken",
            },
            {
                "name": "RBI PA Guidelines — Customer Data",
                "regulator": "RBI",
                "requirement": "Customer card credentials must not be stored in PA database. Report security incidents to RBI DPSS",
                "deadline_hours": 6,
                "action": "Immediately purge exposed card data, report to RBI DPSS, submit root cause analysis by 7th of next month",
            },
        ],
        "remediation_steps": [
            "Immediately identify and stop the data exposure vector",
            "Assess what data was exposed — classify by PII, payment data, credentials",
            "Notify your Data Protection Officer and Legal team immediately",
            "File mandatory breach notification within 72 hours if personal/payment data was exposed",
            "Engage forensics to determine full scope of exposure",
            "Remediate root cause and implement DLP controls",
        ],
    },
    {
        "category": "Supply Chain & Dependency Vulnerability",
        "cwes": ["CWE-1395", "CWE-506", "CWE-494", "CWE-829"],
        "keywords": ["supply chain", "dependency", "third-party", "npm", "package", "library", "open source"],
        "compliance_controls": ["Third-Party Risk Management", "Software Composition Analysis", "Vendor Assessment"],
        "default_priority": "HIGH",
        "regulations": [
            {
                "name": "NIS2 Directive Article 21(2)(d)",
                "regulator": "ENISA",
                "requirement": "Essential entities must implement supply chain security measures including security in network and information systems",
                "deadline_hours": 72,
                "action": "Audit all third-party dependencies, update affected packages, update vendor risk register",
            },
            {
                "name": "DORA Article 28 — ICT Third-Party Risk",
                "regulator": "EBA/ESMA/EIOPA",
                "requirement": "Financial entities must manage ICT third-party risk. Critical third-party services require contractual security clauses",
                "deadline_hours": 72,
                "action": "Assess if affected library is a critical ICT dependency, update third-party risk register, notify vendors",
            },
            {
                "name": "RBI PA Guidelines — Outsourcing",
                "regulator": "RBI",
                "requirement": "Outsourcing agreements must include audit rights and security compliance clauses",
                "deadline_hours": 48,
                "action": "Patch dependency, update software inventory, review outsourced component security assessments",
            },
        ],
        "remediation_steps": [
            "Update all instances of the vulnerable dependency to patched version",
            "Run software composition analysis (SCA) scan on entire codebase",
            "Review and update third-party vendor risk assessments",
            "Check if any SLAs with vendors cover this vulnerability class",
            "Update software bill of materials (SBOM)",
            "Schedule penetration test to verify no residual exposure",
        ],
    },
    {
        "category": "Availability & Resilience Risk",
        "cwes": ["CWE-400", "CWE-770", "CWE-404", "CWE-703"],
        "keywords": ["denial of service", "dos", "ddos", "resource exhaustion", "outage", "availability"],
        "compliance_controls": ["Business Continuity", "Disaster Recovery", "Incident Response"],
        "default_priority": "HIGH",
        "regulations": [
            {
                "name": "DORA Article 11 — ICT Business Continuity",
                "regulator": "EBA/ESMA",
                "requirement": "Financial entities must have comprehensive business continuity plans for ICT disruptions. RTO/RPO targets mandatory",
                "deadline_hours": 4,
                "action": "Activate BCP/DRP, report major ICT incident to competent authority within 4 hours, document impact",
            },
            {
                "name": "RBI PA Guidelines — Cyber Crisis Management",
                "regulator": "RBI",
                "requirement": "Cyber Crisis Management Plan covering Detection, Containment, Response and Recovery is mandatory",
                "deadline_hours": 6,
                "action": "Activate CCMP, report to RBI DPSS and CERT-In, submit root cause analysis by 7th of next month",
            },
            {
                "name": "PCI-DSS Requirement 12.10",
                "regulator": "PCI SSC",
                "requirement": "Incident response plan must be maintained and tested annually. Immediate response required for suspected compromises",
                "deadline_hours": 4,
                "action": "Activate IR plan, isolate affected systems, preserve forensic evidence, notify payment brands",
            },
        ],
        "remediation_steps": [
            "Activate incident response plan immediately",
            "Apply rate limiting and input validation to affected endpoints",
            "Scale infrastructure to absorb attack if active DoS",
            "Notify upstream providers and activate DDoS mitigation services",
            "Document timeline for BCP/DRP compliance records",
            "Conduct post-incident review within 5 business days",
        ],
    },
    {
        "category": "Network & Infrastructure Exposure",
        "cwes": ["CWE-22", "CWE-23", "CWE-36", "CWE-918", "CWE-441"],
        "keywords": ["path traversal", "ssrf", "server-side request forgery", "network", "firewall", "port"],
        "compliance_controls": ["Network Security", "Perimeter Controls", "Infrastructure Hardening"],
        "default_priority": "HIGH",
        "regulations": [
            {
                "name": "PCI-DSS Requirement 1 — Network Security",
                "regulator": "PCI SSC",
                "requirement": "Install and maintain network security controls. Restrict inbound and outbound traffic to only what is necessary",
                "deadline_hours": 48,
                "action": "Patch vulnerability, update firewall rules, restrict network egress, update network diagram for QSA",
            },
            {
                "name": "RBI PA Guidelines — IT Governance",
                "regulator": "RBI",
                "requirement": "Application access standards based on least privilege principle. Forensic readiness for security events required",
                "deadline_hours": 48,
                "action": "Apply network segmentation, restrict access paths, preserve logs for forensic analysis",
            },
        ],
        "remediation_steps": [
            "Apply patch for path traversal / SSRF vulnerability immediately",
            "Restrict server-side network egress to allowlisted destinations only",
            "Audit all file access and URL fetching code paths",
            "Update firewall rules to block unexpected outbound traffic",
            "Run VAPT on affected component to verify fix",
        ],
    },
]


def map_cves_to_compliance(cves: list[dict]) -> list[dict]:
    """
    Takes a list of CVEs (with cve_id, cwes, description, cvss_score, severity)
    and returns compliance-enriched advisories with specific regulatory obligations and remediation steps.
    """
    results = []

    for cve in cves:
        cve_cwes = set(cve.get("cwes", []))
        description_lower = (cve.get("description", "") + " " + cve.get("cve_id", "")).lower()
        matched_mapping = None

        # Try CWE match first (most precise)
        for mapping in CVE_COMPLIANCE_MAP:
            if cve_cwes & set(mapping["cwes"]):
                matched_mapping = mapping
                break

        # Fallback to keyword match
        if not matched_mapping:
            for mapping in CVE_COMPLIANCE_MAP:
                if any(kw in description_lower for kw in mapping["keywords"]):
                    matched_mapping = mapping
                    break

        if not matched_mapping:
            continue

        # Determine priority from CVSS
        cvss = cve.get("cvss_score", 0)
        if cvss >= 9.0:
            priority = "CRITICAL"
        elif cvss >= 7.0:
            priority = "HIGH"
        elif cvss >= 4.0:
            priority = "MEDIUM"
        else:
            priority = matched_mapping["default_priority"]

        results.append({
            "cve_id": cve.get("cve_id"),
            "cvss_score": cvss,
            "severity": cve.get("severity", "HIGH"),
            "description": cve.get("description", ""),
            "category": matched_mapping["category"],
            "cwes": list(cve_cwes),
            "compliance_controls": matched_mapping["compliance_controls"],
            "compliance_impact": matched_mapping["regulations"],
            "remediation_steps": matched_mapping["remediation_steps"],
            "priority": priority,
        })

    # Sort by CVSS score descending
    results.sort(key=lambda x: x["cvss_score"], reverse=True)
    return results


def format_for_agent(mapped_cves: list[dict]) -> str:
    """Format mapped CVEs for injection into agent prompts."""
    if not mapped_cves:
        return "No active security advisories found for this sector."

    lines = ["ACTIVE SECURITY ADVISORIES WITH COMPLIANCE IMPACT:\n"]
    for adv in mapped_cves[:5]:  # limit to top 5
        lines.append(f"[{adv['cve_id']}] CVSS {adv['cvss_score']} — {adv['category']}")
        lines.append(f"  Description: {adv['description'][:200]}")
        lines.append(f"  Compliance Controls Affected: {', '.join(adv['compliance_controls'])}")
        lines.append("  Regulatory Obligations Triggered:")
        for reg in adv["compliance_impact"]:
            lines.append(
                f"    • {reg['name']} ({reg['regulator']}): {reg['requirement']} "
                f"[Deadline: {reg['deadline_hours']}h]"
            )
        lines.append("")
    return "\n".join(lines)
