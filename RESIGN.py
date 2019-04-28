"""
    "RESIGN bot": Nukes a userspace as per a PvX:RESIGN request
"""

import re
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

# Using the main account for login is not supported. Obtain credentials via Special:BotPasswords
username = input("Bot username: ")
password = getpass("Bot password: ")
url = "https://gwpvx.gamepedia.com/api.php"
session = requests.Session()

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
input("Login " + loggedin + "!")
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

# Prompt for the username
username = input("\nUsername: ")

if username == "":
    apipost(url, {'action':"logout",'format':"json"}, session)
    print("Logged out.")
    raise SystemExit()

# Retrieve all userspace subpages
params_userpages = {
    'action':"query",
    'list':"allpages",
    'apprefix':username,
    'apnamespace':2,
    'aplimit':"max",
    'format':"json"
}
params_usertalks = {
    'action':"query",
    'list':"allpages",
    'apprefix':username,
    'apnamespace':3,
    'aplimit':"max",
    'format':"json"
}

userpages = apiget(url, params_userpages, session)['query']['allpages']
usertalks = apiget(url, params_usertalks, session)['query']['allpages']
pagelist = set()
for page in userpages:
    if re.search("User:" + username + "(/|$)", page['title']) != None:
        pagelist.add(page['title'])
for page in usertalks:
    if re.search("User talk:" + username + "(/|$)", page['title']) != None:
        pagelist.add(page['title'])

# Confirm the pages to be deleted
response = input(str(len(pagelist)) + ' pages to be deleted. Continue? (y/n) ')
if response != 'y':
    apipost(url, {'action':"logout",'format':"json"}, session)
    print("Logged out.")
    raise SystemExit()

# Save list of pages, in case mass undelete is needed
with open("RESIGN-" + username + ".txt", "a") as savelist:
    for p in pagelist:
        line = p + "\n"
        savelist.write(line)

# Delete the pages
for page in pagelist:
    params_delete = {
        'action':"delete",
        'title':page,
        'reason':"[[PvX:RESIGN]]",
        'format':"json",
        'token':edittoken
    }
    
    try:
        apipost(url, params_delete, session)['delete']
        print("'" + page + "' deleted.")
    except KeyError:
        print("Could not delete '" + page + "'. Error code: " + result['error']['code'])

# Logout
apipost(url, {'action':"logout",'format':"json"}, session)
print("Logged out.")

