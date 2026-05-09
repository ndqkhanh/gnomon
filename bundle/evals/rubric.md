# Gnomon eval rubric

A trace eval **passes** when:

1. The attributor's `primitive` field matches `expected_primitive`.
2. The classifier's `failure_class` matches `expected_class`
   (with `unknown` accepted for traces that fall outside the three
   known classes).
3. The proposed patch passes the reversibility check
   (`LBL-GNOMON-REVERSIBLE`).

Aggregate metrics:

- **Attribution recall** — fraction of attributions matching the
  ground-truth primitive (target ≥0.85).
- **Classification accuracy** — fraction matching the ground-truth
  class (target ≥0.80).
- **Patch reversibility rate** — fraction of patches that pass the
  reversibility check (target 1.0; reversibility is a contract).
