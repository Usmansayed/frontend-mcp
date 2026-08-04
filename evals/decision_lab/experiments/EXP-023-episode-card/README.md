# EXP-023 — Perfect Layer Phase B (episode_card readout)

**Date:** 2026-07-18  
**Status:** done  
**Track:** Perfect Coordination Layer Phase B

## Hypothesis

Agents read one `episode_card.v1` instead of nesting through coordinator + strategy.

## Lab lock

`scenarios/episode_card_readout.yaml` — after start, snapshot has `episode_card.schema=episode_card.v1` and nonempty `what_matters`.

## Verdict

**Win** when baseline includes this scenario.
