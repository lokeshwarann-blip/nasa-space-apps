# Security Architecture & Authorization Specification

**NASA Space Apps Challenge — Astronaut Health Monitoring Software**  
**Document Version:** 1.0  
**Notice:** Hackathon Engineering Prototype — Not a Certified Medical Device

---

> [!WARNING]
> **Regulatory Disclaimer:**  
> This software is an engineering prototype developed for the NASA Space Apps Challenge. It has not undergone formal clinical validation, FDA clearance, or NASA flight hardware/software certification. No claims of HIPAA compliance, HITECH certification, or aerospace flight surgeon replacement are made.

---

## 1. Authentication & Identity Architecture

### 1.1 Local Development Adapter vs Production Identity Federation
* **Hackathon Development Adapter (`LocalDevIdentityProvider`):**
  * Provides Argon2id salted password hashing and deterministic RFC 7519 JWT issuance for standalone development and testing.
  * Secrets are strictly injected through `Settings` environment configuration (`.env`).
* **Production Integration Roadmap:**
  * In a production aerospace deployment, authentication must be delegated to an external enterprise OIDC / SAML Identity Provider (e.g., NASA Launchpad, Keycloak, or government PIV/CAC card infrastructure).
  * Tokens in production should use asymmetric cryptography (RS256 / Ed25519) verified dynamically against the IdP's JSON Web Key Set (JWKS) endpoint.
  * Mandatory multi-factor authentication (MFA) and token revocation / backchannel logout must be enabled.

---

## 2. Role-Based & Object-Level Access Control (RBAC & BOLA Prevention)

Access control is enforced at both the API boundary and the service domain boundary:

| Logical Role | Permitted Actions | Prohibited Actions | Object-Level Scope Enforcement |
| :--- | :--- | :--- | :--- |
| **`CREW_MEMBER`** | Read personal telemetry, self-report wellness check-ins, view personal mission assignments. | Viewing peer astronaut vitals, modifying clinical rules, managing users. | Restricted strictly to records where `crew_member_id == token.crew_member_id`. Cross-crew UUID guessing returns `403 Forbidden`. |
| **`FLIGHT_SURGEON`** | Review clinical assessments, triage alarms, and inspect telemetry for assigned crew. | Modifying system configuration, inspecting unassigned crew members. | Restricted strictly to records where `target_crew_member_id in token.assigned_crew_ids`. |
| **`ADMIN`** | User account provisioning, system configuration, audit review. | Automatic unrestricted access to clinical records and crew vitals. | Denied access to crew health records unless explicitly assigned as a medical officer for that subject. |

---

## 3. Cryptographic Token Validation Specifications

Every incoming request to protected endpoints is evaluated against:
1. **Compact Serialization:** Must contain three valid Base64url sections (`header.payload.signature`).
2. **Algorithm Constraint:** Strict adherence to `HS256` (or `RS256` in production). Algorithmic downgrade attacks (e.g. `none` algorithm) are explicitly rejected.
3. **Cryptographic Signature:** Verified using constant-time comparison (`hmac.compare_digest`) against `SECRET_KEY`.
4. **Token Expiration (`exp`):** Reject expired tokens (`TokenExpiredError`).
5. **Issuer Verification (`iss`):** Must match `settings.JWT_ISSUER` (`nasa-space-apps-auth`).
6. **Audience Verification (`aud`):** Must match `settings.JWT_AUDIENCE` (`nasa-space-apps-api`).
7. **Identity Claims (`sub`, `role`):** Never accept unauthenticated client assertions or body-supplied roles.

---

## 4. Threat Model & Remaining Security Risks

1. **Host Security & Token Storage:**
   * JWT tokens stored in browser localStorage or client memory are susceptible to XSS if a web frontend is connected. Production clients should use HTTP-only, Secure, SameSite cookies or in-memory workers.
2. **Key Rotation & Revocation:**
   * The current development prototype uses stateless JWTs without a distributed token revocation blocklist (e.g., Redis blocklist). In production, token lifespans should be shortened (e.g., 15 minutes) with refresh token rotation.
3. **Database-at-Rest Encryption:**
   * PostgreSQL tables containing telemetry must employ Transparent Data Encryption (TDE) or column-level envelope encryption in production cloud/on-prem environments.

