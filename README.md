# PortfolioOS

> [!CAUTION]
> **This project is in early development and is NOT ready for use.**
> APIs, data formats, and features are unstable and will change without notice. Do not rely on this software for actual financial decisions.

![Status](https://img.shields.io/badge/status-pre--alpha-red)
![License](https://img.shields.io/badge/license-PolyForm%20NC%201.0-blue)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-informational)

PortfolioOS is a local-first, privacy-preserving financial operating system that combines accurate long-term wealth tracking, serious FIRE simulations, and global market intelligence into a single, explainable platform. All data stays on your machine — no logins, no cloud sync, no credential sharing.

- **Portfolio Tracking** — Record and monitor stocks, ETFs, bonds, crypto, real assets, and custom assets with automatic historical gap reconstruction
- **FIRE Simulator** — Monte Carlo simulations across five FIRE types (Lean, Normal, Fat, Coast, Barista) with life event modeling and withdrawal strategy comparison
- **Market Intelligence** — Continuous data pipeline ingesting macro indicators, equity data, and alternative signals with confidence-scored analysis and structured reporting

## Planned Features

- [ ] Manual portfolio entry and CSV/XLSX/JSON import
- [ ] Historical price gap detection and reconstruction
- [ ] Net worth tracking with longitudinal visualization
- [ ] Monte Carlo FIRE simulations (10,000 trials)
- [ ] Multiple FIRE type analysis (Lean/Normal/Fat/Coast/Barista)
- [ ] Life event modeling (job changes, windfalls, expenses)
- [ ] Macro indicator dashboard (FRED data)
- [ ] Equity analysis and sector comparison
- [ ] LLM-powered natural language portfolio queries (LM Studio default)
- [ ] Structured report generation (daily/weekly/monthly)
- [ ] Percentile-based comparative analytics
- [ ] Data export (CSV, JSON, PDF)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| App Shell | Electron |
| Frontend | React 19 + TypeScript + Vite |
| Styling | Tailwind CSS 4 + shadcn/ui |
| Charts | Recharts + Lightweight Charts + D3.js |
| State | Zustand + TanStack Query |
| Analytics Engine | Python (NumPy, Pandas, SciPy) |
| Primary Database | DuckDB |
| App State Database | SQLite |
| LLM (default) | LM Studio (local) |
| LLM (cloud, opt-in) | OpenAI, Anthropic, OpenRouter |

## Getting Started

> Development setup instructions will be added once the project scaffolding is complete.

### Prerequisites

- Node.js 20+
- pnpm
- Python 3.11+
- uv (Python package manager)

### Setup

```bash
git clone https://github.com/Admiralhunter/PortfolioOS.git
cd PortfolioOS
# Setup instructions coming soon
```

## Documentation

- [Product Specification](docs/SPEC.md)
- [Architecture Design](docs/ARCHITECTURE.md)

## Contributing

This project is not yet accepting external contributions. Watch this repository for updates on when contributions will be welcome.

## License

This project is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE).

**This software may not be used for commercial purposes.** See the LICENSE file for full terms. For commercial licensing inquiries, contact the author.

## Disclaimer

PortfolioOS is not a financial advisor. It does not provide financial, investment, tax, or legal advice. All simulations, projections, and analysis are for informational and educational purposes only. Past performance does not guarantee future results. Monte Carlo simulations represent probability distributions, not predictions. Always consult qualified professionals for financial decisions.
