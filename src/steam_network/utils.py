from typing import TypeVar, List, Any, Optional, Callable

T = TypeVar("T")

"""Top Level Utilities. This is mostly me Converting python one-liners into their C# Linq equivalent. I think it's easier to read, but i'm probably horribly wrong. 

"""


def First_Or_Null(listOfStuff:List[T], predicate: Callable[[T], bool]) -> Optional[T]:
    return next((f for f in listOfStuff if predicate(f)), "none")

def Any(listOfStuff:List[T], predicate: Callable[[T], bool]) -> bool:
    return any(predicate(f) for f in listOfStuff)

def All(listOfStuff:List[T], predicate: Callable[[T], bool]) -> bool:
    return all(predicate(f) for f in listOfStuff)
