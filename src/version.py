__version__ = "0.53"
__changelog__ = {
    "0.53": '''
    - fix crashes due to pushing big cache multiple times in a row
    - fix crashes due to O(n^2) licenses lookup for big libraries
    - fix crashes due to apps parsing for big libraries
    - workaround issue with improper games cache invalidation for big libraries
    - improved how Steam in/out protobuf traffic is logged
    ''',
    "0.52": '''
    - raise BackendError instead of BackendTimeout when couldn't login with token
    - register steam app ticket with CM before logging and save a new ticket after login
    ''',
    "0.51.2":'''
    - Enhance local game sizes by returning downloading size if game is not fully installed yet
    - Drop attaching obfuscated private ip to login params.
    ''',
    "0.51.1":'''
    - Fixup marking when games cache is ready in situations when part of the cache was already initialized
    - Optimize retrieving subscription status
    - Fixes for rich presence translations for certain games (dota, stellaris)
    ''',
    "0.51":'''
    - Use package access token when retrieving package information, should fix some games not appearing
    ''',
    "0.50.9":'''
    - Refactor games cache for readability and debugging purposses
    - Implement getting local game sizes
    ''',
    "0.50.8":'''
    - Fix crash on potential looping rich presence translation
    - Fix possible 0 owned games sent issue occuring if previous retrieval was stopped mid-way
    ''',
    "0.50.7":'''
    - Use LoginKeyAccepted message post auth
    - Retry using servers from a different cellid (update login params to handle cell id)
    ''',
    "0.50.6":'''
    - Send log off call on plugin shutdown
    - More precise login parameters, up protocol version
    ''',
    "0.50.5":'''
    - Don't get stuck on broken cache in subsequent runs, instead always reimport packages which didn't end up being resolved (Thanks Dugsdghk!)
    - Don't crash protobuf on bytes response in initial rich presence parsing (Thanks Dugsdghk!)
    ''',
    "0.50.4":'''
    - Fix for owned games which are also present in one of family sharings being reported only as family shared. (Thanks for the help Svill and TM-CG!)
    ''',
    "0.50.3":'''
    - Dont endlessly retry auth to not lock user out
    ''',
    "0.50.2":'''
    - Fix missing achievement_id crashing protobuf_client (Thanks MartinCa!)
    - Extended supported result codes from steam auth
    - Increase logging of protobuf responses
    ''',
    "0.50.1":'''
    - Ignore incompatible cache
    ''',
    "0.50": '''
    - Handle potential infinite rich presence translation
    - Return Family sharing games as a subscriptions
    - Dont crash on unknown presence format
    ''',
    "0.49": '''
    - Better handle parsing rich presence from steam
    - Add a cooldown to parsing local files, should fix ssues with large cpu usage during game installation
    - Better flow in case of clicking forgot password during auth ( focus should stay on proper window )
    ''',
    "0.48": '''
    - Cache the results of owned games so the import is possibly immediate in subsequent plugin runs
    ''',
    "0.47": '''
    - Change the logic of sent friend nicknames to always display the username with optional given nickname instead of one of the two
    - Pull steam friends from protobuf communication instead of scrapping website
    - Move authentication to protobuf
    ''',
    "0.46.5": '''
    - Hotfix for some achievements not being properly recognized by Galaxy (Trailing whitespace in names)
    ''',
    "0.46": '''
    - Potential fixes for key error on achievements retrieval
    - Retrieve last_played time from protobuf instead of website scrapping
    ''',
    "0.45": '''
    - Quickfix for plugin crash while getting achievements
    - Restore mechanism to get last_played time if game was launched via Steam
    ''',
    "0.44": '''
    - Achievements and GameTime are now pulled from protobufs instead of scrapping the website
    - Tags are now pulled from protobufs instead of scrapping local files (allows for tags import without installed steam client)
    '''
}
