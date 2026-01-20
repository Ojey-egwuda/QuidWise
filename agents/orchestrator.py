"""
QuidWise - LangGraph Orchestrator
AI-powered personal finance assistant for UK residents
"""
import os
from dotenv import load_dotenv
import json
from typing import TypedDict, Annotated, Literal, Sequence
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import tool
import operator

# Load environment variables from .env file
load_dotenv()

# Import tools
from tools.tax_calculator import calculate_uk_tax
from tools.transaction_parser import parse_transactions
from tools.boe_api import get_economic_rates
from tools.yfinance_tool import analyze_portfolio, get_stock_quote
from tools.exchange_api import convert_currency, get_exchange_rates


# Define state with message accumulation
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_query: str
    transaction_data: str | None
    portfolio_data: list | None


# Create LangChain tools from our functions
@tool
def calculate_tax(
    gross_salary: float,
    student_loan_plan: str = None,
    has_postgraduate_loan: bool = False,
    pension_contribution_percent: float = 0.0,
    salary_sacrifice_pension: bool = False,
    bonus: float = 0.0
) -> dict:
    """
    Calculate UK income tax, National Insurance, and student loan repayments.
    
    Args:
        gross_salary: Annual gross salary in GBP
        student_loan_plan: One of 'plan_1', 'plan_2', 'plan_4', 'plan_5', or None
        has_postgraduate_loan: Whether user has a postgraduate loan
        pension_contribution_percent: Percentage of salary contributed to pension
        salary_sacrifice_pension: Whether pension is via salary sacrifice
        bonus: Any bonus amount in GBP
    """
    return calculate_uk_tax(
        gross_salary=gross_salary,
        student_loan_plan=student_loan_plan,
        has_postgraduate_loan=has_postgraduate_loan,
        pension_contribution_percent=pension_contribution_percent,
        salary_sacrifice_pension=salary_sacrifice_pension,
        bonus=bonus
    )


@tool
def parse_bank_transactions(csv_content: str) -> dict:
    """
    Parse bank transaction CSV data and return spending analysis.
    Currently supports Monzo CSV exports.
    
    Args:
        csv_content: Raw CSV content from bank export
    """
    return parse_transactions(csv_content)


@tool
def get_uk_economic_rates() -> dict:
    """
    Get current UK economic rates from Bank of England.
    Returns: Bank Rate, CPI inflation, mortgage rates, savings rates.
    """
    return get_economic_rates()


@tool
def analyze_investment_portfolio(holdings: list[dict]) -> dict:
    """
    Analyze investment portfolio and get current values.
    
    Args:
        holdings: List of holdings, each with 'symbol', 'quantity', and optional 'cost_basis'
                  Example: [{"symbol": "VWRL.L", "quantity": 100, "cost_basis": 8000}]
    """
    return analyze_portfolio(holdings)


@tool
def get_stock_price(symbol: str) -> dict:
    """
    Get current stock/ETF price and info.
    
    Args:
        symbol: Stock ticker symbol (use .L suffix for London Stock Exchange)
    """
    return get_stock_quote(symbol)


@tool
def convert_money(amount: float, from_currency: str, to_currency: str) -> dict:
    """
    Convert money between currencies.
    
    Args:
        amount: Amount to convert
        from_currency: Source currency code (e.g., 'GBP')
        to_currency: Target currency code (e.g., 'USD')
    """
    return convert_currency(amount, from_currency, to_currency)


@tool
def get_fx_rates() -> dict:
    """Get current exchange rates from GBP to common currencies."""
    return get_exchange_rates()


# All tools available
ALL_TOOLS = [
    calculate_tax,
    parse_bank_transactions,
    get_uk_economic_rates,
    analyze_investment_portfolio,
    get_stock_price,
    convert_money,
    get_fx_rates,
]


SYSTEM_PROMPT = """You are QuidWise, a smart personal finance assistant for UK residents.

CRITICAL RULES - YOU MUST FOLLOW THESE:
1. For ANY question about tax, salary, take home pay, income tax, National Insurance, student loans, pension contributions, or marginal rates - you MUST use the calculate_tax tool. NEVER answer tax questions from memory.
2. For ANY question about interest rates, inflation, Bank of England rates - you MUST use get_uk_economic_rates tool.
3. For ANY question about stocks, ETFs, portfolio values - you MUST use get_stock_price or analyze_investment_portfolio tools.
4. For ANY question about currency conversion - you MUST use convert_money or get_fx_rates tools.
5. If transaction data is ALREADY PROVIDED in the message (marked as "ALREADY PARSED"), DO NOT call parse_bank_transactions - just analyze the data given to you.

YOU ARE NOT ALLOWED TO:
- Answer tax questions without calling calculate_tax first
- Quote tax rates, thresholds, or calculations from memory
- Estimate or approximate financial figures
- Say "approximately" or "around" for tax calculations
- Call parse_bank_transactions when data is already provided in the context

YOU MUST ALWAYS:
- Call the appropriate tool FIRST, then explain the results
- Use exact figures from tool responses
- Show the breakdown clearly with £ symbols

When explaining why marginal rates exceed 50%, distinguish between:
1. PA TAPER (60% trap): Only applies £100k-£125,140. Caused by losing Personal Allowance.
2. LOAN STACKING: Applies at any income. IT (20-45%) + NI (8%/2%) + Student Loans (9%) + PG (6%) = up to 68%

Available tools:
- calculate_tax: For ALL tax calculations (income tax, NI, student loans, marginal rates, pension)
- parse_bank_transactions: For analyzing bank CSV exports (ONLY if raw CSV needs parsing)
- get_uk_economic_rates: For Bank of England rates and inflation
- analyze_investment_portfolio: For portfolio analysis
- get_stock_price: For individual stock/ETF prices
- convert_money: For currency conversion
- get_fx_rates: For exchange rates

Tax Year: 2025/26

When asked about marginal tax rates, you MUST call calculate_tax with the salary to get the accurate marginal_tax_rate from the tool response. The £100k-£125,140 band has a 60%+ effective marginal rate due to personal allowance taper - only the tool calculates this correctly.

Always remind users to seek professional advice for major financial decisions.
Format all currency with £ symbol and commas for thousands."""


def create_graph():
    """Create the agent workflow graph"""
    
    # Create LLM with tools
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    llm_with_tools = llm.bind_tools(ALL_TOOLS)
    
    # Agent node
    def agent(state: AgentState):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    # Check if we should continue to tools or end
    def should_continue(state: AgentState) -> Literal["tools", "end"]:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "end"
    
    # Create tool node
    tool_node = ToolNode(ALL_TOOLS)
    
    # Build graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("agent", agent)
    workflow.add_node("tools", tool_node)
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "end": END}
    )
    
    # Tools always return to agent
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()


# Main interface
class QuidWiseAgent:
    """Main interface for QuidWise"""
    
    def __init__(self):
        self.graph = create_graph()
    
    def chat(self, message: str, transaction_csv: str = None, portfolio: list = None) -> str:
        """
        Process a user message
        
        Args:
            message: User's question or request
            transaction_csv: Optional CSV content from bank export
            portfolio: Optional list of holdings for portfolio analysis
        """
        # Build context message if data provided
        context = message
        
        if transaction_csv:
            # Parse the CSV first and create a summary for the AI
            from tools.transaction_parser import TransactionParser
            parser = TransactionParser()
            try:
                transactions = parser.parse_auto(transaction_csv)
                summary = parser.summarize(transactions)
                
                # Build a detailed summary string for the AI
                spending_breakdown = "\n".join([
                    f"  - {cat.replace('_', ' ').title()}: £{amt:.2f}" 
                    for cat, amt in sorted(summary.spending_by_category.items(), key=lambda x: x[1], reverse=True)
                ])
                
                top_merchants_str = "\n".join([
                    f"  - {merchant}: £{amt:.2f}" 
                    for merchant, amt in summary.top_merchants[:10]
                ])
                
                date_range_str = f"{summary.date_range[0]} to {summary.date_range[1]}" if summary.date_range else "Unknown"
                
                context = f"""{message}

[TRANSACTION DATA - ALREADY PARSED - DO NOT CALL parse_bank_transactions TOOL]
Date Range: {date_range_str}
Total Transactions: {summary.transaction_count}
Total Income: £{summary.total_income:,.2f}
Total Spending: £{summary.total_spending:,.2f}
Net Flow: £{summary.net_flow:,.2f}

Spending by Category:
{spending_breakdown}

Top Merchants (by spend):
{top_merchants_str}

Analyze this spending data and provide insights and suggestions. DO NOT call parse_bank_transactions - the data is already parsed above."""
            except Exception as e:
                context = f"{message}\n\n[Error parsing transaction data: {e}]"
        
        if portfolio:
            context = f"{message}\n\n[User has portfolio: {json.dumps(portfolio)}]"
        
        state = {
            "messages": [HumanMessage(content=context)],
            "user_query": message,
            "transaction_data": transaction_csv,
            "portfolio_data": portfolio,
        }
        
        result = self.graph.invoke(state)
        
        # Extract final response
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                return msg.content
        
        return "I couldn't process your request. Please try again."


if __name__ == "__main__":
    # Quick test
    agent = QuidWiseAgent()
    response = agent.chat("What would my take home pay be on a £50,000 salary with a Plan 2 student loan?")
    print(response)
