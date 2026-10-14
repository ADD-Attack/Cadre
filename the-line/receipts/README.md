# Receipts

One JSON file per shipped ticket, written by the sensor
(`conveyor/sensor.mjs`) after independently fetching the live artifact
and checking the ticket's sensor markers.

A receipt records: ticket id, live URL, attempt number, pass/fail,
timestamp, HTTP status, byte size, and the result of every individual
check. Receipts are append-only history: a failed attempt stays on
record alongside the later pass.

No receipt, no completion. If a product has no receipt in this folder,
the line has not shipped it — whatever anyone says.
