# BIAN Service Domain: Party Lifecycle Management

**Category:** Reference Data / Party  
**Enterprise-shared:** Yes — shared across all product fleets  
**BIAN version focus:** 12–14 (semantic reference for RAG Fleet)

## Purpose

Tracks the state of a party relationship with the bank from initial onboarding checks (KYC/KYB, sanctions, PEP) through periodic re-assessment and off-boarding. This is the primary BIAN home for enterprise KYC orchestration.

## Canonical operations

Initiate, Update, Control, Retrieve, Evaluate, Notify

## Business objects (BOM touchpoints)

Party, PartyRelationship, ProspectProcedure, QualificationCheck

## RAG / dual-pull rules

1. Dual-pull must include `fleet_id=bian` + `bian_service_domain=Party Lifecycle Management`.
2. Product fleets must not redefine KYC; use enterprise fleet rack `kyc_onboarding`.
3. Codegen emits Party Lifecycle Management stubs for onboarding scopes.
