# Alarm Flood Response Procedure

## Definition

A flood is 10 or more alarms activating within any rolling 10-minute window on a single unit,
as detected by the flood-analysis function in the Alarm Management system.

## Immediate Actions

1. Do not attempt to acknowledge every individual alarm as it arrives. Floods are almost always
   caused by a single upstream event (a trip, a power dip, an instrument air failure, or a
   cooling water interruption) that cascades into many secondary and tertiary alarms.
2. Identify the earliest alarm in the flood window -- it is the most likely root cause. Later
   alarms in the same window are usually consequences, not independent problems.
3. Check the unit's overall status (running / tripped) and utility supplies (power, instrument
   air, cooling water) before investigating individual instruments.
4. Once the root cause is addressed, alarms should begin clearing on their own; do not manually
   force-clear alarms that have not actually returned to normal.

## After the Flood

Log the flood window (start time, end time, peak rate, and asset/alarm breakdown) and route it
to the rationalization backlog. Repeated floods in the same unit are themselves grounds for a
rationalization review, since a well-configured alarm system should rarely flood even during a
genuine unit upset.

## Shift Handover

Any flood event must be included in the shift handover notes, including whether the underlying
cause was confirmed and resolved or is still under investigation.
