from typing import TypeVar, Generic, Callable, List, Iterable, cast
import multiprocessing
import asyncio

T = TypeVar("T")
U = TypeVar("U")
async def parallel_map_async(items: Iterable[T], action: Callable[[T], U]) -> List[U]:
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    
    def success_lambda(items: List[U]):
        future.set_result(items)
    
    def failure_lambda(ex : Exception):
        future.set_exception(ex)
    
    with multiprocessing.Pool() as pool:
        pool.map_async(action, items, len(items) / 8, success_lambda, failure_lambda)
    data = await future
    return cast(List[U], data)

        with multiprocessing.Pool() as pool:
            pool.map_async(self._action, items, len(items) / 8, success_lambda, failure_lambda)
        
        return future

