# Contributing

Please keep hardware-tested results separate from offline analysis.
Do not mark `.02.50` as tested based only on a successful patch build or wizard
verification. A useful hardware report includes the actual model/generation,
system/UI versions, exact hashes, installation outcome, visible SMB menu and a
scan initiated at the display that arrived at its destination.

Unknown images must remain rejected by default. New firmware profiles need
independently checked GUI control flow and exact input/output/GUI hashes;
reusing offsets just because two files look similar is insufficient.

Run `python3 -m unittest discover -s tests -v` before submitting changes.
Do not add firmware blobs, dumps, scans, credentials, configuration exports or
private LAN details to commits or issues. Use synthetic fixtures for CI.

The patcher must stay offline. Keep optional device-configuration helpers
separate and explicit about what they change. Do not add automatic flashing,
password guesses, hidden diagnostic access, or unrelated feature changes.
