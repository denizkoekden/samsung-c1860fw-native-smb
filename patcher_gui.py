#!/usr/bin/env python3
"""Small, offline Tk front end. All firmware checks live in patcher.py."""
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from pathlib import Path

from patcher import PatchError, inspect_file, patch_file


def main():
    root = tk.Tk()
    root.title("Samsung C1860FW – nativer SMB-Scan")
    root.geometry("800x570")
    frame = ttk.Frame(root, padding=16)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Offline-Patcher für Samsung Xpress C1860FW",
              font=("TkDefaultFont", 15, "bold")).pack(anchor="w")
    ttk.Label(frame, text=".04.06: an einem Gerät getestet  ·  .02.50: am Gerät UNGETESTET\n"
              "Zuerst docs/ANLEITUNG.md lesen. Dieses Programm lädt nichts zum Drucker hoch.",
              wraplength=750).pack(anchor="w", pady=(8, 14))
    row = ttk.Frame(frame)
    row.pack(fill="x")
    selected = tk.StringVar()
    entry = ttk.Entry(row, textvariable=selected)
    entry.pack(side="left", fill="x", expand=True)
    busy = False

    def browse():
        value = filedialog.askopenfilename(title="ORIGINALE Hersteller-Firmware auswählen",
                                           filetypes=[("Samsung Firmware", "*.hd"), ("Alle Dateien", "*")])
        if value:
            selected.set(value)

    choose = ttk.Button(row, text="Original .hd auswählen…", command=browse)
    choose.pack(side="right", padx=(8, 0))
    allow = tk.BooleanVar(value=False)
    acknowledgement = ttk.Checkbutton(frame, variable=allow,
        text="Nur .02.50: Ich habe die Warnung zum UNGETESTETEN alten Hardwarezweig gelesen.")
    acknowledgement.pack(anchor="w", pady=12)
    output = scrolledtext.ScrolledText(frame, height=16, wrap="word", state="disabled")
    output.pack(fill="both", expand=True)
    events = queue.Queue()

    def log(text):
        output.configure(state="normal")
        output.insert("end", text + "\n")
        output.see("end")
        output.configure(state="disabled")

    def finish():
        nonlocal busy
        busy = False
        for widget in (choose, button, entry, acknowledgement):
            widget.configure(state="normal")

    def worker(source, target, permission):
        try:
            result = patch_file(source, target, allow_untested=permission,
                                log=lambda line: events.put(("log", line)))
            events.put(("done", result))
        except Exception as exc:
            events.put(("error", str(exc)))

    def start():
        nonlocal busy
        if busy:
            return
        source = Path(selected.get().strip())
        try:
            profile = inspect_file(source)
            if not profile.tested and not allow.get():
                raise PatchError(".02.50 ist am Gerät UNGETESTET. Bitte zuerst die Anleitung lesen "
                                 "und die zusätzliche Freigabe oben aktivieren.")
        except (PatchError, OSError) as exc:
            messagebox.showerror("Keine Datei erstellt", str(exc), parent=root)
            return
        name = source.stem + ("_SMB.hd" if profile.tested else "_SMB_UNTESTED.hd")
        target = filedialog.asksaveasfilename(title="Neue SMB-Firmware speichern",
                    initialdir=str(source.parent), initialfile=name, defaultextension=".hd",
                    filetypes=[("Samsung Firmware", "*.hd")], confirmoverwrite=True)
        if not target:
            return
        # The core rejects all existing outputs, even after a save-dialog confirmation.
        busy = True
        for widget in (choose, button, entry, acknowledgement):
            widget.configure(state="disabled")
        log("Prüfung und Komprimierung laufen. Das kann einige Minuten dauern…")
        threading.Thread(target=worker, args=(source, Path(target), allow.get()), daemon=True).start()

    button = ttk.Button(frame, text="SMB-Datei erstellen – kein Flashen", command=start)
    button.pack(anchor="e", pady=(12, 0))

    def poll():
        try:
            while True:
                kind, value = events.get_nowait()
                if kind == "log":
                    log(value)
                elif kind == "done":
                    finish()
                    messagebox.showinfo("Datei fertig – Drucker unverändert",
                        "Die geprüfte SMB-.hd und ein JSON-Prüfbericht wurden erstellt.\n\n"
                        "Jetzt der SyncThru-Anleitung in docs/ANLEITUNG.md folgen.\n"
                        "Das Erstellen der Datei installiert noch keine Firmware.", parent=root)
                else:
                    finish()
                    log("FEHLER: " + value)
                    messagebox.showerror("Keine vollständige Ausgabedatei erstellt", value, parent=root)
        except queue.Empty:
            pass
        root.after(100, poll)

    def close():
        if busy:
            messagebox.showinfo("Bitte warten", "Die Offline-Datei wird gerade erstellt.", parent=root)
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    root.after(100, poll)
    root.mainloop()


if __name__ == "__main__":
    main()
