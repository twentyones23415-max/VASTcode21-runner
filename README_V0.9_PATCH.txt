VASTcode21 Cloud Evolution v0.9 patch

Adds persistent evolutionary research to the existing public GitHub runner without exposing strategy source or keys.

New behavior:
- remembers prior experiments in encrypted state
- backfills fingerprints for legacy candidates
- avoids duplicate strategy parameter sets
- 35% exploration / 65% elite-guided evolution by default
- mutation + crossover lineage
- generation tracking
- encrypted leaderboard
- persistent MT5 validation queue
- public summary exposes counts only, not strategy specs
- live trading OFF
- paid services OFF

Apply over the existing VASTcode21_github_v0.8 folder and commit the modified public files.
