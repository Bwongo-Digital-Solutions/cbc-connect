# Clinical verification gates

CBC Connect must not be used to diagnose, treat, release, or communicate patient results until the local laboratory has completed and documented validation and approval.

## Analyzer validation
- Confirm the exact HumaCount 30TS model, serial/interface options and firmware.
- Obtain vendor protocol documentation and multiple de-identified exports from the deployed device.
- Record serial settings or TCP framing, character encoding, delimiters, checksum rules, terminators and retransmission behavior.
- Build parser tests from real examples plus malformed, truncated, duplicate and out-of-order messages.
- Independently compare every supported analyte, unit, precision, flag and timestamp against the analyzer display/printout.
- Test sample ID matching, duplicate suppression, disconnect/reconnect, queue recovery and replay.
- Keep the parser disabled until the laboratory and engineering owners sign the validation record.

## Clinical configuration
- Never infer or ship universal CBC reference intervals. They depend on laboratory method, analyzer, population, age, sex and local policy.
- Store each interval with its population, age/sex applicability, unit and traceable source.
- A second authorized supervisor must verify each draft interval. Verification records are governance evidence, not automatic proof of clinical validity.
- Do not automatically calculate flags or convert units from draft/unverified intervals.
- Verify report content, rounding, flags, abnormal-result handling, critical-result escalation and correction/amendment procedures.

## Operational approval
- Document acceptance criteria, test evidence, deviations, approvers and approval date.
- Perform parallel testing against the current validated laboratory workflow before go-live.
- Revalidate after analyzer firmware, protocol, mapping, reference interval or report-template changes.
- Maintain a rollback plan and ensure clinicians continue using the approved source of truth.

The HumaCount 30TS adapter in this repository intentionally fails closed. No real device protocol or clinical validation has been asserted.
