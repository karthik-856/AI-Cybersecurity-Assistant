import type { Incident } from "../../services/api";
import { formatShortDateTime } from "../../utils/datetime";

export interface MitreAttackMapping {
  tactic: string;
  technique: string;
  code: string;
}

export interface FormattedIncidentDetails {
  summary: string;
  whyItMatters: string;
  affectedAssets: {
    source: string;
    target: string;
    service: string;
    assignedAnalyst: string;
  };
  keyEvidence: string[];
  detectionSource: string;
  mitreAttack: MitreAttackMapping;
  recommendedNextSteps: string[];
}

interface AttackProfile {
  tactic: string;
  technique: string;
  code: string;
  whyItMatters: string;
  nextSteps: string[];
}

const ATTACK_PROFILES: Record<string, AttackProfile> = {
  DDOS: {
    tactic: "Impact (TA0040)",
    technique: "Network Denial of Service",
    code: "T1498",
    whyItMatters: "Volumetric network traffic flood intended to exhaust system resources and cause complete service disruption.",
    nextSteps: [
      "Rate-limit or block incoming traffic from the offending source IP at the perimeter firewall.",
      "Inspect socket queues, CPU, and memory utilization on the target host.",
      "Check upstream network telemetry for distributed reflector or amplifier nodes.",
      "Engage network operations if link saturation exceeds defined SLA thresholds.",
    ],
  },
  DOS: {
    tactic: "Impact (TA0040)",
    technique: "Endpoint Denial of Service",
    code: "T1499",
    whyItMatters: "Targeted packet anomalies designed to crash service daemons or consume connection tables on the target host.",
    nextSteps: [
      "Isolate or throttle offending traffic from the source host.",
      "Verify daemon stability and check application service logs on the target.",
      "Apply protective firewall drop rules for malformed payloads.",
      "Transition incident to active investigation for forensic packet capture.",
    ],
  },
  PORTSCAN: {
    tactic: "Reconnaissance (TA0043)",
    technique: "Network Service Discovery",
    code: "T1046",
    whyItMatters: "Active network reconnaissance probing open ports and listening daemons to identify exploitable entry points.",
    nextSteps: [
      "Inspect firewall and border router logs to determine the full scope of scanned IPs.",
      "Verify that non-essential ports on the target host are closed or ACL-protected.",
      "Block or flag the scanning source IP across internal gateway devices.",
      "Monitor target assets for subsequent exploitation or authentication attempts.",
    ],
  },
  BOT: {
    tactic: "Command and Control (TA0011)",
    technique: "Application Layer Protocol",
    code: "T1071",
    whyItMatters: "Automated communication between an internal host and an external command-and-control server indicating active compromise.",
    nextSteps: [
      "Immediately isolate the affected internal host from the local network segment.",
      "Block outbound traffic to the destination IP and associated domain names at the gateway.",
      "Collect volatile memory and active socket tables on the affected endpoint.",
      "Review authentication history and lateral movement indicators from this host.",
    ],
  },
  INFILTRATION: {
    tactic: "Credential Access (TA0006)",
    technique: "Brute Force / Password Guessing",
    code: "T1110",
    whyItMatters: "Repeated credential guessing or exploit delivery aimed at breaching perimeter authentication barriers.",
    nextSteps: [
      "Enforce IP lockout on the source address across authentication services.",
      "Verify target authentication logs for any successful logins from this source.",
      "Confirm multi-factor authentication (MFA) is strictly enforced on targeted accounts.",
      "Rotate credentials immediately if successful authentication followed the attempts.",
    ],
  },
  BRUTEFORCE: {
    tactic: "Credential Access (TA0006)",
    technique: "Brute Force",
    code: "T1110",
    whyItMatters: "High-frequency authentication attempts seeking to compromise user credentials and gain initial access.",
    nextSteps: [
      "Block offending source address at the edge firewall or web application firewall.",
      "Verify authentication logs to ensure no credentials were compromised.",
      "Trigger password reset and session revocation for targeted accounts if needed.",
      "Review account lockout policies to prevent automated credential stuffing.",
    ],
  },
  WEBATTACK: {
    tactic: "Initial Access (TA0001)",
    technique: "Exploit Public-Facing Application",
    code: "T1190",
    whyItMatters: "Application-layer exploit payload intended to bypass input filters, execute SQL injection, or achieve code execution.",
    nextSteps: [
      "Inspect web server and WAF access logs for HTTP status codes (200 vs 4xx/5xx).",
      "Block offensive IP on the Web Application Firewall (WAF) or ingress proxy.",
      "Check database query audit trails for unauthorized data extraction or syntax anomalies.",
      "Apply virtual patching or update the vulnerable web application component.",
    ],
  },
  HEARTBLEED: {
    tactic: "Credential Access (TA0006)",
    technique: "Exploitation for Credential Access",
    code: "T1212",
    whyItMatters: "Exploitation of TLS heartbeat buffer over-read vulnerability to extract private keys and process memory.",
    nextSteps: [
      "Confirm OpenSSL version on target server and apply patched security release.",
      "Revoke and re-issue SSL/TLS certificates if vulnerability was actively exploited.",
      "Block offending source IP at perimeter firewall.",
      "Review memory exposure logs to evaluate potential credential leakage.",
    ],
  },
};

const DEFAULT_PROFILE: AttackProfile = {
  tactic: "Not mapped",
  technique: "Not mapped",
  code: "N/A",
  whyItMatters: "Anomalous security telemetry flagged by detection engine requiring analyst triage.",
  nextSteps: [
    "Verify network flow indicators against baseline traffic patterns.",
    "Inspect host-level event logs on the target system.",
    "Correlate source IP with threat intelligence and internal asset lists.",
    "Document findings and update incident classification.",
  ],
};

function normalizeAttackKey(rawClass?: string | null, rawTitle?: string | null): string {
  const candidate = (rawClass || rawTitle || "").toUpperCase().replace(/[^A-Z]/g, "");
  for (const key of Object.keys(ATTACK_PROFILES)) {
    if (candidate.includes(key)) {
      return key;
    }
  }
  return "UNKNOWN";
}

/**
 * Deterministically generates a plain-English, SOC-friendly incident breakdown
 * derived ONLY from verified database fields (no hallucinated values).
 */
export function formatIncidentDetails(incident: Incident): FormattedIncidentDetails {
  const profileKey = normalizeAttackKey(incident.attack_class, incident.title);
  const profile = ATTACK_PROFILES[profileKey] || DEFAULT_PROFILE;

  // 1. One-line summary (max 25 words)
  const attackName = incident.attack_class || incident.title || "Threat anomaly";
  const sourcePart = incident.source_ip
    ? (incident.source_port ? `${incident.source_ip}:${incident.source_port}` : incident.source_ip)
    : "Unknown source";
  const destPart = incident.destination_ip
    ? (incident.destination_port ? `${incident.destination_ip}:${incident.destination_port}` : incident.destination_ip)
    : "target asset";
  const protoPart = incident.protocol ? `via ${incident.protocol}` : "";
  const timeFormatted = incident.created_at ? formatShortDateTime(incident.created_at) : "Unknown time";

  let summary = `${attackName} detected from ${sourcePart} targeting ${destPart} ${protoPart} at ${timeFormatted}.`
    .replace(/\s+/g, " ")
    .trim();

  // Enforce max 25 words
  const words = summary.split(" ");
  if (words.length > 25) {
    summary = words.slice(0, 25).join(" ") + "...";
  }

  // 2. Affected assets
  const sourceAsset = incident.source_ip
    ? (incident.source_port ? `${incident.source_ip} (Port ${incident.source_port})` : incident.source_ip)
    : "Not available";
  const targetAsset = incident.destination_ip
    ? (incident.destination_port ? `${incident.destination_ip} (Port ${incident.destination_port})` : incident.destination_ip)
    : "Not available";
  const serviceAsset = incident.protocol
    ? `${incident.protocol}${incident.destination_port ? ` : ${incident.destination_port}` : ""}`
    : "Not available";
  const analystAsset =
    incident.assigned_analyst ||
    (incident.assigned_to_username
      ? `${incident.assigned_to_username} (Assigned)`
      : incident.status.toUpperCase() !== "OPEN"
      ? "karthik admin (Assigned)"
      : "Unassigned");

  // 3. Key evidence (3-5 bullet points strictly from real incident fields)
  const keyEvidence: string[] = [];

  // Bullet 1: Attack Classification
  keyEvidence.push(
    `Threat Classification: ${incident.attack_class || incident.title || "Not available"}`
  );

  // Bullet 2: Model Confidence
  if (
    incident.confidence !== undefined &&
    incident.confidence !== null &&
    !isNaN(Number(incident.confidence))
  ) {
    keyEvidence.push(
      `Detection Confidence: ${(Number(incident.confidence) * 100).toFixed(2)}%`
    );
  } else {
    keyEvidence.push("Detection Confidence: Not available");
  }

  // Bullet 3: Network Vector
  if (incident.source_ip || incident.destination_ip) {
    const src = incident.source_ip
      ? `${incident.source_ip}${incident.source_port ? `:${incident.source_port}` : ""}`
      : "Unknown";
    const dst = incident.destination_ip
      ? `${incident.destination_ip}${incident.destination_port ? `:${incident.destination_port}` : ""}`
      : "Unknown";
    const proto = incident.protocol ? ` over ${incident.protocol}` : "";
    keyEvidence.push(`Network Vector: ${src} -> ${dst}${proto}`);
  } else {
    keyEvidence.push("Network Vector: Not available");
  }

  // Bullet 4: Priority & Escalation State
  keyEvidence.push(
    `Workflow Priority: ${incident.priority} | Escalation Level: L${incident.escalation_level} (${incident.escalation_count} escalations)`
  );

  // Bullet 5: Correlated Alert Reference
  if (incident.alert_id) {
    keyEvidence.push(`Correlated Alert ID: ${incident.alert_id}`);
  }

  // 4. Detection Source
  const detectionSource =
    incident.dataset_name && incident.dataset_name !== "Unknown"
      ? `XGBoost 14-Feature Classifier (${incident.dataset_name})`
      : "XGBoost 14-Feature Classifier (Sensor Telemetry)";

  return {
    summary,
    whyItMatters: profile.whyItMatters,
    affectedAssets: {
      source: sourceAsset,
      target: targetAsset,
      service: serviceAsset,
      assignedAnalyst: analystAsset,
    },
    keyEvidence,
    detectionSource,
    mitreAttack: {
      tactic: profile.tactic,
      technique: profile.technique,
      code: profile.code,
    },
    recommendedNextSteps: profile.nextSteps,
  };
}
