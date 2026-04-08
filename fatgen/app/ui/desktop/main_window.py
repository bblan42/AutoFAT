"""
Tkinter desktop UI — stub.

Full implementation deferred to Phase 2 desktop build.
Run with: python main.py --desktop
"""
import sys


def run():
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        print("ERROR: tkinter is not available in this environment.")
        print("Run 'python main.py --web' to use the browser-based UI instead.")
        sys.exit(1)

    root = tk.Tk()
    root.title("FATGen — Factory Acceptance Test Generator")
    root.geometry("900x600")
    root.configure(bg="#0d0f12")

    # Header bar
    header = tk.Frame(root, bg="#13161b", height=48)
    header.pack(fill="x", side="top")
    header.pack_propagate(False)

    title_lbl = tk.Label(
        header,
        text="FATGEN  —  Factory Acceptance Test Generator",
        bg="#13161b",
        fg="#f5a623",
        font=("Arial", 12, "bold"),
        anchor="w",
        padx=16,
    )
    title_lbl.pack(side="left", fill="y")

    # Body
    body = tk.Frame(root, bg="#0d0f12")
    body.pack(fill="both", expand=True, padx=40, pady=40)

    msg = tk.Label(
        body,
        text="Desktop UI — Coming Soon",
        bg="#0d0f12",
        fg="#edf0f5",
        font=("Arial", 18, "bold"),
    )
    msg.pack(pady=(40, 12))

    sub = tk.Label(
        body,
        text=(
            "The Tkinter desktop UI will be built in a future phase.\n\n"
            "In the meantime, use the web UI:\n"
            "    python main.py --web\n\n"
            "Then open  http://localhost:5000  in your browser."
        ),
        bg="#0d0f12",
        fg="#606878",
        font=("Courier", 11),
        justify="center",
    )
    sub.pack()

    root.mainloop()
