"""
Transaction Parser for UK Bank CSV exports
Currently supports: Monzo
Extensible for: Starling, HSBC, Barclays
"""
import csv
import io
from datetime import datetime, date
from collections import defaultdict
from models.schemas import Transaction, TransactionSummary, TransactionCategory


# Monzo category mapping to our standard categories
MONZO_CATEGORY_MAP = {
    "groceries": TransactionCategory.GROCERIES,
    "eating_out": TransactionCategory.EATING_OUT,
    "transport": TransactionCategory.TRANSPORT,
    "bills": TransactionCategory.BILLS,
    "entertainment": TransactionCategory.ENTERTAINMENT,
    "shopping": TransactionCategory.SHOPPING,
    "personal_care": TransactionCategory.HEALTH,
    "health": TransactionCategory.HEALTH,
    "general": TransactionCategory.OTHER,
    "finances": TransactionCategory.SAVINGS,
    "income": TransactionCategory.INCOME,
    "transfers": TransactionCategory.TRANSFER,
    "cash": TransactionCategory.CASH,
    "holidays": TransactionCategory.ENTERTAINMENT,
    "family": TransactionCategory.OTHER,
    "charity": TransactionCategory.OTHER,
    "gifts": TransactionCategory.SHOPPING,
    "expenses": TransactionCategory.OTHER,
}

# Keywords for fallback categorization
CATEGORY_KEYWORDS = {
    TransactionCategory.GROCERIES: [
        "tesco", "sainsbury", "asda", "morrisons", "aldi", "lidl", 
        "waitrose", "co-op", "ocado", "iceland", "m&s food"
    ],
    TransactionCategory.EATING_OUT: [
        "mcdonald", "burger king", "kfc", "nando", "pizza", "domino",
        "uber eats", "deliveroo", "just eat", "costa", "starbucks",
        "pret", "greggs", "cafe", "restaurant", "pub"
    ],
    TransactionCategory.TRANSPORT: [
        "tfl", "uber", "bolt", "trainline", "national rail", "bus",
        "petrol", "shell", "bp", "esso", "parking", "congestion"
    ],
    TransactionCategory.BILLS: [
        "council tax", "water", "thames", "electric", "gas", "energy",
        "british gas", "edf", "octopus", "bulb", "tv licence"
    ],
    TransactionCategory.SUBSCRIPTIONS: [
        "netflix", "spotify", "amazon prime", "disney", "apple",
        "youtube", "gym", "now tv", "sky", "bt", "virgin media"
    ],
    TransactionCategory.HOUSING: [
        "rent", "mortgage", "rightmove", "zoopla", "openrent"
    ],
    TransactionCategory.HEALTH: [
        "pharmacy", "boots", "superdrug", "dentist", "gp", "nhs",
        "specsavers", "vision express"
    ],
}


class TransactionParser:
    """Parse bank CSV exports into standardized transactions"""
    
    def __init__(self):
        self.transactions: list[Transaction] = []
    
    def parse_monzo(self, csv_content: str) -> list[Transaction]:
        """
        Parse Monzo CSV export
        
        Monzo CSV columns:
        Transaction ID, Date, Time, Type, Name, Emoji, Category,
        Amount, Currency, Local amount, Local currency, Notes and #tags,
        Address, Receipt, Description, Category split, Money Out, Money In
        """
        self.transactions = []
        
        # Handle BOM
        csv_content = csv_content.strip()
        if csv_content.startswith('\ufeff'):
            csv_content = csv_content[1:]
        
        reader = csv.DictReader(io.StringIO(csv_content))
        
        for row in reader:
            try:
                # Parse date
                date_str = row.get("Date") or ""
                if not date_str:
                    continue
                tx_date = datetime.strptime(date_str, "%d/%m/%Y").date()
                
                # Parse amount (Monzo has separate Money Out/Money In columns)
                # Use "or" to handle None values
                money_out = (row.get("Money Out") or "").strip()
                money_in = (row.get("Money In") or "").strip()
                
                if money_out:
                    amount = -abs(float(money_out))
                elif money_in:
                    amount = abs(float(money_in))
                else:
                    # Fallback to Amount column
                    amount_str = (row.get("Amount") or "0").strip()
                    amount = float(amount_str) if amount_str else 0
                
                # Get description
                name = (row.get("Name") or "").strip()
                description = (row.get("Description") or "").strip() or name
                
                # Map category
                raw_category = (row.get("Category") or "").lower().strip()
                category = MONZO_CATEGORY_MAP.get(
                    raw_category, 
                    TransactionCategory.OTHER
                )
                
                # Override category based on keywords if generic
                if category == TransactionCategory.OTHER:
                    category = self._categorize_by_keywords(description)
                
                # If it's income (positive amount), mark as income
                if amount > 0 and category not in [
                    TransactionCategory.TRANSFER, 
                    TransactionCategory.INCOME
                ]:
                    if "salary" in description.lower() or "payroll" in description.lower():
                        category = TransactionCategory.INCOME
                
                tx = Transaction(
                    date=tx_date,
                    description=description,
                    amount=amount,
                    category=category,
                    merchant=name,
                    raw_category=raw_category
                )
                self.transactions.append(tx)
                
            except (ValueError, KeyError) as e:
                # Skip malformed rows
                continue
        
        return self.transactions
    
    def _categorize_by_keywords(self, description: str) -> TransactionCategory:
        """Fallback categorization using keywords"""
        desc_lower = description.lower()
        
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in desc_lower for kw in keywords):
                return category
        
        return TransactionCategory.OTHER
    
    def detect_bank_format(self, csv_content: str) -> str:
        """Auto detect which bank the CSV is from"""
        # Handle potential BOM and normalize
        csv_content = csv_content.strip()
        if csv_content.startswith('\ufeff'):
            csv_content = csv_content[1:]
        
        first_line = csv_content.split("\n")[0].lower().strip()
        
        # Monzo detection - check for key Monzo-specific columns
        monzo_indicators = ["transaction id", "emoji", "money out", "money in"]
        monzo_matches = sum(1 for indicator in monzo_indicators if indicator in first_line)
        
        if monzo_matches >= 2:  # At least 2 Monzo indicators
            return "monzo"
        elif "counter party" in first_line:
            return "starling"
        elif "transaction date" in first_line and "transaction description" in first_line:
            return "hsbc"
        elif "transaction date" in first_line and "memo" in first_line:
            return "barclays"
        # Generic CSV with Date, Description, Amount columns
        elif "date" in first_line and "amount" in first_line:
            return "generic"
        else:
            return "unknown"
    
    def parse_generic(self, csv_content: str) -> list[Transaction]:
        """
        Parse generic CSV with Date, Description, Amount columns
        Works with simple bank exports
        """
        self.transactions = []
        
        # Handle BOM
        csv_content = csv_content.strip()
        if csv_content.startswith('\ufeff'):
            csv_content = csv_content[1:]
        
        reader = csv.DictReader(io.StringIO(csv_content))
        
        # Normalize column names (handle case variations)
        fieldnames = reader.fieldnames or []
        col_map = {col.lower().strip(): col for col in fieldnames}
        
        for row in reader:
            try:
                # Find date column (try variations)
                date_str = None
                for key in ["date", "transaction date", "trans date", "posted date"]:
                    if key in col_map:
                        date_str = (row.get(col_map[key]) or "").strip()
                        if date_str:
                            break
                
                if not date_str:
                    continue
                
                # Try multiple date formats
                tx_date = None
                for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d %b %Y", "%d/%m/%y"]:
                    try:
                        tx_date = datetime.strptime(date_str, fmt).date()
                        break
                    except ValueError:
                        continue
                
                if not tx_date:
                    continue
                
                # Find amount column
                amount = 0.0
                for key in ["amount", "debit", "credit", "value"]:
                    if key in col_map:
                        amount_str = (row.get(col_map[key]) or "0").strip()
                        # Remove currency symbols and commas
                        amount_str = amount_str.replace("£", "").replace(",", "").replace("$", "")
                        if amount_str:
                            try:
                                amount = float(amount_str)
                                break
                            except ValueError:
                                continue
                
                # Find description column
                description = ""
                for key in ["description", "name", "merchant", "details", "narrative", "reference"]:
                    if key in col_map:
                        description = (row.get(col_map[key]) or "").strip()
                        if description:
                            break
                
                if not description:
                    description = "Unknown transaction"
                
                # Categorize by keywords
                category = self._categorize_by_keywords(description)
                
                # If positive amount and looks like income
                if amount > 0:
                    desc_lower = description.lower()
                    if any(kw in desc_lower for kw in ["salary", "payroll", "wages", "income", "transfer in"]):
                        category = TransactionCategory.INCOME
                
                tx = Transaction(
                    date=tx_date,
                    description=description,
                    amount=amount,
                    category=category,
                    merchant=description[:50],
                    raw_category=None
                )
                self.transactions.append(tx)
                
            except (ValueError, KeyError) as e:
                continue
        
        return self.transactions
    
    def parse_auto(self, csv_content: str) -> list[Transaction]:
        """Auto detect bank format and parse"""
        # Handle BOM
        csv_content = csv_content.strip()
        if csv_content.startswith('\ufeff'):
            csv_content = csv_content[1:]
        
        bank = self.detect_bank_format(csv_content)
        
        if bank == "monzo":
            return self.parse_monzo(csv_content)
        elif bank == "generic":
            return self.parse_generic(csv_content)
        else:
            # Provide helpful error with detected headers
            first_line = csv_content.split("\n")[0][:200]
            raise ValueError(
                f"Unsupported bank format: {bank}.\n"
                f"Supported formats: Monzo, or generic CSV with Date/Description/Amount columns.\n"
                f"Detected headers: {first_line}..."
            )
    
    def summarize(self, transactions: list[Transaction] | None = None) -> TransactionSummary:
        """Generate summary statistics from transactions"""
        txs = transactions or self.transactions
        
        if not txs:
            return TransactionSummary()
        
        total_income = sum(t.amount for t in txs if t.amount > 0)
        total_spending = abs(sum(t.amount for t in txs if t.amount < 0))
        
        # Spending by category
        spending_by_cat = defaultdict(float)
        for t in txs:
            if t.amount < 0 and t.category:
                spending_by_cat[t.category.value] += abs(t.amount)
        
        # Top merchants
        merchant_totals = defaultdict(float)
        for t in txs:
            if t.amount < 0 and t.merchant:
                merchant_totals[t.merchant] += abs(t.amount)
        
        top_merchants = sorted(
            merchant_totals.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        # Date range
        dates = [t.date for t in txs]
        date_range = (min(dates), max(dates)) if dates else None
        
        return TransactionSummary(
            total_income=round(total_income, 2),
            total_spending=round(total_spending, 2),
            net_flow=round(total_income - total_spending, 2),
            spending_by_category=dict(spending_by_cat),
            top_merchants=top_merchants,
            transaction_count=len(txs),
            date_range=date_range
        )


# Convenience function for tool usage
def parse_transactions(csv_content: str) -> dict:
    """Parse bank transactions and return summary wrapper for LangGraph tool"""
    parser = TransactionParser()
    transactions = parser.parse_auto(csv_content)
    summary = parser.summarize(transactions)
    
    return {
        "transactions": [t.model_dump() for t in transactions],
        "summary": summary.model_dump(),
        "transaction_count": len(transactions)
    }
