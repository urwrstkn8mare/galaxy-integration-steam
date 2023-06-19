from .shared import IS_WIN

if IS_WIN:
    from .win import WinClient as Client
else:
    from .mac import MacClient as Client
