# Primary-source overlap check, 2026-10-07

[SPIN's author-hosted workshop paper](https://spinroot.com/spin/symposia/ws97/schoot.pdf), *Partial-order verification in SPIN can be more efficient*, discusses interleaving reduction and local/termination/LTL properties. General partial-order model checking is established; a conservative domain restriction and its repaired controls are implementation evidence, not a novel reduction algorithm.

[Official SPIN manual](https://spinroot.com/spin/Man/Quick.html) describes enabled-action enumeration and exploration of successor states with visited-state handling. A matched exhaustive checker must model the same action guards, properties and scheduling policy; per-step lint is not an adequate strongest baseline for that question.

[Official TLC execution documentation](https://nightly.tlapl.us/doc/model/executing-tlc.html) documents actual model checker execution and error examination. This artifact invokes no TLC process. Its starter-export metadata projection therefore supplies no independent semantics validation.

The prior journal audit records exact operational-workflow leads in `audit/journal/prior-art.md`. This bounded round verified primary model-checker documentation and overlap in the proposed mechanisms; it did not complete the closer workflow comparison or claim novelty clearance. A neutral matched-semantics external-baseline study remains a journal gate.
