# End-to-end proof outline

Date / author / session:
Approach and related IDs:
Base commit:
Status: exploratory outline / ordinary proof / reviewed proof

## Exact input and conclusion

State the input, constructors, semantics, quantifiers, and the weakest useful
conclusion. Define witnesshood by the canonical predicate.

## Construction contracts

Define every symbol. For an algorithm or automaton, give its states, alphabet,
transition behavior, initial state, acceptance or output condition, missing-case
behavior, invariant, finiteness, and effective construction.

## Route

Write every implication from input to conclusion. Mark each link as evidence,
proved here, imported with mapped hypotheses, or an open obligation. For a
reduction, show both directions and effectiveness. For a decision procedure,
separate soundness, completeness, and termination.

## Stronger claims to avoid

List any convenient strengthening that is not needed, such as preserving every
candidate or every agreement profile. Explain why a counterexample to it would
not refute the target.

## Discriminating falsification

Name the adversarial family, bounds, minimization invariant, independent
predicate, and relevant boundary cases. State how to interpret exhaustion,
timeout, or memory failure.

## Review and formalization

List actual independent reviews and checks. Name the semantic risk or critical
dependency that motivates formalization. End with one remaining obligation.
