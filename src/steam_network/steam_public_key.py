from rsa import PublicKey

class SteamPublicKey:
    """
        Essentially a named Tuple containing a Public Key and an associated timestamp.

        It's easier to do it this way because it's relatively immutable (but it's python, so it's not), but more importantly, easier to null out both at once.
    """
    def __init__(self, pKey: PublicKey, ts: int):
        self._pKey = pKey
        self._ts = ts

    @property
    def rsa_public_key(self):
        return self._pKey

    @property
    def timestamp(self):
        return self._ts