"""
Exchange Rate API Integration
Uses free exchangerate-api.com for currency conversion
"""
import httpx
from datetime import datetime
from typing import Optional


class ExchangeRateAPI:
    """
    Free exchange rate API
    https://www.exchangerate-api.com/docs/free
    """
    
    BASE_URL = "https://open.er-api.com/v6/latest"
    
    def __init__(self):
        self.client = httpx.Client(timeout=15.0)
        self._cache: dict = {}
        self._cache_time: Optional[datetime] = None
    
    def get_rates(self, base_currency: str = "GBP") -> Optional[dict]:
        """Get exchange rates for a base currency"""
        # Check cache (valid for 1 hour)
        cache_key = base_currency.upper()
        if (
            self._cache.get(cache_key) and 
            self._cache_time and 
            (datetime.now() - self._cache_time).seconds < 3600
        ):
            return self._cache[cache_key]
        
        try:
            response = self.client.get(f"{self.BASE_URL}/{base_currency}")
            response.raise_for_status()
            data = response.json()
            
            if data.get("result") == "success":
                rates = {
                    "base": data["base_code"],
                    "last_updated": data["time_last_update_utc"],
                    "rates": data["rates"]
                }
                self._cache[cache_key] = rates
                self._cache_time = datetime.now()
                return rates
                
        except httpx.HTTPError as e:
            print(f"Exchange rate API error: {e}")
        
        return None
    
    def convert(
        self, 
        amount: float, 
        from_currency: str, 
        to_currency: str
    ) -> Optional[dict]:
        """Convert amount between currencies"""
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        rates = self.get_rates(from_currency)
        
        if rates and to_currency in rates["rates"]:
            rate = rates["rates"][to_currency]
            converted = amount * rate
            
            return {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "original_amount": amount,
                "converted_amount": round(converted, 2),
                "exchange_rate": rate,
                "last_updated": rates["last_updated"]
            }
        
        return None
    
    def get_common_rates(self) -> dict:
        """Get rates for common currencies from GBP"""
        rates = self.get_rates("GBP")
        
        if not rates:
            return {"error": "Could not fetch rates"}
        
        common_currencies = ["USD", "EUR", "JPY", "AUD", "CAD", "CHF", "INR", "NGN"]
        
        return {
            "base": "GBP",
            "last_updated": rates["last_updated"],
            "rates": {
                curr: rates["rates"].get(curr) 
                for curr in common_currencies 
                if curr in rates["rates"]
            }
        }
    
    def close(self):
        """Close HTTP client"""
        self.client.close()


# Convenience functions for tool usage
def convert_currency(
    amount: float, 
    from_currency: str, 
    to_currency: str
) -> dict:
    """Convert currency - wrapper for LangGraph tool"""
    api = ExchangeRateAPI()
    try:
        result = api.convert(amount, from_currency, to_currency)
        return result or {"error": "Conversion failed"}
    finally:
        api.close()


def get_exchange_rates() -> dict:
    """Get common exchange rates from GBP - wrapper for LangGraph tool"""
    api = ExchangeRateAPI()
    try:
        return api.get_common_rates()
    finally:
        api.close()
