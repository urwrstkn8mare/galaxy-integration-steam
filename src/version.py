__version__ = "0.50.3"
__changelog__ = {
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


