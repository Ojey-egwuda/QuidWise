# 💷 QuidWise 
<a href="https://quidwise.streamlit.app/" target="_blank" rel="noopener noreferrer">
  🚀 Live Demo
</a>

  
</a>

</a>



**Smart Money for the UK** — An AI-powered personal finance assistant built with LangGraph.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Tax Year](https://img.shields.io/badge/tax%20year-2025%2F26-green.svg)

## ✨ Features

### 🧮 UK Tax Calculator (2025/26)

- **HMRC-Accurate** calculations with edge case handling
- Income tax (Basic 20%, Higher 40%, Additional 45%)
- National Insurance Class 1 (8% / 2%)
- Student loans (Plans 1, 2, 4, 5, Postgraduate)
- Pension contributions with salary sacrifice
- Personal Allowance taper (£100k-£125,140 "60% trap")
- Marginal tax rate calculations at exact boundaries

### 💳 Transaction Analysis

- Monzo CSV import with auto-detection
- Generic CSV support (Date/Description/Amount)
- Automatic spending categorization
- Top merchant analysis
- AI-powered spending insights

### 📈 Investment Tracking

- Real-time portfolio valuation (yfinance)
- UK ETF support (LSE .L tickers)
- Gain/loss tracking with cost basis
- ISA allowance monitoring (£20,000)
- Diversification suggestions

### 💱 Currency & Rates

- Bank of England base rate
- Live exchange rates (150+ currencies)
- Currency conversion tool

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI                              │
│              (Tax Calculator • Transactions • Investments)   │
├─────────────────────────────────────────────────────────────┤
│                   QuidWise Agent                             │
│            LangGraph ReAct Pattern + Tool Loop               │
├─────────────┬─────────────┬─────────────┬───────────────────┤
│ calculate_  │ parse_bank_ │ get_stock_  │ convert_money     │
│ tax         │ transactions│ price       │ get_fx_rates      │
├─────────────┴─────────────┴─────────────┴───────────────────┤
│  UK Tax Engine  │  Transaction Parser  │  API Integrations  │
│  (JSON rates)   │  (Monzo/Generic)     │  (BoE/yfinance/FX) │
└─────────────────────────────────────────────────────────────┘
```

### Agentic Pattern

- **Single Agent + Tools** (ReAct pattern)
- LangGraph cyclic workflow with conditional routing
- Tool enforcement via system prompt (no hallucination)
- Message accumulation for multi-turn context

## 🚀 Quick Start

### 1. Clone and Install

```bash
git clone <repo-url>
cd quidwise

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key:
# OPENAI_API_KEY=sk-your-key-here
```

### 3. Run the App

```bash
streamlit run ui/app.py
```

Open `http://localhost:8501` in your browser.

## 💬 Usage Examples

### Tax Calculations

```
You: What's my take-home on £100,000?

QuidWise: Here's your tax breakdown for £100,000:

📊 Summary
• Gross Income: £100,000
• Total Deductions: £31,442.60
• Net Annual: £68,557.40
• Net Monthly: £5,713.12

📈 Tax Efficiency
• Effective Rate: 31.44%
• Marginal Rate: 62% ⚠️

💡 You're in the 60% marginal rate band (£100k-£125,140).
Consider increasing pension contributions to restore your Personal Allowance.
```

### Marginal Rate Analysis

```
You: Why does my marginal rate exceed 50% at £45k with student loans?

QuidWise: At £45,000 with Plan 2 + Postgraduate loan, your marginal rate
is 43% due to LOAN STACKING:

• Income Tax (Basic): 20%
• National Insurance: 8%
• Plan 2 Student Loan: 9%
• Postgraduate Loan: 6%
• Total: 43%

This is different from the 60% PA TAPER trap which only affects £100k-£125k earners.
```

### Transaction Analysis

1. Export CSV from Monzo (Account → Settings → Export)
2. Upload in the Transactions tab
3. Click "Get AI Analysis" for personalized insights

## 📁 Project Structure

```
quidwise/
├── agents/
│   └── orchestrator.py      # LangGraph agent + tools
├── tools/
│   ├── tax_calculator.py    # UK tax engine
│   ├── transaction_parser.py # Bank CSV parsing
│   ├── boe_api.py           # Bank of England API
│   ├── yfinance_tool.py     # Portfolio analysis
│   └── exchange_api.py      # Currency conversion
├── models/
│   └── schemas.py           # Pydantic models
├── ui/
│   └── app.py               # Streamlit interface
├── data/
│   └── tax_rates_2025_26.json
├── tests/
│   └── test_tax_calculator.py
├── requirements.txt
└── README.md
```

## 🧪 Testing

```bash
python tests/test_tax_calculator.py
```

Tests cover:

- All tax bands and thresholds
- Marginal rate boundaries (£100k, £125,140)
- Student loan calculations
- Salary sacrifice vs normal pension
- Input validation (negative values rejected)
- Zero-deduction edge cases

## 📋 Tax Year 2025/26 Rates

| Band               | Threshold          | Rate |
| ------------------ | ------------------ | ---- |
| Personal Allowance | £0 - £12,570       | 0%   |
| Basic Rate         | £12,571 - £50,270  | 20%  |
| Higher Rate        | £50,271 - £125,140 | 40%  |
| Additional Rate    | £125,140+          | 45%  |

**National Insurance**: 8% (£12,570-£50,270), 2% (above)

**Student Loans**:
| Plan | Threshold | Rate |
|------|-----------|------|
| Plan 1 | £24,990 | 9% |
| Plan 2 | £27,295 | 9% |
| Plan 4 | £31,395 | 9% |
| Plan 5 | £25,000 | 9% |
| Postgraduate | £21,000 | 6% |

## ⚠️ Disclaimer

**QuidWise is for informational and educational purposes only.**

- Not financial, tax, or investment advice
- Based on standard UK rates — may not cover all circumstances
- Always consult qualified professionals for major financial decisions

## 👨‍💻 Author

**Ojonugwa Egwuda**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://www.linkedin.com/in/egwudaojonugwa/)

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

Built with ❤️ for UK personal finance | Powered by LangGraph + Streamlit
