from typing import TypeVar, Generic, Callable, List, Optional, Tuple
import multiprocessing
import asyncio

Value = TypeVar("Value")
class Entry(Generic[Value]):
    pass

T = TypeVar("T")
U = TypeVar("U")
class TaskParallelizer(Generic[T, U]):
    def __init__(self,
                action: Callable[[T], U], 
    ):
        self._action: Callable[[T], U] = action

    def parallel_for_async(self, items: List[T]) -> "asyncio.Future[List[U]]":
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def success_lambda(items: List[U]):
            future.set_result(items)

        def failure_lambda(ex : Exception):
            future.set_exception(ex)

        with multiprocessing.Pool() as pool:
            pool.map_async(self._action, items, len(items) / 8, success_lambda, failure_lambda)
        
        return future

