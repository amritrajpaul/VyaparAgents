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

ANALYST_NAMES = ["Market", "Social", "News", "Fundamentals"]

AGENT_TEAMS = {
    "Analyst Team": [
        "Market Analyst",
        "Social Analyst",
        "News Analyst",
        "Fundamentals Analyst",
    ],
    "Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"],
    "Trading Team": ["Trader"],
    "Risk Management": ["Risky Analyst", "Neutral Analyst", "Safe Analyst"],
    "Portfolio Management": ["Portfolio Manager"],
}

class TradingAgentsGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TradingAgents GUI")
        self.geometry("700x750")
        self.agent_status = {
            agent: "pending"
            for agents in AGENT_TEAMS.values()
            for agent in agents
        }
        self.tool_calls = 0
        self.llm_calls = 0
        self.generated_reports = 0
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
        depth_opts = [
            ("Shallow - Quick research, few debate rounds", 1),
            ("Medium - Moderate debate rounds", 3),
            ("Deep - Comprehensive research", 5),
        ]
        self.depth_map = {label: val for label, val in depth_opts}
        self.depth_var = tk.StringVar(value=depth_opts[0][0])
        ttk.OptionMenu(
            frame,
            self.depth_var,
            depth_opts[0][0],
            *[opt[0] for opt in depth_opts],
        ).grid(row=row, column=1, sticky="ew")
        row += 1

        analyst_frame = ttk.LabelFrame(frame, text="Analysts")
        analyst_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        self.analyst_vars = []
        for i, name in enumerate(ANALYST_NAMES):
            var = tk.BooleanVar(value=True)
            self.analyst_vars.append((name, var))
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

        self.progress_bar = ttk.Progressbar(frame, mode="indeterminate")
        self.progress_bar.grid(row=row, column=0, columnspan=2, sticky="ew")
        row += 1

        notebook = ttk.Notebook(frame)
        notebook.grid(row=row, column=0, columnspan=2, sticky="nsew")
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(row, weight=1)

        self.progress_tab = ttk.Frame(notebook)
        self.report_tab = ttk.Frame(notebook)
        notebook.add(self.progress_tab, text="Progress")
        notebook.add(self.report_tab, text="Final Report")

        self.progress_tree = ttk.Treeview(
            self.progress_tab,
            columns=("team", "agent", "status"),
            show="headings",
            height=10,
        )
        for col in ("team", "agent", "status"):
            self.progress_tree.heading(col, text=col.title())
            self.progress_tree.column(col, width=100, anchor="center")
        self.progress_tree.pack(fill=tk.X)
        for team, agents in AGENT_TEAMS.items():
            first = True
            for agent in agents:
                team_name = team if first else ""
                self.progress_tree.insert("", "end", iid=agent, values=(team_name, agent, "pending"))
                first = False
            self.progress_tree.insert("", "end")

        self.progress_text = scrolledtext.ScrolledText(
            self.progress_tab, height=10, state="disabled"
        )
        self.progress_text.pack(fill=tk.BOTH, expand=True)

        self.stats_var = tk.StringVar(value="Tool Calls: 0 | LLM Calls: 0 | Generated Reports: 0")
        ttk.Label(self.progress_tab, textvariable=self.stats_var).pack(fill=tk.X)

        self.report_text = scrolledtext.ScrolledText(self.report_tab, height=15, state="disabled")
        self.report_text.pack(fill=tk.BOTH, expand=True)

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
        selected_analysts = [name.lower() for name, var in self.analyst_vars if var.get()]

        if not selected_analysts:
            messagebox.showerror("No analysts", "Please select at least one analyst")
            return
        config = DEFAULT_CONFIG.copy()
        depth_value = self.depth_map.get(self.depth_var.get(), 1)
        config["max_debate_rounds"] = depth_value
        config["max_risk_discuss_rounds"] = depth_value
        config["quick_think_llm"] = self.quick_model_var.get()
        config["deep_think_llm"] = self.deep_model_var.get()
        config["llm_provider"] = self.provider_var.get()
        self.progress_text.config(state="normal")
        self.progress_text.delete("1.0", tk.END)
        self.progress_text.insert(tk.END, "Running analysis...\n")
        self.progress_text.config(state="disabled")
        self.progress_bar.start(10)
        for agent in self.agent_status:
            self.agent_status[agent] = "pending"
            if self.progress_tree.exists(agent):
                self.progress_tree.set(agent, column="status", value="pending")
        self.tool_calls = 0
        self.llm_calls = 0
        self.generated_reports = 0
        self._refresh_stats()

        self.report_text.config(state="normal")
        self.report_text.delete("1.0", tk.END)
        self.report_text.config(state="disabled")
        threading.Thread(
            target=self._run_graph,
            args=(selected_analysts, config),
            daemon=True,
        ).start()

    def _run_graph(self, analysts, config):
        try:
            graph = TradingAgentsGraph(analysts, debug=True, config=config)
            init_state = graph.propagator.create_initial_state(
                self.ticker_var.get(), self.date_var.get()
            )
            args = graph.propagator.get_graph_args()

            trace = []
            for chunk in graph.graph.stream(init_state, **args):
                if chunk.get("messages"):
                    last_message = chunk["messages"][-1]
                    content = getattr(last_message, "content", str(last_message))
                    role = getattr(
                        last_message,
                        "role",
                        getattr(last_message, "type", type(last_message).__name__),
                    )
                    self.llm_calls += 1
                    if hasattr(last_message, "tool_calls"):
                        self.tool_calls += len(last_message.tool_calls)
                    self._append_progress(f"{role}: {content}")

                # Update statuses based on reports
                if chunk.get("market_report"):
                    self.generated_reports += 1
                    self._update_status("Market Analyst", "completed")
                    if "social" in analysts:
                        self._update_status("Social Analyst", "in_progress")

                if chunk.get("sentiment_report"):
                    self.generated_reports += 1
                    self._update_status("Social Analyst", "completed")
                    if "news" in analysts:
                        self._update_status("News Analyst", "in_progress")

                if chunk.get("news_report"):
                    self.generated_reports += 1
                    self._update_status("News Analyst", "completed")
                    if "fundamentals" in analysts:
                        self._update_status("Fundamentals Analyst", "in_progress")

                if chunk.get("fundamentals_report"):
                    self.generated_reports += 1
                    self._update_status("Fundamentals Analyst", "completed")

                if chunk.get("investment_plan"):
                    self.generated_reports += 1
                    self._update_status("Bull Researcher", "completed")
                    self._update_status("Bear Researcher", "completed")
                    self._update_status("Research Manager", "completed")
                    self._update_status("Trader", "in_progress")

                if chunk.get("trader_investment_plan"):
                    self.generated_reports += 1
                    self._update_status("Trader", "completed")
                    self._update_status("Risky Analyst", "in_progress")

                if chunk.get("final_trade_decision"):
                    self.generated_reports += 1
                    self._update_status("Risky Analyst", "completed")
                    self._update_status("Safe Analyst", "completed")
                    self._update_status("Neutral Analyst", "completed")
                    self._update_status("Portfolio Manager", "completed")

                self._refresh_stats()
                trace.append(chunk)

            final_state = trace[-1]
            decision = graph.process_signal(final_state["final_trade_decision"])
            self._append_progress("\nAnalysis complete\n")
            report = self._build_final_report(final_state)
            self._update_report(report, decision)
        except Exception as e:
            self._append_progress(f"\nError: {e}\n")
        finally:
            self.after(0, self.progress_bar.stop)


    def _append_progress(self, text):
        def _update():
            self.progress_text.config(state="normal")
            self.progress_text.insert(tk.END, text + "\n")
            self.progress_text.see(tk.END)
            self.progress_text.config(state="disabled")

        self.after(0, _update)

    def _update_status(self, agent, status):
        self.agent_status[agent] = status
        self.progress_tree.set(agent, column="status", value=status)

    def _refresh_stats(self):
        self.stats_var.set(
            f"Tool Calls: {self.tool_calls} | LLM Calls: {self.llm_calls} | Generated Reports: {self.generated_reports}"
        )

    def _update_report(self, report, decision):
        def _fill():
            self.report_text.config(state="normal")
            self.report_text.insert(tk.END, report)
            self.report_text.insert(tk.END, f"\n\nFinal Decision:\n{decision}\n")
            self.report_text.see(tk.END)
            self.report_text.config(state="disabled")
            self._refresh_stats()

        self.after(0, _fill)

    def _build_final_report(self, state):
        sections = []
        if state.get("market_report"):
            sections.append("## Market Analysis\n" + state["market_report"])
        if state.get("sentiment_report"):
            sections.append("## Social Sentiment\n" + state["sentiment_report"])
        if state.get("news_report"):
            sections.append("## News Analysis\n" + state["news_report"])
        if state.get("fundamentals_report"):
            sections.append("## Fundamentals Analysis\n" + state["fundamentals_report"])
        if state.get("investment_plan"):
            sections.append("## Research Team Decision\n" + state["investment_plan"])
        if state.get("trader_investment_plan"):
            sections.append("## Trading Team Plan\n" + state["trader_investment_plan"])
        if state.get("final_trade_decision"):
            sections.append("## Portfolio Management Decision\n" + state["final_trade_decision"])
        return "\n\n".join(sections)


def main():
    app = TradingAgentsGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
