# Centrifugal Pump Troubleshooting Guide

## High Bearing Vibration

Common root causes, roughly in order of frequency:

1. **Bearing wear** -- progressive increase in vibration amplitude over weeks to months,
   often with a characteristic frequency signature. The usual fix is bearing replacement and
   shaft/coupling alignment check.
2. **Misalignment** -- vibration dominated by 1x and 2x running speed, often appears shortly
   after any maintenance that involved decoupling the pump from its driver.
3. **Imbalance** -- vibration dominated by 1x running speed, radial direction, steady rather
   than trending.
4. **Cavitation** -- irregular, broadband vibration accompanied by a crackling noise and
   suction pressure below the pump's NPSH requirement.
5. **Looseness** -- vibration with multiple harmonics and often inconsistent readings between
   consecutive checks; check foundation bolts and bearing housing fit.

If a pump shows recurring high bearing vibration alarms across multiple weeks despite a recent
repair, re-open the investigation rather than assuming the repair was ineffective from a single
reading -- request a full vibration spectrum analysis rather than relying on the RMS trip alone.

## High Discharge Pressure / Low Suction Pressure

Usually a downstream blockage, a closed or failing control valve, or an upstream strainer
fouling. Verify local pressure gauges against the transmitter before assuming an instrument
fault.

## Seal Leak Detected

Mechanical seal wear, thermal shock from a rapid temperature change, or running the pump outside
its allowable flow range (too far left or right of the best efficiency point) all accelerate
seal wear. A seal that fails repeatedly on the same pump within a short interval suggests the
pump is being operated outside its intended flow range rather than a defective seal batch.

## When to Escalate

Escalate to engineering when: vibration exceeds the shutdown threshold, the same alarm recurs
more than 5 times in 90 days on one asset, or a repair has already been performed and the
condition returns within 60 days.
