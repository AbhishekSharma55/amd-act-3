# Held-out recovery comparison

7 frozen synthetic scenarios: h1 is the demo/reference case, the others are held out. Same CP-SAT engine with a 10 s cap per policy solve (the CPU reference is one solve; Rehearsal solves 2-3 policies), not an equal total budget; every case here solved to optimality well within it. Selection seeds [101, 102, 103]; outcomes on separate seeds [9001, 9002, 9003, 9004, 9005] x 500 samples. Synthetic uncertainty, not calibrated to a real factory.

| Case | Kind | Method | Plan | Valid | Weighted tardiness (min) | Overtime min / cost | Risky promises exposed | Held-out E[weighted late min] | Held-out P(all promises kept) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| h1 | outage + hard date (demo) | cpu_reference | reference | True | 190 | 0 / 0.0 | - | 251.4 | 0.479 |
| h1 | outage + hard date (demo) | rehearsal_replay_hidden | alt_reroute | True | 190 | 0 / 0.0 | - | 251.4 | 0.479 |
| h1 | outage + hard date (demo) | rehearsal_replay_shown | alt_reroute | True | 190 | 0 / 0.0 | J4 | 251.4 | 0.479 |
| h2 | outage, no overtime | cpu_reference | reference | True | 0 | 0 / 0.0 | - | 2.8 | 0.768 |
| h2 | outage, no overtime | rehearsal_replay_hidden | alt_keep | True | 0 | 0 / 0.0 | - | 36.9 | 0.125 |
| h2 | outage, no overtime | rehearsal_replay_shown | alt_reroute | True | 0 | 0 / 0.0 | J4 | 2.8 | 0.768 |
| h3 | lathe outage + priority + limited overtime | cpu_reference | reference | True | 10 | 0 / 0.0 | - | 289.4 | 0.002 |
| h3 | lathe outage + priority + limited overtime | rehearsal_replay_hidden | alt_keep | True | 10 | 0 / 0.0 | - | 289.4 | 0.002 |
| h3 | lathe outage + priority + limited overtime | rehearsal_replay_shown | alt_keep | True | 10 | 0 / 0.0 | J4, J5, J7 | 289.4 | 0.002 |
| h4 | changed due dates, no outage | cpu_reference | reference | True | 0 | 0 / 0.0 | - | 0.0 | 1.0 |
| h4 | changed due dates, no outage | rehearsal_replay_hidden | alt_keep | True | 0 | 0 / 0.0 | - | 0.0 | 1.0 |
| h4 | changed due dates, no outage | rehearsal_replay_shown | alt_keep | True | 0 | 0 / 0.0 | - | 0.0 | 1.0 |
| h5 | infeasible hard date | all | alt_keep: INFEASIBLE; alt_reroute: INFEASIBLE; alt_reroute_overtime: INFEASIBLE | - | - | - | - | - | - |
| h6 | two machines, future outages | cpu_reference | reference | True | 250 | 0 / 0.0 | - | 1180.7 | 0.005 |
| h6 | two machines, future outages | rehearsal_replay_hidden | alt_reroute | True | 250 | 0 / 0.0 | - | 1180.7 | 0.005 |
| h6 | two machines, future outages | rehearsal_replay_shown | alt_keep | True | 560 | 50 / 37.5 | - | 782.1 | 1.0 |
| h7 | long lathe outage, tight overtime cutoff | cpu_reference | reference | True | 745 | 30 / 22.5 | - | 1081.8 | 1.0 |
| h7 | long lathe outage, tight overtime cutoff | rehearsal_replay_hidden | alt_keep | True | 745 | 30 / 22.5 | - | 1081.8 | 1.0 |
| h7 | long lathe outage, tight overtime cutoff | rehearsal_replay_shown | alt_keep | True | 745 | 30 / 22.5 | - | 1081.8 | 1.0 |
