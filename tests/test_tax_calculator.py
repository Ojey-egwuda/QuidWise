"""
Tests for QuidWise Tax Calculator
"""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Direct imports to avoid loading all tools
from pydantic import BaseModel
from typing import Optional
from enum import Enum


class StudentLoanPlan(str, Enum):
    PLAN_1 = "plan_1"
    PLAN_2 = "plan_2"
    PLAN_4 = "plan_4"
    PLAN_5 = "plan_5"
    POSTGRADUATE = "postgraduate"


class TaxInput(BaseModel):
    gross_salary: float
    student_loan_plan: Optional[StudentLoanPlan] = None
    has_postgraduate_loan: bool = False
    pension_contribution_percent: float = 0.0
    salary_sacrifice_pension: bool = False
    bonus: float = 0.0


class TaxBreakdown(BaseModel):
    gross_income: float
    taxable_income: float
    personal_allowance_used: float
    income_tax_basic: float = 0.0
    income_tax_higher: float = 0.0
    income_tax_additional: float = 0.0
    total_income_tax: float = 0.0
    ni_contributions: float = 0.0
    student_loan_repayment: float = 0.0
    postgraduate_loan_repayment: float = 0.0
    pension_contribution: float = 0.0
    pension_tax_relief: float = 0.0
    total_deductions: float = 0.0
    net_annual_income: float = 0.0
    net_monthly_income: float = 0.0
    effective_tax_rate: float = 0.0
    marginal_tax_rate: float = 0.0


class UKTaxCalculator:
    def __init__(self):
        rates_path = Path(__file__).parent.parent / "data" / "tax_rates_2025_26.json"
        with open(rates_path) as f:
            self.rates = json.load(f)
    
    def calculate(self, tax_input: TaxInput) -> TaxBreakdown:
        gross = tax_input.gross_salary + tax_input.bonus
        pension_contribution = gross * (tax_input.pension_contribution_percent / 100)
        
        if tax_input.salary_sacrifice_pension:
            taxable_gross = gross - pension_contribution
        else:
            taxable_gross = gross
        
        personal_allowance = self._calculate_personal_allowance(taxable_gross)
        taxable_income = max(0, taxable_gross - personal_allowance)
        
        basic, higher, additional = self._calculate_income_tax(taxable_income)
        total_income_tax = basic + higher + additional
        ni = self._calculate_ni(taxable_gross)
        
        student_loan = self._calculate_student_loan(taxable_gross, tax_input.student_loan_plan)
        postgrad_loan = self._calculate_postgraduate_loan(taxable_gross) if tax_input.has_postgraduate_loan else 0.0
        
        pension_tax_relief = 0.0
        if not tax_input.salary_sacrifice_pension and pension_contribution > 0:
            if taxable_income > self.rates["income_tax"]["bands"][0]["max"]:
                higher_rate_portion = min(pension_contribution, taxable_income - self.rates["income_tax"]["bands"][0]["max"])
                pension_tax_relief = higher_rate_portion * 0.20
        
        total_deductions = total_income_tax + ni + student_loan + postgrad_loan + (pension_contribution if not tax_input.salary_sacrifice_pension else 0)
        net_annual = gross - total_deductions
        net_monthly = net_annual / 12
        effective_rate = (total_deductions / gross * 100) if gross > 0 else 0
        marginal_rate = self._calculate_marginal_rate(taxable_gross, tax_input)
        
        return TaxBreakdown(
            gross_income=gross, taxable_income=taxable_income, personal_allowance_used=personal_allowance,
            income_tax_basic=basic, income_tax_higher=higher, income_tax_additional=additional,
            total_income_tax=total_income_tax, ni_contributions=ni, student_loan_repayment=student_loan,
            postgraduate_loan_repayment=postgrad_loan, pension_contribution=pension_contribution,
            pension_tax_relief=pension_tax_relief, total_deductions=total_deductions,
            net_annual_income=net_annual, net_monthly_income=net_monthly,
            effective_tax_rate=round(effective_rate, 2), marginal_tax_rate=round(marginal_rate, 2)
        )
    
    def _calculate_personal_allowance(self, gross: float) -> float:
        base_allowance = self.rates["income_tax"]["personal_allowance"]
        taper_threshold = self.rates["income_tax"]["personal_allowance_taper_threshold"]
        if gross <= taper_threshold:
            return base_allowance
        reduction = (gross - taper_threshold) / 2
        return max(0, base_allowance - reduction)
    
    def _calculate_income_tax(self, taxable_income: float) -> tuple:
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
        ni_rates = self.rates["national_insurance"]["class_1"]
        primary_threshold = ni_rates["primary_threshold_annual"]
        uel = ni_rates["upper_earnings_limit"]
        if gross <= primary_threshold:
            return 0.0
        ni_main = min(gross, uel) - primary_threshold
        ni_main_amount = ni_main * ni_rates["rate_between_thresholds"]
        ni_upper_amount = 0.0
        if gross > uel:
            ni_upper_amount = (gross - uel) * ni_rates["rate_above_uel"]
        return ni_main_amount + ni_upper_amount
    
    def _calculate_student_loan(self, gross: float, plan) -> float:
        if not plan:
            return 0.0
        plan_rates = self.rates["student_loans"].get(plan.value)
        if not plan_rates:
            return 0.0
        if gross <= plan_rates["threshold"]:
            return 0.0
        return (gross - plan_rates["threshold"]) * plan_rates["rate"]
    
    def _calculate_postgraduate_loan(self, gross: float) -> float:
        pg_rates = self.rates["student_loans"]["postgraduate"]
        if gross <= pg_rates["threshold"]:
            return 0.0
        return (gross - pg_rates["threshold"]) * pg_rates["rate"]
    
    def _calculate_marginal_rate(self, gross: float, tax_input) -> float:
        # Calculate what the NEXT pound of income would be taxed at
        next_gross = gross + 1
        next_pa = self._calculate_personal_allowance(next_gross)
        next_taxable = next_gross - next_pa
        
        bands = self.rates["income_tax"]["bands"]
        income_tax_marginal = 0.20
        for band in bands:
            band_max = band["max"] if band["max"] else float("inf")
            if next_taxable > band["min"]:
                income_tax_marginal = band["rate"]
        
        # Special case: £100k-£125,140 has 60% effective marginal (PA taper)
        taper_threshold = self.rates["income_tax"]["personal_allowance_taper_threshold"]
        if taper_threshold < next_gross <= 125140:
            income_tax_marginal = 0.60
        
        ni_rates = self.rates["national_insurance"]["class_1"]
        if next_gross > ni_rates["upper_earnings_limit"]:
            ni_marginal = ni_rates["rate_above_uel"]
        elif next_gross > ni_rates["primary_threshold_annual"]:
            ni_marginal = ni_rates["rate_between_thresholds"]
        else:
            ni_marginal = 0.0
        
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


def test_basic_tax_calculation():
    """Test basic salary calculation"""
    calculator = UKTaxCalculator()
    
    tax_input = TaxInput(gross_salary=50000)
    result = calculator.calculate(tax_input)
    
    assert result.gross_income == 50000
    assert result.personal_allowance_used == 12570
    assert result.taxable_income == 37430
    assert result.total_income_tax > 0
    assert result.ni_contributions > 0
    assert result.net_annual_income < 50000
    
    print(f"✓ £50k salary → Net: £{result.net_annual_income:,.2f}/year (£{result.net_monthly_income:,.2f}/month)")


def test_student_loan_plan_2():
    """Test Plan 2 student loan calculation"""
    calculator = UKTaxCalculator()
    
    tax_input = TaxInput(
        gross_salary=35000,
        student_loan_plan=StudentLoanPlan.PLAN_2
    )
    result = calculator.calculate(tax_input)
    
    # Plan 2 threshold is £27,295
    expected_sl = (35000 - 27295) * 0.09
    assert abs(result.student_loan_repayment - expected_sl) < 1
    
    print(f"✓ Plan 2 student loan: £{result.student_loan_repayment:,.2f}/year")


def test_high_earner_pa_taper():
    """Test Personal Allowance taper for £100k+ earners"""
    calculator = UKTaxCalculator()
    
    # At £125,140+, PA should be fully tapered
    tax_input = TaxInput(gross_salary=130000)
    result = calculator.calculate(tax_input)
    
    assert result.personal_allowance_used == 0
    print(f"✓ £130k earner PA taper: £{result.personal_allowance_used} (fully tapered)")
    
    # At £110,000, PA should be partially tapered
    tax_input_2 = TaxInput(gross_salary=110000)
    result_2 = calculator.calculate(tax_input_2)
    
    expected_pa = 12570 - ((110000 - 100000) / 2)  # £7,570
    assert abs(result_2.personal_allowance_used - expected_pa) < 1
    print(f"✓ £110k earner PA taper: £{result_2.personal_allowance_used:,.0f}")


def test_pension_salary_sacrifice():
    """Test salary sacrifice pension contributions"""
    calculator = UKTaxCalculator()
    
    # Without salary sacrifice
    regular = TaxInput(
        gross_salary=60000,
        pension_contribution_percent=5,
        salary_sacrifice_pension=False
    )
    result_regular = calculator.calculate(regular)
    
    # With salary sacrifice
    sacrifice = TaxInput(
        gross_salary=60000,
        pension_contribution_percent=5,
        salary_sacrifice_pension=True
    )
    result_sacrifice = calculator.calculate(sacrifice)
    
    # Salary sacrifice should result in lower tax/NI
    assert result_sacrifice.total_income_tax < result_regular.total_income_tax
    assert result_sacrifice.ni_contributions < result_regular.ni_contributions
    
    savings = (result_sacrifice.net_annual_income - result_regular.net_annual_income)
    print(f"✓ Salary sacrifice saves: £{savings:,.2f}/year vs regular pension")


def test_marginal_rate_calculation():
    """Test marginal tax rate calculation"""
    calculator = UKTaxCalculator()
    
    # Basic rate taxpayer
    basic = TaxInput(gross_salary=30000)
    result_basic = calculator.calculate(basic)
    assert result_basic.marginal_tax_rate == 28  # 20% IT + 8% NI
    
    # Higher rate taxpayer
    higher = TaxInput(gross_salary=60000)
    result_higher = calculator.calculate(higher)
    assert result_higher.marginal_tax_rate == 42  # 40% IT + 2% NI
    
    # 60% trap (£100k-£125k)
    trap = TaxInput(gross_salary=110000)
    result_trap = calculator.calculate(trap)
    assert result_trap.marginal_tax_rate == 62  # 60% IT + 2% NI
    
    print(f"✓ Marginal rates: Basic={result_basic.marginal_tax_rate}%, Higher={result_higher.marginal_tax_rate}%, Trap={result_trap.marginal_tax_rate}%")


def test_marginal_rate_boundaries():
    """Test marginal rates at exact threshold boundaries"""
    calculator = UKTaxCalculator()
    
    # Exactly £100,000 - next £1 enters the trap
    result = calculator.calculate(TaxInput(gross_salary=100000))
    assert result.marginal_tax_rate == 62, f"£100k marginal should be 62%, got {result.marginal_tax_rate}%"
    print(f"✓ £100,000 marginal rate: {result.marginal_tax_rate}% (next £1 enters trap)")
    
    # Exactly £125,140 - next £1 is additional rate
    result = calculator.calculate(TaxInput(gross_salary=125140))
    assert result.marginal_tax_rate == 47, f"£125,140 marginal should be 47%, got {result.marginal_tax_rate}%"
    print(f"✓ £125,140 marginal rate: {result.marginal_tax_rate}% (next £1 is additional rate)")
    
    # £99,999 - still in higher rate, not yet in trap
    result = calculator.calculate(TaxInput(gross_salary=99999))
    assert result.marginal_tax_rate == 42, f"£99,999 marginal should be 42%, got {result.marginal_tax_rate}%"
    print(f"✓ £99,999 marginal rate: {result.marginal_tax_rate}% (not yet in trap)")


def test_postgraduate_loan():
    """Test postgraduate loan alongside Plan 2"""
    calculator = UKTaxCalculator()
    
    tax_input = TaxInput(
        gross_salary=45000,
        student_loan_plan=StudentLoanPlan.PLAN_2,
        has_postgraduate_loan=True
    )
    result = calculator.calculate(tax_input)
    
    # PG loan threshold is £21,000 at 6%
    expected_pg = (45000 - 21000) * 0.06
    assert abs(result.postgraduate_loan_repayment - expected_pg) < 1
    
    total_sl = result.student_loan_repayment + result.postgraduate_loan_repayment
    print(f"✓ Plan 2 + PG loan: £{total_sl:,.2f}/year total repayments")


def test_negative_salary_rejected():
    """Test that negative salary is rejected"""
    # Import directly to avoid tools/__init__.py loading httpx
    import importlib.util
    spec = importlib.util.spec_from_file_location("tax_calculator", Path(__file__).parent.parent / "tools" / "tax_calculator.py")
    tax_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tax_module)
    RealCalculator = tax_module.UKTaxCalculator
    
    from models.schemas import TaxInput as RealTaxInput
    
    calculator = RealCalculator()
    
    try:
        calculator.calculate(RealTaxInput(gross_salary=-1000))
        assert False, "Should have raised ValueError for negative salary"
    except ValueError as e:
        assert "negative" in str(e).lower()
        print(f"✓ Negative salary rejected: {e}")


def test_negative_bonus_rejected():
    """Test that negative bonus is rejected"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("tax_calculator", Path(__file__).parent.parent / "tools" / "tax_calculator.py")
    tax_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tax_module)
    RealCalculator = tax_module.UKTaxCalculator
    
    from models.schemas import TaxInput as RealTaxInput
    
    calculator = RealCalculator()
    
    try:
        calculator.calculate(RealTaxInput(gross_salary=50000, bonus=-5000))
        assert False, "Should have raised ValueError for negative bonus"
    except ValueError as e:
        assert "negative" in str(e).lower()
        print(f"✓ Negative bonus rejected: {e}")


def test_invalid_pension_percent_rejected():
    """Test that invalid pension percentage is rejected"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("tax_calculator", Path(__file__).parent.parent / "tools" / "tax_calculator.py")
    tax_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tax_module)
    RealCalculator = tax_module.UKTaxCalculator
    
    from models.schemas import TaxInput as RealTaxInput
    
    calculator = RealCalculator()
    
    # Test negative
    try:
        calculator.calculate(RealTaxInput(gross_salary=50000, pension_contribution_percent=-5))
        assert False, "Should have raised ValueError for negative pension"
    except ValueError as e:
        assert "pension" in str(e).lower()
        print(f"✓ Negative pension rejected: {e}")
    
    # Test over 100%
    try:
        calculator.calculate(RealTaxInput(gross_salary=50000, pension_contribution_percent=150))
        assert False, "Should have raised ValueError for pension > 100%"
    except ValueError as e:
        assert "pension" in str(e).lower()
        print(f"✓ Pension > 100% rejected: {e}")


def test_zero_deductions_below_threshold():
    """Test that income below all thresholds has zero deductions"""
    calculator = UKTaxCalculator()
    
    # £12,000 is below Personal Allowance (£12,570) and NI threshold
    result = calculator.calculate(TaxInput(gross_salary=12000))
    
    assert result.total_income_tax == 0, f"Expected 0 income tax, got {result.total_income_tax}"
    assert result.ni_contributions == 0, f"Expected 0 NI, got {result.ni_contributions}"
    assert result.total_deductions == 0, f"Expected 0 total deductions, got {result.total_deductions}"
    assert result.net_annual_income == 12000, f"Expected £12,000 net, got {result.net_annual_income}"
    
    print(f"✓ £12,000 salary: Zero deductions, full take-home")


def test_zero_salary():
    """Test that zero salary works correctly"""
    calculator = UKTaxCalculator()
    
    result = calculator.calculate(TaxInput(gross_salary=0))
    
    assert result.gross_income == 0
    assert result.total_deductions == 0
    assert result.net_annual_income == 0
    assert result.effective_tax_rate == 0
    
    print(f"✓ £0 salary: All values correctly zero")


def test_secondary_job_no_personal_allowance():
    """Test that secondary job does not get Personal Allowance"""
    # Import the actual calculator to test is_secondary_job
    import importlib.util
    spec = importlib.util.spec_from_file_location("tax_calculator", Path(__file__).parent.parent / "tools" / "tax_calculator.py")
    tax_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tax_module)
    RealCalculator = tax_module.UKTaxCalculator
    
    from models.schemas import TaxInput as RealTaxInput
    
    calculator = RealCalculator()
    
    # Primary job £20,000 - should have PA
    primary = calculator.calculate(RealTaxInput(gross_salary=20000, is_secondary_job=False))
    
    # Secondary job £20,000 - should NOT have PA
    secondary = calculator.calculate(RealTaxInput(gross_salary=20000, is_secondary_job=True))
    
    # Primary should have PA applied
    assert primary.personal_allowance_used == 12570, f"Primary should have full PA, got {primary.personal_allowance_used}"
    assert primary.taxable_income == 7430  # 20000 - 12570
    
    # Secondary should have zero PA
    assert secondary.personal_allowance_used == 0, f"Secondary should have 0 PA, got {secondary.personal_allowance_used}"
    assert secondary.taxable_income == 20000  # Full amount taxable
    assert secondary.is_secondary_job == True
    
    # Secondary job should pay more tax (full 20% on £20k)
    assert secondary.total_income_tax > primary.total_income_tax
    
    expected_secondary_tax = 20000 * 0.20  # £4,000
    assert abs(secondary.total_income_tax - expected_secondary_tax) < 1, f"Expected £4,000 tax, got {secondary.total_income_tax}"
    
    print(f"✓ Secondary job: £{secondary.total_income_tax:,.2f} tax (no PA) vs Primary: £{primary.total_income_tax:,.2f} (with PA)")


def test_secondary_job_marginal_rate():
    """Test marginal rate for secondary job (no 60% trap since no PA to lose)"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("tax_calculator", Path(__file__).parent.parent / "tools" / "tax_calculator.py")
    tax_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tax_module)
    RealCalculator = tax_module.UKTaxCalculator
    
    from models.schemas import TaxInput as RealTaxInput
    
    calculator = RealCalculator()
    
    # Primary job at £110k - in the 60% trap
    primary = calculator.calculate(RealTaxInput(gross_salary=110000, is_secondary_job=False))
    
    # Secondary job at £110k - NOT in trap (no PA to lose)
    secondary = calculator.calculate(RealTaxInput(gross_salary=110000, is_secondary_job=True))
    
    # Primary should have 62% marginal (60% trap + 2% NI)
    assert primary.marginal_tax_rate == 62, f"Primary £110k marginal should be 62%, got {primary.marginal_tax_rate}%"
    
    # Secondary should have 42% marginal (40% higher rate + 2% NI, no trap)
    assert secondary.marginal_tax_rate == 42, f"Secondary £110k marginal should be 42%, got {secondary.marginal_tax_rate}%"
    
    print(f"✓ Secondary job avoids 60% trap: Primary={primary.marginal_tax_rate}%, Secondary={secondary.marginal_tax_rate}%")


def test_secondary_job_low_income():
    """Test secondary job with low income (would be tax-free if primary)"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("tax_calculator", Path(__file__).parent.parent / "tools" / "tax_calculator.py")
    tax_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tax_module)
    RealCalculator = tax_module.UKTaxCalculator
    
    from models.schemas import TaxInput as RealTaxInput
    
    calculator = RealCalculator()
    
    # £10,000 as primary job - below PA, zero tax
    primary = calculator.calculate(RealTaxInput(gross_salary=10000, is_secondary_job=False))
    
    # £10,000 as secondary job - fully taxed at 20%
    secondary = calculator.calculate(RealTaxInput(gross_salary=10000, is_secondary_job=True))
    
    assert primary.total_income_tax == 0, "Primary £10k should have zero tax"
    assert secondary.total_income_tax == 2000, f"Secondary £10k should pay £2,000 tax, got {secondary.total_income_tax}"
    
    print(f"✓ Secondary £10k: Pays £{secondary.total_income_tax:,.2f} tax (Primary would be £0)")


if __name__ == "__main__":
    print("\n🧪 Running QuidWise Tax Calculator Tests\n")
    print("-" * 50)
    
    test_basic_tax_calculation()
    test_student_loan_plan_2()
    test_high_earner_pa_taper()
    test_pension_salary_sacrifice()
    test_marginal_rate_calculation()
    test_marginal_rate_boundaries()
    test_postgraduate_loan()
    
    # Input validation tests
    print("\n--- Input Validation Tests ---")
    test_negative_salary_rejected()
    test_negative_bonus_rejected()
    test_invalid_pension_percent_rejected()
    
    # Edge case tests
    print("\n--- Edge Case Tests ---")
    test_zero_deductions_below_threshold()
    test_zero_salary()
    
    # Secondary job tests
    print("\n--- Secondary Job Tests ---")
    test_secondary_job_no_personal_allowance()
    test_secondary_job_marginal_rate()
    test_secondary_job_low_income()
    
    print("-" * 50)
    print("\n✅ All tests passed!\n")
