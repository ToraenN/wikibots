"""
    "Oops": Undoes deletion by bot by crawling the delete log.
"""

import requests

# Either hardcode the credentials here, or use the input boxes. 
# Using the main account for login is not supported. Obtain credentials via Special:BotPasswords
username = input("Bot username: ")
password = input("Bot password: ")
url = "https://gwpvx.gamepedia.com/api.php"
session = requests.Session()

# Retrieve login token first
params_tokens = {
    'action':"query",
    'meta':"tokens",
    'type':"login",
    'format':"json"
}

apicall = session.get(url=url, params=params_tokens)
result = apicall.json()

logintoken = result['query']['tokens']['logintoken']

# Then we can login
params_login = {
    'action':"login",
    'lgname':username,
    'lgpassword':password,
    'lgtoken':logintoken,
    'format':"json"
}

apicall = session.post(url, data=params_login)
result = apicall.json()
loggedin = result['login']['result']
print("Login " + loggedin + "!")
del params_login
if loggedin != 'Success':
    raise SystemExit()

# Get an edit token
params_edittoken = {
    'action':"query",
    'meta':"tokens",
    'format':"json"
}

apicall = session.post(url, data= params_edittoken)
result = apicall.json()

edittoken = result['query']['tokens']['csrftoken']

# Prompt user for bot to correct
botname = input("Bot username: ")

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

apicall = session.get(url=url, params=params_deletecheck)
result = apicall.json()
deletedlist = result['query']['logevents']
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
    
    apicall = session.get(url=url, params=params_existcheck)
    result = apicall.json()
    
    try:
        result['query']['pages']['-1']
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
        apicall = session.post(url=url, data=params_restore)
        result = apicall.json()
        try:
            result['undelete']
            print("'" + title + "' restored.")
        except KeyError:
            print("Could not restore '" + title + "'. Error code: " + result['error']['code'])
    # Break the loop -> quit the script
    elif response == 'd':
        break

# Logout
session.post(url, data= {'action':"logout"})
