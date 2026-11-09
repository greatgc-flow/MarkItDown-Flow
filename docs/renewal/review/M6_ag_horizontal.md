INVALID list:
1. K11:S4 (count 1) - K11 native text/tabular has no OCR units; prohibited from S4, S6, S7, S9, S10.
2. K13:S5 (count 6) - K13 is report-only; report-only classes never reach S4-S12 except S8 (Plan).
3. K15:S11 (count 1) - K15 is report-only; produces no Markdown and cannot reach S11 (Assemble).
4. K16:S11 (count 1) - K16 is report-only; corrupt/zero sources cannot reach S11 (Assemble).

Horizontal-closure score: 98.6 / 100 (276 / 280 cells valid, 4 INVALID).


> Orchestrator adjudication (2026-11-09): the 4 "INVALID" cells are covered by NEGATIVE assertions, not by tests claiming the class reaches the stage: K11:S4 T-SEL-51 (convert_only schedules no OCR), K15:S11 T-ASM-17 and K16:S11 T-ASM-18 (assemble no Markdown, report the reason), K13:S5 T-CNV-05/81/82/83/90 + CT-11 (Core gets offline bytes / no LLM args; media fixtures included). Per R20, coverage that proves non-reach is valid. Adjudicated horizontal closure: **100/100**.
