# Scenario: Enterprise KYC / Party Lifecycle Onboarding

**Business outcome:** A new individual or corporate party is qualified and registered
so any product fleet (lending, deposits, cards, trade, investments) may proceed.

## Sequence (BIAN service domains)

```text
1. Party Authentication          — identity proofing session
2. Document Services             — capture ID, address, corporate docs
3. Party Lifecycle Management    — KYC/KYB checks, sanctions, PEP, risk rating
4. Legal Entity Directory        — (corporate) hierarchy / LEI
5. Party Data Management         — structure associations / officers
6. Party Reference Data Directory — persist party reference data
7. Customer Profile              — build usable profile
8. Customer Access Entitlement   — baseline channel entitlements
9. Customer Agreement            — terms / disclosures acceptance
10. Servicing Event History      — audit trail of onboarding events
```

Optional: Customer Credit Rating, Fraud Evaluation.

## RAG rules

- Scope **enterprise** fleet rack `kyc_onboarding` OR dual-pull BIAN domains listed above.
- Product fleets must **not** redefine KYC; they reference this common capability.
- Codegen for onboarding should emit stubs for Party Lifecycle Management first.
