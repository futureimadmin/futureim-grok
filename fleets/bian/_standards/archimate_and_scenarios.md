# BIAN ArchiMate views and business scenarios

## ArchiMate expression

| BIAN concept | ArchiMate orientation |
|--------------|----------------------|
| Service Domain | Capability |
| Business Area / Domain | Grouping + capability hierarchy |
| Service operation exchange | Serving / flow |
| Business Scenario | Interaction / process sequence |
| Wireframe | First-order allowed connections |

## Business Scenario properties

Bounded · Meaningful · Non-prescriptive · Loose coupled

## Wireframe vs scenario

| Artifact | Role |
|----------|------|
| Wireframe | Allowed edges between domains |
| Business Scenario | Archetypal path (sequence) |

## Agent sequence discipline

1. List participating service domains
2. Order Retrieve/Evaluate before dependent Initiate
3. Payment Order before Payment Execution
4. Credit assessment before facility Initiate
5. Never invent cross-domain shared tables
