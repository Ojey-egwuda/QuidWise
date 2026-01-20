"""
Pydantic models for QuidWise
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, date
from enum import Enum


class TransactionCategory(str, Enum):
    GROCERIES = "groceries"
    EATING_OUT = "eating_out"
    TRANSPORT = "transport"
    BILLS = "bills"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    HEALTH = "health"
    INCOME = "income"
    TRANSFER = "transfer"
    CASH = "cash"
    SUBSCRIPTIONS = "subscriptions"
    HOUSING = "housing"
    SAVINGS = "savings"
    INVESTMENTS = "investments"
    OTHER = "other"


class Transaction(BaseModel):
    """Single transaction record"""
    date: date
    description: str
    amount: float  # Negative = outgoing, Positive = incoming
    category: Optional[TransactionCategory] = None
    merchant: Optional[str] = None
    raw_category: Optional[str] = None  # Original category from bank


class TransactionSummary(BaseModel):
    """Aggregated transaction analysis"""
    total_income: float = 0.0
    total_spending: float = 0.0
    net_flow: float = 0.0
    spending_by_category: dict[str, float] = Field(default_factory=dict)
    top_merchants: list[tuple[str, float]] = Field(default_factory=list)
    transaction_count: int = 0
    date_range: tuple[date, date] | None = None


class StudentLoanPlan(str, Enum):
    PLAN_1 = "plan_1"
    PLAN_2 = "plan_2"
    PLAN_4 = "plan_4"
    PLAN_5 = "plan_5"
    POSTGRADUATE = "postgraduate"


class TaxInput(BaseModel):
    """Input for tax calculation"""
    gross_salary: float
    student_loan_plan: Optional[StudentLoanPlan] = None
    has_postgraduate_loan: bool = False
    pension_contribution_percent: float = 0.0  # Employee contribution %
    salary_sacrifice_pension: bool = False
    bonus: float = 0.0
    dividend_income: float = 0.0
    rental_income: float = 0.0
    

class TaxBreakdown(BaseModel):
    """Detailed tax calculation result"""
    gross_income: float
    taxable_income: float
    personal_allowance_used: float
    
    # Income Tax
    income_tax_basic: float = 0.0
    income_tax_higher: float = 0.0
    income_tax_additional: float = 0.0
    total_income_tax: float = 0.0
    
    # National Insurance
    ni_contributions: float = 0.0
    
    # Student Loans
    student_loan_repayment: float = 0.0
    postgraduate_loan_repayment: float = 0.0
    
    # Pension
    pension_contribution: float = 0.0
    pension_tax_relief: float = 0.0
    
    # Totals
    total_deductions: float = 0.0
    net_annual_income: float = 0.0
    net_monthly_income: float = 0.0
    effective_tax_rate: float = 0.0
    marginal_tax_rate: float = 0.0


class ISAStatus(BaseModel):
    """ISA allowance tracking"""
    tax_year: str
    total_allowance: float = 20000.0
    used_allowance: float = 0.0
    remaining_allowance: float = 20000.0
    stocks_shares_isa: float = 0.0
    cash_isa: float = 0.0
    lifetime_isa: float = 0.0
    lifetime_isa_bonus_earned: float = 0.0


class PortfolioHolding(BaseModel):
    """Single investment holding"""
    symbol: str
    name: str
    quantity: float
    current_price: float
    current_value: float
    cost_basis: Optional[float] = None
    gain_loss: Optional[float] = None
    gain_loss_percent: Optional[float] = None


class PortfolioSummary(BaseModel):
    """Investment portfolio overview"""
    total_value: float
    holdings: list[PortfolioHolding]
    currency: str = "GBP"
    last_updated: datetime


class BudgetInsight(BaseModel):
    """AI generated budget insight"""
    category: str
    insight: str
    severity: Literal["info", "warning", "alert"]
    potential_savings: Optional[float] = None


class FinancialHealthReport(BaseModel):
    """Complete financial health assessment"""
    tax_breakdown: Optional[TaxBreakdown] = None
    spending_summary: Optional[TransactionSummary] = None
    isa_status: Optional[ISAStatus] = None
    portfolio_summary: Optional[PortfolioSummary] = None
    insights: list[BudgetInsight] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
