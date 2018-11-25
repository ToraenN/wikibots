"""
    "RESIGN bot": Nukes a userspace as per a PvX:RESIGN request
"""

import re
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
    
# Prompt for the username
username = input("\nUsername: ")

if username == "":
    session.post(url, data= {'action':"logout"})
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
apicall = session.get(url=url, params=params_userpages)
result = apicall.json()
userpages = result['query']['allpages']
apicall = session.get(url=url, params=params_usertalks)
result = apicall.json()
usertalks = result['query']['allpages']
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
    session.post(url, data= {'action':"logout"})
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
    
    apicall = session.post(url=url, data=params_delete)
    result = apicall.json()
    
    try:
        result['delete']
        print("'" + page + "' deleted.")
    except KeyError:
        print("Could not delete '" + page + "'. Error code: " + result['error']['code'])

# Logout
session.post(url, data= {'action':"logout"})
