# Alarm Management Philosophy

## Purpose

This document defines how alarms are classified, prioritized, and rationalized across all
process units. It applies to every alarm raised by the Alarm Management system regardless of
source system, and is the reference standard operators and engineers use when deciding whether
an alarm requires immediate action, monitoring, or removal.

## Severity Definitions

- **Critical**: Immediate risk to personnel safety, equipment integrity, or environmental
  compliance. Requires acknowledgement within 2 minutes and corrective action within 15 minutes.
- **High**: Significant deviation from safe operating limits that will become critical if
  ignored. Requires acknowledgement within 5 minutes.
- **Medium**: Deviation from normal operating range that does not yet threaten safety or
  equipment. Should be investigated within the current shift.
- **Low**: Informational or early-warning condition. Reviewed during routine rounds.

## Recurring Alarm Policy

An alarm that occurs more than 5 times in a 90-day window on the same asset is classified as
**recurring** and must be entered into the rationalization backlog. Recurring alarms are a
leading indicator of an underlying mechanical or process problem rather than a nuisance to be
silenced -- operators should not simply acknowledge and dismiss them repeatedly without a
documented root-cause investigation.

## Alarm Flood Policy

A flood is defined as 10 or more alarms activating within any rolling 10-minute window on a
single unit. During a flood, operators should follow the Alarm Flood Response Procedure rather
than attempt to action every individual alarm, since floods are usually caused by a single
upstream event (trip, power loss, or instrument air failure) cascading into secondary alarms.

## Rationalization Principles

1. Every alarm should have a documented reason to exist, a defined operator response, and a
   justified setpoint.
2. Alarms that chatter (activate and clear within 60 seconds) repeatedly are strong candidates
   for deadband or delay-timer adjustment, not for simple suppression.
3. Alarms that stay active for unusually long periods (multiple hours) without operator
   response should be reviewed for whether the setpoint, the sensor, or the response procedure
   is at fault.
4. Rationalization decisions must be documented and approved before an alarm's configuration is
   changed. Removing or suppressing an alarm without documented justification is not permitted.
