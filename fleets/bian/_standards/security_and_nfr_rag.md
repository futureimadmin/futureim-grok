# Security and standards — robust RAG for banking fleets

RAG is a knowledge and design plane. Money movement stays in controlled transactional systems.

## Standards stack

| Standard | Use |
|----------|-----|
| BIAN | Domain boundaries, Semantic APIs, BOM |
| ISO 20022 | Payment/securities semantics |
| OAS 3.x / AsyncAPI 3.x | Interface contracts |
| ArchiMate 3 | EA capability views |
| OAuth2 / OIDC / mTLS | API and service identity |
| PCI DSS | Tokenize cards; no PAN in vectors |
| Privacy (GDPR/local) | Minimize PII in embeddings |
| AI model risk | Human-in-the-loop for credit/payments |

## RAG security controls

1. Tenant + fleet + rack + tier restricts on every query
2. access_level on chunks
3. No secrets in knowledge docs
4. PII hygiene before seed/upload
5. Prompt injection resistance — docs are untrusted data
6. Grounding + citations; refuse if insufficient context
7. RAGAS gates; no auto-execute of high-risk actions from LLM
8. Codegen is scaffolding only
9. Separation of duties: RAG proposes; core systems execute
10. Audit assistant sessions (fleet/rack/mode/domains/RAGAS/user)

## Agent rules

- Never instruct real payment Execute without controlled application layer
- Never mix BIAN structure with product pricing as single authority
- Prefer Retrieve/Evaluate before Initiate on dependent facilities
- Flag PCI/PII if asked to embed raw card or government IDs
