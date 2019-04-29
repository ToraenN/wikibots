"""
    "Oops": Undoes deletion by bot by crawling the delete log.
"""

import requests
from getpass import getpass

def apiget(url, parameters, session):
    apicall = session.get(url=url, params=parameters)
    result = apicall.json()
    return result

def apipost(url, parameters, session):
    apicall = session.post(url=url, data=parameters)
    result = apicall.json()
    return result

def startup(url, session):
    # Using the main account for login is not supported. Obtain credentials via Special:BotPasswords
    # The only permissions you need to give to the bot password are 'high volume editing' and 'edit existing pages'.
    username = input("Bot username: ")
    password = getpass("Bot password: ")
    
    # Retrieve login token first
    params_tokens = {
        'action':"query",
        'meta':"tokens",
        'type':"login",
        'format':"json"
    }
    
    logintoken = apiget(url, params_tokens, session)['query']['tokens']['logintoken']
    
    # Then we can login
    params_login = {
        'action':"login",
        'lgname':username,
        'lgpassword':password,
        'lgtoken':logintoken,
        'format':"json"
    }
    
    loggedin = apipost(url, params_login, session)['login']['result']
    print("Login " + loggedin + "!")
    del params_login, username, password
    if loggedin != 'Success':
        raise SystemExit()
    
    # Get an edit token
    params_edittoken = {
        'action':"query",
        'meta':"tokens",
        'format':"json"
    }
    
    edittoken = apipost(url, params_edittoken, session)['query']['tokens']['csrftoken']
    return edittoken

def logout(url, session):
    apipost(url, {'action':"logout",'format':"json"}, session)
    print("Logged out.")
    raise SystemExit()

url = "https://gwpvx.gamepedia.com/api.php"
session = requests.Session()
edittoken = startup(url, session)
botname = input("Reverse deletions by user: ")

# Check delete log
params_deletecheck = {
    'action':"query",
    'list':"logevents",
    'leprop':"type|title|details|user",
    'letype':"delete",
    'lelimit':"max",
    'leuser':botname,
    'format':"json"
}

deletedlist = apiget(url, params_deletecheck, session)['query']['logevents']
restorelist = list()
for event in deletedlist:
    if event['action'] == 'delete':
        restorelist.append(event['title'])

print("For each entry, enter one of the following:\n'y': restore the page.\n'd': end the script.\nLeave blank to ignore the page.")
for title in restorelist:
    # Skip any entry that is already restored/recreated
    params_existcheck = {
        'action':"query",
        'titles':title,
        'format':"json"
    }
    
    try:
        apiget(url, params_existcheck, session)['query']['pages']['-1']
    except KeyError:
        continue
    
    params_restore = {
        'action':"undelete",
        'title':title,
        'reason':"Reverting accidental deletion.",
        'token':edittoken,
        'format':"json"
    }
    
    response = input("Restore '" + title + "'? ")
    # Restore the page
    if response == 'y':
        try:
            apipost(url, params_restore, session)['undelete']
            print("'" + title + "' restored.")
        except KeyError:
            print("Could not restore '" + title + "'. Error code: " + result['error']['code'])
    # Break the loop -> quit the script
    elif response == 'd':
        break

logout(url, session)