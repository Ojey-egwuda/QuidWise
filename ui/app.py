"""
MoneyMind UK - World-Class Streamlit Interface
Personal Finance Assistant for UK Residents
"""
import streamlit as st
import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.orchestrator import QuidWiseAgent
from tools.tax_calculator import UKTaxCalculator
from tools.transaction_parser import TransactionParser
from models.schemas import StudentLoanPlan

# Page config
st.set_page_config(
    page_title="QuidWise | Smart Money for the UK",
    page_icon="💷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Custom metric styling */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
    }
    
    /* Tab styling - WORKS IN BOTH LIGHT AND DARK MODE */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 10px 20px;
        background-color: #374151 !important;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
        color: white !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #4B5563 !important;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50 !important;
        color: white !important;
    }
    
    /* Force text color on all tab elements */
    .stTabs [data-baseweb="tab"] * {
        color: white !important;
    }
    
    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] span,
    .stTabs [data-baseweb="tab"] div {
        color: white !important;
    }
    
    /* Card-like containers */
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 10px 0;
    }
    
    /* Footer styling */
    .footer-container {
        margin-top: 50px;
        padding: 20px;
        border-top: 1px solid #e0e0e0;
        text-align: center;
    }
    
    /* Divider */
    .section-divider {
        margin: 30px 0;
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #667eea, transparent);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    st.session_state.agent = None
if "csv_content" not in st.session_state:
    st.session_state.csv_content = None
if "holdings" not in st.session_state:
    st.session_state.holdings = []


def init_agent():
    """Initialize the QuidWise agent"""
    if st.session_state.agent is None:
        try:
            st.session_state.agent = QuidWiseAgent()
        except Exception as e:
            st.error(f"Failed to initialize agent: {e}")
            st.info("Make sure OPENAI_API_KEY is set in your environment")


def format_currency(amount: float) -> str:
    """Format number as GBP currency"""
    return f"£{amount:,.2f}"


def create_gauge_chart(value: float, title: str, max_value: float = 100, suffix: str = "%"):
    """Create a gauge chart for rates"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'suffix': suffix, 'font': {'size': 40}},
        title={'text': title, 'font': {'size': 16}},
        gauge={
            'axis': {'range': [0, max_value], 'tickwidth': 1},
            'bar': {'color': "#667eea"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#e0e0e0",
            'steps': [
                {'range': [0, max_value * 0.3], 'color': '#e8f5e9'},
                {'range': [max_value * 0.3, max_value * 0.6], 'color': '#fff3e0'},
                {'range': [max_value * 0.6, max_value], 'color': '#ffebee'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': "#333", 'family': "Arial"}
    )
    return fig


def create_donut_chart(labels: list, values: list, title: str):
    """Create a donut chart for spending breakdown"""
    colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', 
              '#00f2fe', '#43e97b', '#fa709a', '#fee140', '#30cfd0']
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker_colors=colors[:len(labels)],
        textinfo='label+percent',
        textposition='outside',
        pull=[0.05] * len(labels)
    )])
    
    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=18)),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        height=400,
        margin=dict(l=20, r=20, t=60, b=80),
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig


def create_bar_chart(categories: list, amounts: list, title: str):
    """Create a horizontal bar chart"""
    df = pd.DataFrame({'Category': categories, 'Amount': amounts})
    df = df.sort_values('Amount', ascending=True)
    
    fig = px.bar(
        df, 
        x='Amount', 
        y='Category', 
        orientation='h',
        title=title,
        color='Amount',
        color_continuous_scale=['#667eea', '#764ba2']
    )
    
    fig.update_layout(
        showlegend=False,
        coloraxis_showscale=False,
        height=max(300, len(categories) * 40),
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis_title="Amount (£)",
        yaxis_title=""
    )
    
    fig.update_traces(
        texttemplate='£%{x:,.2f}',
        textposition='outside'
    )
    
    return fig


def render_header():
    """Render the main header"""
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 20px 0;'>
            <h1 style='font-size: 3rem; margin-bottom: 0;'>💷 QuidWise</h1>
            <p style='font-size: 1.2rem; color: #666; margin-top: 10px;'>
                Smart Money for the UK
            </p>
            <p style='font-size: 0.9rem; color: #888;'>
                Tax Calculator • Budget Analyzer • Investment Tracker
            </p>
        </div>
        """, unsafe_allow_html=True)


def render_sidebar():
    """Render sidebar with quick tools and info"""
    with st.sidebar:
        st.markdown("## ⚡ Quick Tax Check")
        
        # Quick Tax Calculator
        salary = st.number_input(
            "Annual Salary (£)", 
            min_value=0, 
            max_value=1000000, 
            value=50000,
            step=1000,
            key="quick_salary",
            help="Enter your gross annual salary"
        )
        
        student_loan = st.selectbox(
            "Student Loan",
            ["None", "Plan 1", "Plan 2", "Plan 4", "Plan 5"],
            key="quick_sl"
        )
        
        if st.button("💰 Calculate", key="quick_calc", use_container_width=True):
            calculator = UKTaxCalculator()
            from models.schemas import TaxInput
            
            sl_map = {
                "None": None,
                "Plan 1": StudentLoanPlan.PLAN_1,
                "Plan 2": StudentLoanPlan.PLAN_2,
                "Plan 4": StudentLoanPlan.PLAN_4,
                "Plan 5": StudentLoanPlan.PLAN_5,
            }
            
            tax_input = TaxInput(
                gross_salary=salary,
                student_loan_plan=sl_map[student_loan]
            )
            
            result = calculator.calculate(tax_input)
            
            st.success(f"**Net Monthly**")
            st.markdown(f"### {format_currency(result.net_monthly_income)}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Net Annual", format_currency(result.net_annual_income))
            with col2:
                st.metric("Tax Rate", f"{result.effective_tax_rate}%")
        
        st.markdown("---")
        
        # Tax Year Badge
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 15px; border-radius: 10px; text-align: center; color: white;'>
            <p style='margin: 0; font-size: 0.9rem;'>📅 Tax Year</p>
            <p style='margin: 5px 0 0 0; font-size: 1.3rem; font-weight: bold;'>2025/26</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Key Rates
        st.markdown("### 📊 Key UK Rates")
        
        rates_data = {
            "Personal Allowance": "£12,570",
            "Basic Rate (20%)": "£0 - £37,700",
            "Higher Rate (40%)": "£37,700 - £125,140",
            "Additional (45%)": "Over £125,140",
            "NI Main Rate": "8%",
            "ISA Allowance": "£20,000"
        }
        
        for label, value in rates_data.items():
            st.markdown(f"**{label}**")
            st.markdown(f"`{value}`")
        
        st.markdown("---")
        
        # Disclaimer
        st.markdown("""
        <div style='background-color: #fff3cd; padding: 15px; border-radius: 8px; 
                    border-left: 4px solid #ffc107;'>
            <p style='margin: 0; font-size: 0.85rem; color: #856404;'>
                ⚠️ <strong>Disclaimer</strong><br>
                This tool is for informational purposes only. 
                Always consult a qualified professional for financial advice.
            </p>
        </div>
        """, unsafe_allow_html=True)


def render_chat_tab():
    """Render the main chat interface"""
    st.markdown("### 💬 Ask QuidWise Anything")
    st.markdown("_Get instant answers about UK tax, budgeting, and investments_")
    
    # Example questions
    with st.expander("💡 Example Questions", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **Tax Questions:**
            - What's my take-home on £50,000?
            - Am I in the 60% tax trap at £105k?
            - How much pension to escape the trap?
            """)
        with col2:
            st.markdown("""
            **Investment Questions:**
            - Track my portfolio: 50 VWRL.L at £95
            - What's the current GBP to USD rate?
            - How much ISA allowance is left?
            """)
    
    st.markdown("---")
    
    # Chat container
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar="🧑‍💼" if message["role"] == "user" else "🤖"):
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask about UK tax, budgeting, or investments..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🧑‍💼"):
            st.markdown(prompt)
        
        # Get agent response
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                init_agent()
                if st.session_state.agent:
                    response = st.session_state.agent.chat(prompt)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    st.error("Agent not initialized. Please check your API key.")
    
    # Clear chat button
    if st.session_state.messages:
        st.markdown("---")
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()


def render_tax_tab():
    """Render detailed tax calculator"""
    st.markdown("### 🧮 UK Tax Calculator 2025/26")
    st.markdown("_Calculate your exact take-home pay with all deductions_")
    
    st.markdown("---")
    
    # Employment Type Selection
    st.markdown("#### 💼 Employment Type")
    employment_type = st.radio(
        "Is this your primary or secondary job?",
        ["Primary Job (uses Personal Allowance)", "Secondary Job / Additional Income (no Personal Allowance)"],
        horizontal=True,
        help="Secondary jobs use BR tax code - you don't get Personal Allowance as it's used by your primary job"
    )
    is_secondary_job = employment_type.startswith("Secondary")
    
    if is_secondary_job:
        st.info("💡 **Secondary Job Selected**: No Personal Allowance will be applied. This is correct if your PA is already used by your main employment.")
    
    st.markdown("---")
    
    # Input Section
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 💷 Income")
        gross_salary = st.number_input(
            "Annual Gross Salary (£)",
            min_value=0,
            max_value=1000000,
            value=50000,
            step=1000,
            format="%d"
        )
        
        bonus = st.number_input(
            "Annual Bonus (£)",
            min_value=0,
            max_value=500000,
            value=0,
            step=500
        )
    
    with col2:
        st.markdown("#### 🎓 Student Loans")
        student_loan = st.selectbox(
            "Loan Plan",
            ["None", "Plan 1 (pre-2012)", "Plan 2 (post-2012)", "Plan 4 (Scotland)", "Plan 5 (post-2023)"]
        )
        
        has_pg_loan = st.checkbox("Postgraduate Loan", help="6% above £21,000 threshold")
    
    with col3:
        st.markdown("#### 🏦 Pension")
        pension_pct = st.slider(
            "Contribution (%)",
            min_value=0,
            max_value=40,
            value=5
        )
        
        salary_sacrifice = st.checkbox(
            "Salary Sacrifice",
            help="More tax efficient - reduces gross before tax/NI"
        )
    
    st.markdown("---")
    
    # Calculate button
    if st.button("📊 Calculate My Tax", type="primary", use_container_width=True):
        calculator = UKTaxCalculator()
        
        sl_map = {
            "None": None,
            "Plan 1 (pre-2012)": StudentLoanPlan.PLAN_1,
            "Plan 2 (post-2012)": StudentLoanPlan.PLAN_2,
            "Plan 4 (Scotland)": StudentLoanPlan.PLAN_4,
            "Plan 5 (post-2023)": StudentLoanPlan.PLAN_5,
        }
        
        from models.schemas import TaxInput
        tax_input = TaxInput(
            gross_salary=gross_salary,
            bonus=bonus,
            student_loan_plan=sl_map[student_loan],
            has_postgraduate_loan=has_pg_loan,
            pension_contribution_percent=pension_pct,
            salary_sacrifice_pension=salary_sacrifice,
            is_secondary_job=is_secondary_job
        )
        
        result = calculator.calculate(tax_input)
        
        # Results Header
        st.markdown("---")
        st.markdown("## 📋 Your Tax Breakdown")
        
        # Key Metrics Row
        m1, m2, m3, m4 = st.columns(4)
        
        with m1:
            st.metric(
                "💰 Gross Income",
                format_currency(result.gross_income),
                help="Your total income before any deductions"
            )
        
        with m2:
            st.metric(
                "📉 Total Deductions",
                format_currency(result.total_deductions),
                delta=f"-{result.effective_tax_rate}%",
                delta_color="inverse",
                help="Income Tax + NI + Student Loans + Pension"
            )
        
        with m3:
            st.metric(
                "💵 Net Annual",
                format_currency(result.net_annual_income),
                help="Your take-home pay per year"
            )
        
        with m4:
            st.metric(
                "📆 Net Monthly",
                format_currency(result.net_monthly_income),
                help="Your take-home pay per month"
            )
        
        st.markdown("---")
        
        # Detailed Breakdown
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🏛️ Income Tax Breakdown")
            
            tax_data = {
                'Band': ['Basic Rate (20%)', 'Higher Rate (40%)', 'Additional Rate (45%)'],
                'Annual': [result.income_tax_basic, result.income_tax_higher, result.income_tax_additional],
                'Monthly': [result.income_tax_basic/12, result.income_tax_higher/12, result.income_tax_additional/12]
            }
            tax_df = pd.DataFrame(tax_data)
            tax_df['Annual'] = tax_df['Annual'].apply(lambda x: f"£{x:,.2f}")
            tax_df['Monthly'] = tax_df['Monthly'].apply(lambda x: f"£{x:,.2f}")
            
            st.dataframe(tax_df, use_container_width=True, hide_index=True)
            
            st.markdown(f"**Total Income Tax:** {format_currency(result.total_income_tax)}/year")
        
        with col2:
            st.markdown("#### 📊 Other Deductions")
            
            deductions = [
                ("National Insurance", result.ni_contributions),
                ("Student Loan", result.student_loan_repayment),
                ("Postgraduate Loan", result.postgraduate_loan_repayment),
                ("Pension", result.pension_contribution)
            ]
            
            for name, amount in deductions:
                if amount > 0:
                    col_a, col_b = st.columns([3, 2])
                    with col_a:
                        st.markdown(f"**{name}**")
                    with col_b:
                        st.markdown(f"`{format_currency(amount)}/year`")
        
        st.markdown("---")
        
        # Tax Efficiency Gauges
        st.markdown("#### 📈 Tax Efficiency Metrics")
        
        g1, g2, g3 = st.columns(3)
        
        with g1:
            fig = create_gauge_chart(result.effective_tax_rate, "Effective Tax Rate", max_value=60)
            st.plotly_chart(fig, use_container_width=True)
        
        with g2:
            fig = create_gauge_chart(result.marginal_tax_rate, "Marginal Tax Rate", max_value=80)
            st.plotly_chart(fig, use_container_width=True)
        
        with g3:
            pa_pct = (result.personal_allowance_used / 12570) * 100
            fig = create_gauge_chart(pa_pct, "Personal Allowance Used", max_value=100)
            st.plotly_chart(fig, use_container_width=True)
        
        # Warnings and Tips
        if result.is_secondary_job:
            st.info(
                "ℹ️ **Secondary Job / BR Tax Code**\n\n"
                "No Personal Allowance applied - this is correct as your PA is used by your primary employment. "
                "All income from this job is taxed from the first pound."
            )
        elif result.personal_allowance_used < 12570:
            st.warning(
                f"⚠️ **Personal Allowance Reduced**\n\n"
                f"Due to income over £100,000, you're losing "
                f"**{format_currency(12570 - result.personal_allowance_used)}** in tax-free allowance."
            )
        
        if result.marginal_tax_rate >= 60 and not result.is_secondary_job:
            st.info(
                "💡 **60% Tax Trap Alert!**\n\n"
                "You're in the £100k-£125,140 marginal rate band. Consider increasing pension "
                "contributions to bring income below £100k and restore your Personal Allowance. "
                "This could save you significant tax!"
            )


def render_transactions_tab():
    """Render transaction analysis interface"""
    st.markdown("### 💳 Transaction Analysis")
    st.markdown("_Upload your Monzo statement to analyze spending patterns_")
    
    st.markdown("---")
    
    # Upload Section
    col1, col2 = st.columns([3, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "📤 Upload Monzo CSV Export",
            type=["csv"],
            help="Export from Monzo app: Account → Settings → Export → CSV"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Clear Data", use_container_width=True):
            st.session_state.csv_content = None
            st.rerun()
    
    # How to export guide
    with st.expander("📱 How to Export from Monzo"):
        st.markdown("""
        1. Open the **Monzo app** on your phone
        2. Go to **Account** tab
        3. Tap **Settings** (gear icon)
        4. Select **Export transactions**
        5. Choose your date range
        6. Select **CSV** format
        7. Download and upload here!
        """)
    
    # Store CSV in session state when uploaded
    if uploaded_file:
        # Use utf-8-sig to automatically handle BOM
        csv_content = uploaded_file.read().decode("utf-8-sig")
        st.session_state.csv_content = csv_content
    
    # Process and display data
    if st.session_state.csv_content:
        parser = TransactionParser()
        
        try:
            transactions = parser.parse_auto(st.session_state.csv_content)
            summary = parser.summarize(transactions)
            
            st.markdown("---")
            
            # Summary Metrics
            st.markdown("#### 📊 Summary")
            
            m1, m2, m3, m4 = st.columns(4)
            
            with m1:
                st.metric(
                    "💰 Total Income",
                    format_currency(summary.total_income),
                    help="All incoming transactions"
                )
            
            with m2:
                st.metric(
                    "💸 Total Spending",
                    format_currency(summary.total_spending),
                    help="All outgoing transactions"
                )
            
            with m3:
                delta_color = "normal" if summary.net_flow >= 0 else "inverse"
                st.metric(
                    "📈 Net Flow",
                    format_currency(summary.net_flow),
                    delta=f"{'Surplus' if summary.net_flow >= 0 else 'Deficit'}",
                    delta_color=delta_color
                )
            
            with m4:
                st.metric(
                    "🔢 Transactions",
                    summary.transaction_count,
                    help="Total number of transactions"
                )
            
            if summary.date_range:
                st.caption(f"📅 Period: {summary.date_range[0]} to {summary.date_range[1]}")
            
            st.markdown("---")
            
            # Charts Row
            col1, col2 = st.columns(2)
            
            with col1:
                if summary.spending_by_category:
                    categories = [k.replace("_", " ").title() for k in summary.spending_by_category.keys()]
                    amounts = list(summary.spending_by_category.values())
                    
                    fig = create_donut_chart(categories, amounts, "💰 Spending by Category")
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if summary.top_merchants:
                    merchants = [m[0][:20] for m in summary.top_merchants[:8]]  # Truncate names
                    amounts = [m[1] for m in summary.top_merchants[:8]]
                    
                    fig = create_bar_chart(merchants, amounts, "🏪 Top Merchants")
                    st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # AI Analysis Section
            st.markdown("#### 🤖 AI-Powered Insights")
            
            if st.button("✨ Get AI Analysis", type="primary", use_container_width=True):
                init_agent()
                if st.session_state.agent:
                    with st.spinner("Analyzing your spending patterns..."):
                        response = st.session_state.agent.chat(
                            "Analyze my spending and give me personalized insights and suggestions for improvement.",
                            transaction_csv=st.session_state.csv_content
                        )
                        
                        st.markdown("---")
                        st.markdown(response)
                else:
                    st.error("AI agent not available. Check your OpenAI API key.")
            
            # Detailed Table
            with st.expander("📋 View All Transactions"):
                tx_data = []
                for tx in transactions[:100]:  # Limit to 100 for performance
                    tx_data.append({
                        "Date": tx.date,
                        "Description": tx.description[:40],
                        "Category": tx.category.value.replace("_", " ").title() if tx.category else "Other",
                        "Amount": tx.amount
                    })
                
                tx_df = pd.DataFrame(tx_data)
                tx_df['Amount'] = tx_df['Amount'].apply(lambda x: f"£{x:,.2f}")
                st.dataframe(tx_df, use_container_width=True, hide_index=True)
                
        except Exception as e:
            st.error(f"Error parsing CSV: {e}")
            st.info("Please ensure you've uploaded a valid Monzo CSV export.")


def render_investments_tab():
    """Render investment portfolio interface"""
    st.markdown("### 📈 Investment Portfolio Tracker")
    st.markdown("_Track your stocks, ETFs, and ISA allowance_")
    
    st.markdown("---")
    
    # Add Holdings Section
    st.markdown("#### ➕ Add Holdings")
    
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
    
    with col1:
        new_symbol = st.text_input(
            "Symbol",
            placeholder="e.g., VWRL.L",
            help="Use .L suffix for London Stock Exchange"
        )
    
    with col2:
        new_qty = st.number_input("Quantity", min_value=0.0, step=1.0, value=0.0)
    
    with col3:
        new_cost = st.number_input("Cost Basis (£)", min_value=0.0, step=100.0, value=0.0)
    
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add", use_container_width=True):
            if new_symbol and new_qty > 0:
                st.session_state.holdings.append({
                    "symbol": new_symbol.upper(),
                    "quantity": new_qty,
                    "cost_basis": new_cost if new_cost > 0 else None
                })
                st.rerun()
    
    # Common ETFs Quick Add
    with st.expander("🚀 Quick Add Popular UK ETFs"):
        etf_col1, etf_col2, etf_col3, etf_col4 = st.columns(4)
        
        popular_etfs = [
            ("VWRL.L", "Vanguard All-World"),
            ("VUSA.L", "Vanguard S&P 500"),
            ("ISF.L", "iShares FTSE 100"),
            ("VUKE.L", "Vanguard FTSE 100")
        ]
        
        for i, (symbol, name) in enumerate(popular_etfs):
            col = [etf_col1, etf_col2, etf_col3, etf_col4][i]
            with col:
                if st.button(f"{symbol}", key=f"quick_{symbol}", use_container_width=True):
                    st.session_state.holdings.append({
                        "symbol": symbol,
                        "quantity": 1,
                        "cost_basis": None
                    })
                    st.rerun()
                st.caption(name)
    
    st.markdown("---")
    
    # Display Holdings
    if st.session_state.holdings:
        st.markdown("#### 📊 Your Holdings")
        
        holdings_df = pd.DataFrame(st.session_state.holdings)
        holdings_df['Cost Basis'] = holdings_df['cost_basis'].apply(
            lambda x: format_currency(x) if x else "N/A"
        )
        holdings_df = holdings_df.rename(columns={
            'symbol': 'Symbol',
            'quantity': 'Quantity'
        })[['Symbol', 'Quantity', 'Cost Basis']]
        
        st.dataframe(holdings_df, use_container_width=True, hide_index=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Analyze Portfolio", type="primary", use_container_width=True):
                from tools.yfinance_tool import PortfolioAnalyzer
                
                with st.spinner("Fetching live prices..."):
                    analyzer = PortfolioAnalyzer()
                    summary = analyzer.analyze_holdings(st.session_state.holdings)
                    
                    st.markdown("---")
                    st.markdown("#### 📈 Portfolio Summary")
                    
                    st.metric("💰 Total Value", format_currency(summary.total_value))
                    
                    for holding in summary.holdings:
                        with st.container():
                            hcol1, hcol2, hcol3 = st.columns(3)
                            
                            with hcol1:
                                st.markdown(f"**{holding.symbol}**")
                                st.caption(holding.name[:30])
                            
                            with hcol2:
                                st.metric("Current Value", format_currency(holding.current_value))
                            
                            with hcol3:
                                if holding.gain_loss is not None:
                                    st.metric(
                                        "Gain/Loss",
                                        format_currency(holding.gain_loss),
                                        f"{holding.gain_loss_percent:+.1f}%"
                                    )
                    
                    # Diversification Suggestions
                    suggestions = analyzer.suggest_diversification(summary.holdings)
                    if suggestions:
                        st.markdown("---")
                        st.markdown("#### 💡 Diversification Tips")
                        for suggestion in suggestions:
                            st.info(suggestion)
        
        with col2:
            if st.button("🗑️ Clear All Holdings", use_container_width=True):
                st.session_state.holdings = []
                st.rerun()
    
    st.markdown("---")
    
    # ISA Tracker
    st.markdown("#### 🏦 ISA Allowance Tracker 2025/26")
    
    col1, col2 = st.columns([2, 3])
    
    with col1:
        isa_used = st.number_input(
            "Amount Contributed This Year (£)",
            min_value=0.0,
            max_value=20000.0,
            value=0.0,
            step=500.0
        )
    
    with col2:
        isa_remaining = 20000 - isa_used
        progress = isa_used / 20000
        
        st.markdown(f"**{format_currency(isa_remaining)}** remaining")
        st.progress(progress)
        
        if isa_remaining < 5000:
            st.warning("⚠️ Consider topping up your ISA before April 5th!")
        elif isa_remaining < 10000:
            st.info("💡 You still have room to maximize your tax-free savings.")


def render_footer():
    """Render the footer."""
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 20px 0;'>
            <h4>🤖 Contact the Developer</h4>
            <p>Connect with <strong>Ojonugwa Egwuda</strong> on 
                <a href="https://www.linkedin.com/in/egwudaojonugwa/" target="_blank">LinkedIn</a>
            </p>
            <small style='color: #888;'>© 2025 QuidWise | Built with ❤️ using Streamlit & Claude</small>
        </div>
        """, unsafe_allow_html=True)


def main():
    """Main app entry point"""
    render_header()
    render_sidebar()
    
    # Main tabs with icons
    tab1, tab2, tab3, tab4 = st.tabs([
        "💬 AI Chat", 
        "🧮 Tax Calculator", 
        "💳 Transactions",
        "📈 Investments"
    ])
    
    with tab1:
        render_chat_tab()
    
    with tab2:
        render_tax_tab()
    
    with tab3:
        render_transactions_tab()
    
    with tab4:
        render_investments_tab()
    
    render_footer()


if __name__ == "__main__":
    main()
