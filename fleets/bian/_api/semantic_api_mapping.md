# BIAN Semantic API ↔ Service Domain mapping

**Source:** https://github.com/bian-official/public
**Rule:** One YAML API specification = one Service Domain.

## Spec families (release 12–14)

| Path pattern | Meaning |
|--------------|--------|
| `semantic-apis/oas3/yamls/{Domain}.yaml` | BOM-extended OpenAPI 3.x |
| `apis-iso20022_ext-ddd/oas3/yamls/{Domain}.yaml` | ISO20022 + DDD annotations |
| `**/asyncapi-3.x/yamls/{Domain}.yaml` | AsyncAPI 3.x events |

Portal: https://portal.bian.org/

## REST mapping of BIAN action terms

| BIAN action | Typical method |
|-------------|----------------|
| Initiate | POST |
| Register / Evaluate | POST |
| Update / Control / Exchange / Execute / Request / Capture | PUT |
| Retrieve | GET |
| Notify | GET / AsyncAPI |

Path pattern (conceptual):

```text
POST /{ServiceDomain}/initiation
PUT  /{ServiceDomain}/{cr-reference-id}/update
PUT  /{ServiceDomain}/{cr-reference-id}/execution
GET  /{ServiceDomain}/{cr-reference-id}/retrieval
POST /{ServiceDomain}/{cr-reference-id}/{BQ}/initiation
```

## Example mapping

| Service domain | API artifact |
|----------------|--------------|
| Loan | Loan.yaml |
| Mortgage Loan | MortgageLoan.yaml |
| Current Account | CurrentAccount.yaml |
| Payment Execution | PaymentExecution.yaml |
| Customer Offer | CustomerOffer.yaml |
| Direct Debit Mandate | DirectDebitMandate.yaml |

## Codegen

Module = domain; methods = action terms; mark bank policy as EXTENSION; prefer ISO20022 for rails.
