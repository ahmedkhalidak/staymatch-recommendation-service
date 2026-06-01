from abc import ABC, abstractmethod


class BaseScorer(ABC):
    @abstractmethod
    def score(self, user, candidate, context=None) -> float:
        pass