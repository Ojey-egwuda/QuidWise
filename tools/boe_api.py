"""
Bank of England API Integration
Fetches interest rates, inflation data, and economic indicators
"""
import httpx
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass


@dataclass
class BOERate:
    """Bank of England rate data point"""
    date: str
    rate: float
    series_name: str


class BankOfEnglandAPI:
    """
    Bank of England Statistical Interactive Database API
    https://www.bankofengland.co.uk/boeapps/database/
    """
    
    BASE_URL = "https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp"
    
    # Key series codes
    SERIES = {
        "bank_rate": "IUDBEDR",           # Official Bank Rate
        "cpi_inflation": "D7BT",           # CPI Annual Rate
        "cpih_inflation": "L55O",          # CPIH Annual Rate
        "rpi_inflation": "CZBH",           # RPI Annual Rate
        "mortgage_rate_2yr": "IUMBV34",    # 2-year fixed mortgage rate
        "mortgage_rate_5yr": "IUMBV37",    # 5-year fixed mortgage rate
        "savings_rate": "IUMB98S",         # Instant access savings rate
    }
    
    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
    
    def _fetch_series(
        self, 
        series_code: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> list[dict]:
        """
        Fetch a data series from BOE API
        
        Returns CSV-like response that we parse
        """
        if not end_date:
            end_date = datetime.now().strftime("%d/%b/%Y")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%d/%b/%Y")
        
        params = {
            "CodeVer": "new",
            "xml.x": "yes",
            "Datefrom": start_date,
            "Dateto": end_date,
            "SeriesCodes": series_code,
            "CSVF": "TN",  # Tab-separated, no header
            "UsingCodes": "Y",
            "VPD": "Y"
        }
        
        try:
            response = self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            # Parse the response (tab-separated: date, value)
            data = []
            for line in response.text.strip().split("\n"):
                if line.strip():
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        try:
                            data.append({
                                "date": parts[0].strip(),
                                "value": float(parts[1].strip())
                            })
                        except (ValueError, IndexError):
                            continue
            
            return data
            
        except httpx.HTTPError as e:
            print(f"BOE API error: {e}")
            return []
    
    def get_bank_rate(self) -> Optional[BOERate]:
        """Get current Bank of England base rate"""
        data = self._fetch_series(self.SERIES["bank_rate"])
        if data:
            latest = data[-1]
            return BOERate(
                date=latest["date"],
                rate=latest["value"],
                series_name="Bank Rate"
            )
        return None
    
    def get_inflation_cpi(self) -> Optional[BOERate]:
        """Get latest CPI inflation rate"""
        data = self._fetch_series(self.SERIES["cpi_inflation"])
        if data:
            latest = data[-1]
            return BOERate(
                date=latest["date"],
                rate=latest["value"],
                series_name="CPI Inflation"
            )
        return None
    
    def get_mortgage_rates(self) -> dict:
        """Get current average mortgage rates"""
        rates = {}
        
        for name, code in [
            ("2_year_fixed", self.SERIES["mortgage_rate_2yr"]),
            ("5_year_fixed", self.SERIES["mortgage_rate_5yr"])
        ]:
            data = self._fetch_series(code)
            if data:
                rates[name] = {
                    "date": data[-1]["date"],
                    "rate": data[-1]["value"]
                }
        
        return rates
    
    def get_savings_rate(self) -> Optional[BOERate]:
        """Get average instant access savings rate"""
        data = self._fetch_series(self.SERIES["savings_rate"])
        if data:
            latest = data[-1]
            return BOERate(
                date=latest["date"],
                rate=latest["value"],
                series_name="Instant Access Savings Rate"
            )
        return None
    
    def get_all_rates(self) -> dict:
        """Get comprehensive economic rates snapshot"""
        bank_rate = self.get_bank_rate()
        inflation = self.get_inflation_cpi()
        mortgage_rates = self.get_mortgage_rates()
        savings_rate = self.get_savings_rate()
        
        return {
            "bank_rate": {
                "rate": bank_rate.rate if bank_rate else None,
                "date": bank_rate.date if bank_rate else None
            },
            "cpi_inflation": {
                "rate": inflation.rate if inflation else None,
                "date": inflation.date if inflation else None
            },
            "mortgage_rates": mortgage_rates,
            "savings_rate": {
                "rate": savings_rate.rate if savings_rate else None,
                "date": savings_rate.date if savings_rate else None
            },
            "real_return": round(
                (savings_rate.rate if savings_rate else 0) - 
                (inflation.rate if inflation else 0), 
                2
            )
        }
    
    def close(self):
        """Close HTTP client"""
        self.client.close()


# Convenience function for tool usage
def get_economic_rates() -> dict:
    """Get UK economic rates - wrapper for LangGraph tool"""
    api = BankOfEnglandAPI()
    try:
        return api.get_all_rates()
    finally:
        api.close()
