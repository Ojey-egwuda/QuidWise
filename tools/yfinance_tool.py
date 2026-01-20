"""
Portfolio Analyzer using yfinance
Fetches stock/ETF data and calculates portfolio metrics
"""
import yfinance as yf
from datetime import datetime
from typing import Optional
from models.schemas import PortfolioHolding, PortfolioSummary


class PortfolioAnalyzer:
    """Analyze investment portfolio using yfinance data"""
    
    # Common UK ETF tickers (London Stock Exchange)
    UK_ETFS = {
        "VWRL.L": "Vanguard FTSE All-World",
        "VUSA.L": "Vanguard S&P 500",
        "VUKE.L": "Vanguard FTSE 100",
        "ISF.L": "iShares Core FTSE 100",
        "SWDA.L": "iShares Core MSCI World",
        "VFEM.L": "Vanguard FTSE Emerging Markets",
        "VMID.L": "Vanguard FTSE 250",
        "VGOV.L": "Vanguard UK Government Bond",
    }
    
    def __init__(self):
        self.holdings: list[PortfolioHolding] = []
    
    def get_quote(self, symbol: str) -> Optional[dict]:
        """Get current price and info for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Try to get price from various fields
            price = (
                info.get("regularMarketPrice") or 
                info.get("currentPrice") or 
                info.get("previousClose")
            )
            
            if price is None:
                # Fallback to history
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = hist["Close"].iloc[-1]
            
            return {
                "symbol": symbol,
                "name": info.get("shortName") or info.get("longName") or symbol,
                "price": price,
                "currency": info.get("currency", "GBP"),
                "change_percent": info.get("regularMarketChangePercent"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
            }
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None
    
    def analyze_holdings(
        self, 
        holdings: list[dict]
    ) -> PortfolioSummary:
        """
        Analyze a list of holdings
        
        holdings: list of {"symbol": str, "quantity": float, "cost_basis": float (optional)}
        """
        analyzed_holdings = []
        total_value = 0.0
        
        for holding in holdings:
            symbol = holding["symbol"]
            quantity = holding["quantity"]
            cost_basis = holding.get("cost_basis")
            
            quote = self.get_quote(symbol)
            
            if quote and quote["price"]:
                current_value = quantity * quote["price"]
                total_value += current_value
                
                gain_loss = None
                gain_loss_percent = None
                if cost_basis:
                    gain_loss = current_value - cost_basis
                    gain_loss_percent = (gain_loss / cost_basis) * 100 if cost_basis else None
                
                analyzed_holdings.append(PortfolioHolding(
                    symbol=symbol,
                    name=quote["name"],
                    quantity=quantity,
                    current_price=quote["price"],
                    current_value=round(current_value, 2),
                    cost_basis=cost_basis,
                    gain_loss=round(gain_loss, 2) if gain_loss else None,
                    gain_loss_percent=round(gain_loss_percent, 2) if gain_loss_percent else None
                ))
        
        return PortfolioSummary(
            total_value=round(total_value, 2),
            holdings=analyzed_holdings,
            currency="GBP",
            last_updated=datetime.now()
        )
    
    def get_historical_performance(
        self, 
        symbol: str, 
        period: str = "1y"
    ) -> Optional[dict]:
        """Get historical performance for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if hist.empty:
                return None
            
            start_price = hist["Close"].iloc[0]
            end_price = hist["Close"].iloc[-1]
            total_return = ((end_price - start_price) / start_price) * 100
            
            return {
                "symbol": symbol,
                "period": period,
                "start_price": round(start_price, 2),
                "end_price": round(end_price, 2),
                "total_return_percent": round(total_return, 2),
                "high": round(hist["Close"].max(), 2),
                "low": round(hist["Close"].min(), 2),
            }
        except Exception as e:
            print(f"Error fetching history for {symbol}: {e}")
            return None
    
    def suggest_diversification(
        self, 
        holdings: list[PortfolioHolding]
    ) -> list[str]:
        """Suggest diversification improvements"""
        suggestions = []
        
        if not holdings:
            return ["Consider starting with a global index fund like VWRL.L"]
        
        # Check for single stock concentration
        total_value = sum(h.current_value for h in holdings)
        for holding in holdings:
            if total_value > 0:
                weight = (holding.current_value / total_value) * 100
                if weight > 30:
                    suggestions.append(
                        f"{holding.symbol} represents {weight:.1f}% of portfolio - "
                        "consider diversifying to reduce concentration risk"
                    )
        
        # Check for geographic diversification
        symbols = [h.symbol for h in holdings]
        has_uk = any(".L" in s for s in symbols)
        has_us = any(not s.endswith(".L") for s in symbols)
        
        if has_uk and not has_us:
            suggestions.append(
                "Portfolio is UK-focused - consider adding US/global exposure"
            )
        
        return suggestions


# Convenience function for tool usage
def analyze_portfolio(holdings: list[dict]) -> dict:
    """Analyze investment portfolio wrapper for LangGraph tool"""
    analyzer = PortfolioAnalyzer()
    summary = analyzer.analyze_holdings(holdings)
    suggestions = analyzer.suggest_diversification(summary.holdings)
    
    return {
        "summary": summary.model_dump(),
        "diversification_suggestions": suggestions
    }


def get_stock_quote(symbol: str) -> dict:
    """Get single stock quote wrapper for LangGraph tool"""
    analyzer = PortfolioAnalyzer()
    quote = analyzer.get_quote(symbol)
    return quote or {"error": f"Could not fetch data for {symbol}"}
