# Guide: Scoreboard

## Use when
Every structural/balanced turn — before locking UI direction.

## Decisions to resolve
Which unpaid families bind, whether gate blocks claim, and which single tool is next inside the owed plan.

## Minimum evidence
1. Read episode_card: **unpaid + gate + backlog.top**
2. Classify task; build **owed ≤3** = unpaid ∩ class
3. Prefer backlog.top only if already in owed
4. If unpaid empty → still run class min path
5. One tool from owed; re-read unpaid after evidence

## Implementation boundary
Do not treat gate.next or recommended_evidence as the whole plan. Confidence is not a gate.

## Done condition
Owed plan clear; next call from owed; structural locks only after advancement_eligible evidence.
