# Data Retention and Deletion Policy

**NASA Space Apps Challenge — Astronaut Health Monitoring Software**  
**Document Version:** 1.0  
**Status:** Approved for Prototype & Engineering Architecture

---

## 1. Scope & Objective

This policy defines the data lifecycle, retention windows, and cryptographic deletion procedures for:
1. **Astronaut Biometric & Physiological Telemetry** (`HealthMeasurement`)
2. **Subjective Wellness & Symptom Check-Ins** (`WellnessCheckIn`, `SymptomCheckIn`)
3. **Clinical Assessments & Decision Findings** (`Assessment`)
4. **Security & Access Audit Logs** (`AuditEvent`)
5. **User Identities & Cryptographic Hashes** (`User`, `CrewMember`)

---

## 2. Retention Schedules

| Data Category | Target Entity | Mandatory Retention Window | Justification & Standard |
| :--- | :--- | :--- | :--- |
| **High-Frequency Telemetry** | `HealthMeasurement` | Active Mission Duration + 5 Years Post-Flight | Longitudinal physiological recovery tracking & post-mission aerospace medicine research. |
| **Crew Wellness Check-Ins** | `WellnessCheckIn`, `SymptomCheckIn` | Active Mission Duration + 3 Years Post-Flight | Behavioral health tracking and crew adaptation monitoring. |
| **Clinical Assessments** | `Assessment` | 10 Years | Medical decision record traceability and clinical rule-set version auditing. |
| **Security Audit Logs** | `AuditEvent` | Minimum 365 Days (1 Year) | Security incident investigation, compliance auditing, and non-repudiation. |
| **User Account Records** | `User` | Active Service + 30 Days following revocation | Secure account lifecycle management. |

---

## 3. Deletion & Purging Procedures

### 3.1 Soft Deletion & Cryptographic Shredding
* **Operational Inactivation:** Crew records and user accounts are initially marked with status `INACTIVE` or `SUSPENDED` to prevent immediate unauthorized access while preserving referential integrity.
* **Cascading Purging:** When a hard deletion request is authorized, deletion cascades from `CrewMember` down to child telemetry, wellness, and symptom check-in tables via foreign key `ON DELETE CASCADE`.

### 3.2 Audit Log Immutability
* `AuditEvent` records are write-once, append-only.
* Deletion operations on health records or accounts trigger an immediate, immutable `AuditEvent` capturing the authorizing actor, timestamp, and target resource ID.
* No raw biometric payloads or sensitive notes are stored in `AuditEvent` records, ensuring that retained audit trails comply with privacy minimization principles.

---

## 4. Deletion Authorization Workflow
1. Only users with the `ADMIN` role or an authorized Chief Flight Medical Officer may request a permanent purge.
2. All deletion actions require explicit administrative confirmation and generate an auditable event with action `DELETE_HEALTH_RECORD` or `PURGE_CREW_MEMBER`.
3. Automated retention sweeps run as scheduled background maintenance tasks against records exceeding their statutory expiration dates.

