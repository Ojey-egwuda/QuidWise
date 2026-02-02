"""
UK Tax Calculator for 2024/25 Tax Year
Handles income tax, NI, student loans, and pension contributions
"""
import json
from pathlib import Path
from models.schemas import TaxInput, TaxBreakdown, StudentLoanPlan


class UKTaxCalculator:
    def __init__(self):
        # Load tax rates
        rates_path = Path(__file__).parent.parent / "data" / "tax_rates_2025_26.json"
        with open(rates_path) as f:
            self.rates = json.load(f)
    
    def calculate(self, tax_input: TaxInput) -> TaxBreakdown:
        """Calculate complete tax breakdown for given income"""
        # Input validation - financial apps must reject bad data
        if tax_input.gross_salary < 0:
            raise ValueError("Gross salary cannot be negative")
        if tax_input.bonus < 0:
            raise ValueError("Bonus cannot be negative")
        if tax_input.pension_contribution_percent < 0 or tax_input.pension_contribution_percent > 100:
            raise ValueError("Pension contribution must be between 0 and 100 percent")
        
        gross = tax_input.gross_salary + tax_input.bonus
        
        # Calculate pension contribution first (reduces taxable income if salary sacrifice)
        pension_contribution = gross * (tax_input.pension_contribution_percent / 100)
        
        if tax_input.salary_sacrifice_pension:
            # Salary sacrifice: reduces gross before all taxes
            taxable_gross = gross - pension_contribution
        else:
            taxable_gross = gross
        
        # Personal allowance - NOT applied for secondary jobs (BR tax code)
        if tax_input.is_secondary_job:
            personal_allowance = 0.0
            taxable_income = taxable_gross
        else:
            # Primary job: PA applies (tapers for income > £100k)
            personal_allowance = self._calculate_personal_allowance(taxable_gross)
            taxable_income = max(0, taxable_gross - personal_allowance)
        
        # Income tax
        basic, higher, additional = self._calculate_income_tax(taxable_income)
        total_income_tax = basic + higher + additional
        
        # National Insurance
        ni = self._calculate_ni(taxable_gross)
        
        # Student loans
        student_loan = self._calculate_student_loan(
            taxable_gross, 
            tax_input.student_loan_plan
        )
        postgrad_loan = self._calculate_postgraduate_loan(
            taxable_gross
        ) if tax_input.has_postgraduate_loan else 0.0
        
        # Pension tax relief (only if not salary sacrifice)
        pension_tax_relief = 0.0
        if not tax_input.salary_sacrifice_pension and pension_contribution > 0:
            # Basic rate relief given at source, calculate higher/additional rate relief
            if taxable_income > self.rates["income_tax"]["bands"][0]["max"]:
                # Higher rate taxpayer gets extra 20% relief
                higher_rate_portion = min(
                    pension_contribution,
                    taxable_income - self.rates["income_tax"]["bands"][0]["max"]
                )
                pension_tax_relief = higher_rate_portion * 0.20
                
                if taxable_income > self.rates["income_tax"]["bands"][1]["max"]:
                    # Additional rate gets extra 25% relief
                    additional_portion = min(
                        pension_contribution,
                        taxable_income - self.rates["income_tax"]["bands"][1]["max"]
                    )
                    pension_tax_relief += additional_portion * 0.05
        
        # Totals
        total_deductions = (
            total_income_tax + 
            ni + 
            student_loan + 
            postgrad_loan + 
            (pension_contribution if not tax_input.salary_sacrifice_pension else 0)
        )
        
        net_annual = gross - total_deductions
        net_monthly = net_annual / 12
        
        effective_rate = (total_deductions / gross * 100) if gross > 0 else 0
        marginal_rate = self._calculate_marginal_rate(taxable_gross, tax_input)
        
        return TaxBreakdown(
            gross_income=gross,
            taxable_income=taxable_income,
            personal_allowance_used=personal_allowance,
            is_secondary_job=tax_input.is_secondary_job,
            income_tax_basic=basic,
            income_tax_higher=higher,
            income_tax_additional=additional,
            total_income_tax=total_income_tax,
            ni_contributions=ni,
            student_loan_repayment=student_loan,
            postgraduate_loan_repayment=postgrad_loan,
            pension_contribution=pension_contribution,
            pension_tax_relief=pension_tax_relief,
            total_deductions=total_deductions,
            net_annual_income=net_annual,
            net_monthly_income=net_monthly,
            effective_tax_rate=round(effective_rate, 2),
            marginal_tax_rate=round(marginal_rate, 2)
        )
    
    def _calculate_personal_allowance(self, gross: float) -> float:
        """Personal allowance tapers £1 for every £2 over £100k"""
        base_allowance = self.rates["income_tax"]["personal_allowance"]
        taper_threshold = self.rates["income_tax"]["personal_allowance_taper_threshold"]
        
        if gross <= taper_threshold:
            return base_allowance
        
        reduction = (gross - taper_threshold) / 2
        return max(0, base_allowance - reduction)
    
    def _calculate_income_tax(self, taxable_income: float) -> tuple[float, float, float]:
        """Calculate income tax by band"""
        bands = self.rates["income_tax"]["bands"]
        
        basic = higher = additional = 0.0
        remaining = taxable_income
        
        for band in bands:
            if remaining <= 0:
                break
                
            band_max = band["max"] if band["max"] else float("inf")
            band_width = band_max - band["min"]
            taxable_in_band = min(remaining, band_width)
            tax = taxable_in_band * band["rate"]
            
            if band["name"] == "Basic Rate":
                basic = tax
            elif band["name"] == "Higher Rate":
                higher = tax
            elif band["name"] == "Additional Rate":
                additional = tax
            
            remaining -= taxable_in_band
        
        return basic, higher, additional
    
    def _calculate_ni(self, gross: float) -> float:
        """Calculate Class 1 National Insurance"""
        ni_rates = self.rates["national_insurance"]["class_1"]
        
        primary_threshold = ni_rates["primary_threshold_annual"]
        uel = ni_rates["upper_earnings_limit"]
        rate_main = ni_rates["rate_between_thresholds"]
        rate_upper = ni_rates["rate_above_uel"]
        
        if gross <= primary_threshold:
            return 0.0
        
        # NI between threshold and UEL
        ni_main = min(gross, uel) - primary_threshold
        ni_main_amount = ni_main * rate_main
        
        # NI above UEL
        ni_upper_amount = 0.0
        if gross > uel:
            ni_upper = gross - uel
            ni_upper_amount = ni_upper * rate_upper
        
        return ni_main_amount + ni_upper_amount
    
    def _calculate_student_loan(
        self, 
        gross: float, 
        plan: StudentLoanPlan | None
    ) -> float:
        """Calculate student loan repayment"""
        if not plan:
            return 0.0
        
        plan_rates = self.rates["student_loans"].get(plan.value)
        if not plan_rates:
            return 0.0
        
        threshold = plan_rates["threshold"]
        rate = plan_rates["rate"]
        
        if gross <= threshold:
            return 0.0
        
        return (gross - threshold) * rate
    
    def _calculate_postgraduate_loan(self, gross: float) -> float:
        """Calculate postgraduate loan repayment"""
        pg_rates = self.rates["student_loans"]["postgraduate"]
        threshold = pg_rates["threshold"]
        rate = pg_rates["rate"]
        
        if gross <= threshold:
            return 0.0
        
        return (gross - threshold) * rate
    
    def _calculate_marginal_rate(self, gross: float, tax_input: TaxInput) -> float:
        """Calculate marginal tax rate (tax on next £1 earned)"""
        # Calculate what the NEXT pound of income would be taxed at
        # This means checking where gross + 1 falls, not current gross
        
        next_gross = gross + 1
        
        # For secondary jobs, no PA so taxable = gross
        if tax_input.is_secondary_job:
            next_taxable = next_gross
        else:
            next_pa = self._calculate_personal_allowance(next_gross)
            next_taxable = next_gross - next_pa
        
        bands = self.rates["income_tax"]["bands"]
        
        # Determine income tax marginal rate based on where next taxable pound falls
        income_tax_marginal = 0.0
        for band in bands:
            band_max = band["max"] if band["max"] else float("inf")
            if next_taxable > band["min"] and next_taxable <= band_max:
                income_tax_marginal = band["rate"]
                break
            elif next_taxable > band["min"]:
                # Keep going - might be in a higher band
                income_tax_marginal = band["rate"]
        
        # Special case: £100k-£125,140 has 60% effective marginal (PA taper)
        # ONLY applies to primary jobs - secondary jobs don't have PA to lose
        if not tax_input.is_secondary_job:
            taper_threshold = self.rates["income_tax"]["personal_allowance_taper_threshold"]
            if taper_threshold < next_gross <= 125140:
                # Every £2 earned loses £1 of PA, taxed at 40% = extra 20%
                income_tax_marginal = 0.60
        
        # Add NI marginal (based on next gross)
        ni_rates = self.rates["national_insurance"]["class_1"]
        if next_gross > ni_rates["upper_earnings_limit"]:
            ni_marginal = ni_rates["rate_above_uel"]
        elif next_gross > ni_rates["primary_threshold_annual"]:
            ni_marginal = ni_rates["rate_between_thresholds"]
        else:
            ni_marginal = 0.0
        
        # Add student loan marginal (based on next gross)
        sl_marginal = 0.0
        if tax_input.student_loan_plan:
            plan_rates = self.rates["student_loans"].get(tax_input.student_loan_plan.value)
            if plan_rates and next_gross > plan_rates["threshold"]:
                sl_marginal = plan_rates["rate"]
        
        if tax_input.has_postgraduate_loan:
            pg_rates = self.rates["student_loans"]["postgraduate"]
            if next_gross > pg_rates["threshold"]:
                sl_marginal += pg_rates["rate"]
        
        return (income_tax_marginal + ni_marginal + sl_marginal) * 100


# Convenience function for tool usage
def calculate_uk_tax(
    gross_salary: float,
    student_loan_plan: str | None = None,
    has_postgraduate_loan: bool = False,
    pension_contribution_percent: float = 0.0,
    salary_sacrifice_pension: bool = False,
    bonus: float = 0.0,
    is_secondary_job: bool = False
) -> dict:
    """Calculate UK tax - wrapper for LangGraph tool"""
    calculator = UKTaxCalculator()
    
    plan = None
    if student_loan_plan:
        plan = StudentLoanPlan(student_loan_plan)
    
    tax_input = TaxInput(
        gross_salary=gross_salary,
        student_loan_plan=plan,
        has_postgraduate_loan=has_postgraduate_loan,
        pension_contribution_percent=pension_contribution_percent,
        salary_sacrifice_pension=salary_sacrifice_pension,
        bonus=bonus,
        is_secondary_job=is_secondary_job
    )
    
    result = calculator.calculate(tax_input)
    return result.model_dump()
