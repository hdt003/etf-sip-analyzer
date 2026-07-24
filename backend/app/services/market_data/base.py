from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd

class BaseMarketDataProvider(ABC):
    @abstractmethod
    def get_price_data(self, symbol_or_code: str) -> Dict[str, Any]:
        """
        Fetch latest market price, historical ATH / Peak NAV, 52W range, and historical timeline.
        Returns dict with keys:
        - symbol_or_code
        - name
        - current_price
        - ath_price
        - ath_date
        - low_52w
        - high_52w
        - history (DataFrame or list of {date, close})
        """
        pass

    @abstractmethod
    def search_assets(self, query: str) -> List[Dict[str, Any]]:
        """
        Search assets matching query.
        """
        pass
