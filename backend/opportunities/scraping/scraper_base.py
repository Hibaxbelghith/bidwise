from abc import ABC, abstractmethod
from typing import Dict, Iterable, List


class BaseOpportunityScraper(ABC):
    source_name: str
    source_url: str
    source_type: str

    @abstractmethod
    def fetch_raw_records(self) -> Iterable[Dict]:
        """
        Return source records with provider-native field names.
        """

    def collect(self) -> List[Dict]:
        return list(self.fetch_raw_records())
