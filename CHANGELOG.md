# Changelog

## Unreleased

- Experimental loopback-only view of the printer's original SMB/FTP address-book
  dialogs, with writes disabled by default and explicit address-book-only opt-in.
- Verified opening/editing one guest SMB destination and adding a named-login
  FTP destination through the stock `.04.06` UI, including successful original
  FTP connection/login/permissions checks and independent address-book readback.
  SMB named NAS authentication, delete, `.02.50` browser behavior and an actual
  FTP scan remain untested.
- Reject guest-helper display names that the stock editor cannot accept,
  including underscores; share/path names remain unaffected.
- Research notes distinguish PDF encryption, copy stamps, document boxes,
  stored print modes and printer-hosted shared folders from proven unlocks.

## 1.0.0 — 2026-10-25

- Offline exact-hash patcher for C1860FW V4.00.04.06 / UI V5.08.20.03.
- Experimental, hardware-untested V4.00.02.50 / UI V5.08.51.05 profile, requiring
  explicit opt-in and producing an `_SMB_UNTESTED.hd` filename.
- Reproducible full-image outputs, GUI/instruction validation, component and
  metadata preservation checks, refusal to overwrite inputs/outputs.
- Optional Tk front end and Windows/macOS launchers.
- German step-by-step guide and separately optional guest SMB favorite helper.
- Native display-to-SMB result and photos from one `.04.06` printer.
- Synthetic unit tests and cross-platform CI, without distributed firmware.
