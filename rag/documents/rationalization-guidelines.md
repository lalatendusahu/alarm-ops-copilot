# Alarm Rationalization Guidelines

## When an Alarm Becomes a Rationalization Candidate

- **Recurrence**: more than 5 occurrences of the same alarm on the same asset within a 90-day
  window.
- **Stale duration**: the alarm stays active, on average, for longer than 3 hours (180 minutes)
  before clearing.
- **Chattering**: the alarm activates and clears within 60 seconds, repeatedly. This is
  typically a deadband or setpoint problem rather than a real process excursion.

An alarm can meet more than one of these criteria at once; when it does, it should be treated as
a higher rationalization priority than an alarm meeting only one.

## Investigation Steps

1. Pull the alarm's occurrence history and confirm the pattern (steady recurrence vs. a single
   recent cluster vs. chattering).
2. Check whether a work order already exists for the underlying asset that might explain or
   have attempted to resolve the pattern.
3. Correlate with other alarms on the same or neighboring assets in the same time window --
   a shared root cause often produces alarms on more than one tag.
4. Document the recommended disposition: adjust setpoint/deadband, adjust the response
   procedure, schedule corrective maintenance, or (rarely) retire the alarm entirely.

## What Not To Do

Do not suppress or acknowledge-and-ignore a recurring alarm as a substitute for investigating
it. A recurring high-severity alarm on a high-criticality asset should be assumed to indicate a
real, worsening condition until a root cause has been identified and ruled out.
