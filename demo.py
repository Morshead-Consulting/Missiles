import tkinter as tk
from tkinter import ttk

bg_color = "#CDD2DF"

root = tk.Tk()
root.title("Experimental Simulation Design (Mesa)")
root.configure(bg=bg_color)

# Replace icon
try:
    root.iconbitmap('Morshead_Primary_Logo.ico')
except:
    print("Icon file not found or not compatible.")


# === FRAME: Model Information ===
model_frame = ttk.LabelFrame(root, text="1. Model Configuration")
model_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

ttk.Label(model_frame, text="Select Mesa model file:").grid(row=0, column=0, sticky="w")
ttk.Entry(model_frame, width=40).grid(row=0, column=1)
ttk.Button(model_frame, text="Browse").grid(row=0, column=2)

ttk.Label(model_frame, text="Detected factors:").grid(row=1, column=0, sticky="w")
ttk.Label(model_frame, text="(Mocked: ThreatLevel, BlueStrategy, TerrainType)").grid(row=1, column=1, columnspan=2, sticky="w")

# === FRAME: Design Selection ===
design_frame = ttk.LabelFrame(root, text="2. Experimental Design")
design_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

design_type = tk.StringVar(value="Full Factorial (2-level)")

design_options = [
    "Full Factorial (2-level)",
    "Full Factorial (General)",
    "Latin Hypercube",
    "Fractional Factorial",
    "Plackett-Burman",
    "Box-Behnken",
    "Central Composite",
    "Robust Design (Simulation-focused)"
]

for i, option in enumerate(design_options):
    ttk.Radiobutton(design_frame, text=option, variable=design_type, value=option).grid(row=i, column=0, sticky="w")

ttk.Label(design_frame, text="Number of Factors:").grid(row=0, column=1, sticky="e")
ttk.Entry(design_frame, width=5).grid(row=0, column=2)

ttk.Label(design_frame, text="Levels per Factor:").grid(row=1, column=1, sticky="e")
ttk.Entry(design_frame, width=5).grid(row=1, column=2)

ttk.Label(design_frame, text="Replicates:").grid(row=2, column=1, sticky="e")
ttk.Entry(design_frame, width=5).grid(row=2, column=2)

ttk.Label(design_frame, text="Blocks (optional):").grid(row=3, column=1, sticky="e")
ttk.Entry(design_frame, width=5).grid(row=3, column=2)

# === FRAME: Runtime Constraints ===
runtime_frame = ttk.LabelFrame(root, text="3. Runtime Constraints")
runtime_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

runtime_enabled = tk.BooleanVar()

ttk.Checkbutton(runtime_frame, text="Set maximum allowed runtime", variable=runtime_enabled).grid(row=0, column=0, sticky="w")
ttk.Label(runtime_frame, text="Max runtime (hours):").grid(row=1, column=0, sticky="e")
ttk.Entry(runtime_frame, width=5).grid(row=1, column=1)

ttk.Label(runtime_frame, text="Estimated time per run (seconds):").grid(row=2, column=0, sticky="e")
ttk.Entry(runtime_frame, width=5).grid(row=2, column=1)

# === FRAME: Output Summary ===
output_frame = ttk.LabelFrame(root, text="4. Summary")
output_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

ttk.Label(output_frame, text="Design Points:").grid(row=0, column=0, sticky="w")
ttk.Label(output_frame, text="(Calculated later)").grid(row=0, column=1, sticky="w")

ttk.Label(output_frame, text="Total Runs (with replications):").grid(row=1, column=0, sticky="w")
ttk.Label(output_frame, text="(Calculated later)").grid(row=1, column=1, sticky="w")

ttk.Label(output_frame, text="Estimated Completion Time:").grid(row=2, column=0, sticky="w")
ttk.Label(output_frame, text="(Calculated later)").grid(row=2, column=1, sticky="w")

ttk.Button(output_frame, text="Generate Design Plan").grid(row=3, column=0, pady=5)
ttk.Button(output_frame, text="Visual Summary").grid(row=3, column=1, pady=5)

root.mainloop()
