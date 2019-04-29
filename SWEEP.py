"""
    "Userspace Sweeper": Moves all the pages from an old userspace to their new name, and updates any links accordingly.
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
regexdict = dict()
titlelist = set()

# Prompt user for the old & new usernames
source = input("\nOld username: ")
destination = input("\nNew username: ")
if source == "" or destination == "":
    logout(url, session)

# Retrieve all userspace pages (except the root page, but those were moved when the username changed)
params_olduserpages = {
    'action':"query",
    'list':"allpages",
    'apprefix':source + "/",
    'apnamespace':2,
    'aplimit':"max",
    'format':"json"
}
params_oldtalkpages = {
    'action':"query",
    'list':"allpages",
    'apprefix':source + "/",
    'apnamespace':3,
    'aplimit':"max",
    'format':"json"
}

oldpages = apiget(url, params_olduserpages, session)['query']['allpages']
oldtalks = apiget(url, params_oldtalkpages, session)['query']['allpages']
pagelist = set()
for page in oldpages:
    pagelist.add(page['title'])
for page in oldtalks:
    pagelist.add(page['title'])

# Move the pages
regexdict = dict()
for page in pagelist:
    newpage = re.sub(r'^User:' + source, 'User:' + destination, page)
    newpage = re.sub(r'^User talk:' + source, 'User talk:' + destination, newpage)
    params_move = {
        'action':"move",
        'from':page,
        'to':newpage,
        'reason':"Username change",
        'noredirect':"yes",
        'format':"json",
        'token':edittoken
    }
    
    moveresult = apipost(url, params_move, session)
    
    try:
        print("'" + moveresult['move']['from'] + "' moved to '" + moveresult['move']['to'] + "'.")
        # Build the regex for finding links
        regex = re.compile("\[+" + page.replace(" ", "[_ ]").replace(":", "\:[_ ]{0,1}") + "[_ ]{0,1}(?=[\]\|#])", re.I) # This covers most wikilinks
        
        # Build the replace string
        replace = "[[" + newpage
        
        # Save to dictionary
        regexdict.update({regex:replace})
    except KeyError:
        print("'" + page + "' to " newpage + "':" + moveresult['error']['info'])

# Get list of pages with links to fix
fixlist = set()
for page in pagelist:
    params_linkshere = {
        'action':"query",
        'prop':"linkshere",
        'titles':page,
        'lhlimit':"max",
        'format':"json"
    }
    
    try:
        linkshere = apiget(url, params_linkshere, session)['query']['pages']["-1"]['linkshere'] # -1 will be provided as a placeholder for the page id for any missing page
        for p in linkshere:
            fixlist.add(p['title'])
    except KeyError:
        continue

# Save a copy of the link fix list and the regex dictionary, in case the script crashes
with open("US-fixlist.txt", "a") as savelist:
    for f in fixlist:
        line = f + "\n"
        savelist.write(line)
with open("US-regex.txt", "a") as savedict:
    for r in regexdict:
        line = str(r) + " : " + regexdict[r] + "\n"
        savedict.write(line)

# Fix links
for title in fixlist:
    # Get page wikitext
    params_listentry = {
        'action':"parse",
        'prop':"wikitext",
        'page':title,
        'format':"json"
    }
    
    # Make replacements
    pagetext = apiget(url, params_listentry, session)['parse']['wikitext']['*']
    for a, b in regexdict.items():
        pagetext = re.sub(a, b, pagetext)

    # Commit the edit
    params_editpage = {
        'action':"edit",
        'title':title,
        'bot':"true",
        'summary':"Updating links of moved pages",
        'text':pagetext,
        'token':edittoken,
        'format':"json"
    }
    
    editcommit = apipost(url, params_editpage, session)
    try:
        status = editcommit['edit']['result']
        if status == 'Success':
            print("Links on '" + title + "' updated.")
        else:
            raise KeyError
    except KeyError:
        print("WARNING: Success message not received for '" + title + "'!")
        
logout(url, session)