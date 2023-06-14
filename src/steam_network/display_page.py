from abc import ABC, abstractmethod

class DisplayPage(ABC):
    
    @abstractmethod
    def to_view_string(self) -> str:
        pass

    @abstractmethod
    def get_start_uri(self, errored : bool = False, **kwargs:str) -> str:
        pass

    @abstractmethod
    def end_uri(self) -> str:
        pass

    @abstractmethod
    def get_end_uri_regex(self) -> str:
        pass
