import os
import threading
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

QUICK_MODELS = {
    "openai": ["gpt-4o-mini", "gpt-4.1-nano", "gpt-4.1-mini", "gpt-4o"],
    "anthropic": ["claude-3-5-haiku-latest", "claude-3-5-sonnet-latest", "claude-3-7-sonnet-latest", "claude-sonnet-4-0"],
    "google": ["gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-2.5-flash-preview-05-20"],
    "openrouter": ["meta-llama/llama-4-scout:free", "meta-llama/llama-3.3-8b-instruct:free", "google/gemini-2.0-flash-exp:free"],
    "ollama": ["llama3.1", "llama3.2"],
}

DEEP_MODELS = QUICK_MODELS

ANALYSTS = [
    ("Market", tk.BooleanVar(value=True)),
    ("Social", tk.BooleanVar(value=True)),
    ("News", tk.BooleanVar(value=True)),
    ("Fundamentals", tk.BooleanVar(value=True)),
]

class TradingAgentsGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TradingAgents GUI")
        self.geometry("600x700")
        self._create_widgets()

    def _create_widgets(self):
        frame = ttk.Frame(self)
        frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        row = 0
        ttk.Label(frame, text="Ticker:").grid(row=row, column=0, sticky=tk.W)
        self.ticker_var = tk.StringVar(value="SPY")
        ttk.Entry(frame, textvariable=self.ticker_var).grid(row=row, column=1, sticky="ew")
        row += 1

        ttk.Label(frame, text="Analysis Date (YYYY-MM-DD):").grid(row=row, column=0, sticky=tk.W)
        self.date_var = tk.StringVar(value=datetime.date.today().strftime("%Y-%m-%d"))
        ttk.Entry(frame, textvariable=self.date_var).grid(row=row, column=1, sticky="ew")
        row += 1

        ttk.Label(frame, text="LLM Provider:").grid(row=row, column=0, sticky=tk.W)
        self.provider_var = tk.StringVar(value="openai")
        provider_menu = ttk.OptionMenu(frame, self.provider_var, "openai", *QUICK_MODELS.keys(), command=self._update_models)
        provider_menu.grid(row=row, column=1, sticky="ew")
        row += 1

        ttk.Label(frame, text="Quick Think Model:").grid(row=row, column=0, sticky=tk.W)
        self.quick_model_var = tk.StringVar(value=QUICK_MODELS["openai"][0])
        self.quick_menu = ttk.OptionMenu(frame, self.quick_model_var, QUICK_MODELS["openai"][0], *QUICK_MODELS["openai"])
        self.quick_menu.grid(row=row, column=1, sticky="ew")
        row += 1

        ttk.Label(frame, text="Deep Think Model:").grid(row=row, column=0, sticky=tk.W)
        self.deep_model_var = tk.StringVar(value=DEEP_MODELS["openai"][0])
        self.deep_menu = ttk.OptionMenu(frame, self.deep_model_var, DEEP_MODELS["openai"][0], *DEEP_MODELS["openai"])
        self.deep_menu.grid(row=row, column=1, sticky="ew")
        row += 1

        ttk.Label(frame, text="Research Depth:").grid(row=row, column=0, sticky=tk.W)
        self.depth_var = tk.IntVar(value=1)
        ttk.OptionMenu(frame, self.depth_var, 1, 1, 3, 5).grid(row=row, column=1, sticky="ew")
        row += 1

        analyst_frame = ttk.LabelFrame(frame, text="Analysts")
        analyst_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        for i, (name, var) in enumerate(ANALYSTS):
            ttk.Checkbutton(analyst_frame, text=name, variable=var).grid(row=0, column=i, padx=5)
        row += 1

        key_frame = ttk.LabelFrame(frame, text="API Keys (leave blank to use environment)")
        key_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        self.key_vars = {}
        for idx, key_name in enumerate(["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY", "FINNHUB_API_KEY"]):
            ttk.Label(key_frame, text=key_name + ":").grid(row=idx, column=0, sticky=tk.W)
            var = tk.StringVar(value=os.getenv(key_name, ""))
            self.key_vars[key_name] = var
            ttk.Entry(key_frame, textvariable=var, show="*", width=40).grid(row=idx, column=1, sticky="ew")
        row += 1

        ttk.Button(frame, text="Run Analysis", command=self.run_analysis).grid(row=row, column=0, columnspan=2, pady=10)
        row += 1

        self.output = scrolledtext.ScrolledText(frame, height=15)
        self.output.grid(row=row, column=0, columnspan=2, sticky="nsew")
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(row, weight=1)

    def _update_models(self, *_):
        provider = self.provider_var.get()
        quick_options = QUICK_MODELS.get(provider, [])
        deep_options = DEEP_MODELS.get(provider, [])
        if quick_options:
            self.quick_model_var.set(quick_options[0])
        if deep_options:
            self.deep_model_var.set(deep_options[0])
        self.quick_menu["menu"].delete(0, "end")
        for opt in quick_options:
            self.quick_menu["menu"].add_command(label=opt, command=lambda v=opt: self.quick_model_var.set(v))
        self.deep_menu["menu"].delete(0, "end")
        for opt in deep_options:
            self.deep_menu["menu"].add_command(label=opt, command=lambda v=opt: self.deep_model_var.set(v))

    def run_analysis(self):
        try:
            datetime.datetime.strptime(self.date_var.get(), "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid date", "Please use YYYY-MM-DD format for the date")
            return
        for key, var in self.key_vars.items():
            if var.get():
                os.environ[key] = var.get()
        selected_analysts = [name.lower() for name, var in ANALYSTS if var.get()]
        if not selected_analysts:
            messagebox.showerror("No analysts", "Please select at least one analyst")
            return
        config = DEFAULT_CONFIG.copy()
        config["max_debate_rounds"] = self.depth_var.get()
        config["max_risk_discuss_rounds"] = self.depth_var.get()
        config["quick_think_llm"] = self.quick_model_var.get()
        config["deep_think_llm"] = self.deep_model_var.get()
        config["llm_provider"] = self.provider_var.get()
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, "Running analysis...\n")
        threading.Thread(target=self._run_graph, args=(selected_analysts, config), daemon=True).start()

    def _run_graph(self, analysts, config):
        try:
            graph = TradingAgentsGraph(analysts, debug=False, config=config)
            _, decision = graph.propagate(self.ticker_var.get(), self.date_var.get())
            self.output.insert(tk.END, f"\nFinal Decision:\n{decision}\n")
        except Exception as e:
            self.output.insert(tk.END, f"\nError: {e}\n")


def main():
    app = TradingAgentsGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
