# BIAN Service Domain: Payment Execution

**BIAN version:** 12 (reference)

## Purpose

Execute, clear, and settle payment instructions; manage status through completion, failure, return, or recall.

## Core business objects

| Object | Role |
|--------|------|
| Payment Execution | Runtime execution instance |
| Settlement Position | Clearing/settlement state |
| Return / Recall | Exception objects |

## Boundaries

- Consumes validated **Payment Order** (or scheme-specific instruction).
- Fraud holds may pause execution; cases live in **Fraud Evaluation**.

## Coding guidance

- Model explicit state machine: accepted, in clearing, settled, failed, returned.
- Investigations rack should query execution history, not re-initiate orders blindly.
