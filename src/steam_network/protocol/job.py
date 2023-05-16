from typing import Optional

class Job:
    """ Holds information used to identify a unique job.

    Currently a glorified tuple. Probably unneccesary. But i like OOP so it's what we're using.
    """
    def __init__(this, identifier : int, name:Optional[str]):
        this._job_id : int = identifier
        this._name : str = name

    @property
    def job_id(self):
        return self._job_id

    @property
    def name(self):
        return self._name