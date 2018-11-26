"""
    "Userspace Sweeper": Moves all the pages from an old userspace to their new name, and updates any links accordingly.
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

regexdict = dict()
titlelist = set()

# Get an edit token
params_edittoken = {
    'action':"query",
    'meta':"tokens",
    'format':"json"
}

apicall = session.post(url, data= params_edittoken)
result = apicall.json()

edittoken = result['query']['tokens']['csrftoken']
    
# Prompt user for the old & new usernames
source = input("\nOld username: ")
destination = input("\nNew username: ")
if source == "" or destination == "":
    session.post(url, data= {'action':"logout"})
    raise SystemExit()

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
apicall = session.get(url=url, params=params_olduserpages)
result = apicall.json()
oldpages = result['query']['allpages']
apicall = session.get(url=url, params=params_oldtalkpages)
result = apicall.json()
oldtalks = result['query']['allpages']
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
    
    apicall = session.post(url=url, data=params_move)
    result = apicall.json()
    
    try:
        print("'" + result['move']['from'] + "' moved to '" + result['move']['to'] + "'.")
        # Build the regex for finding links
        regex = re.compile("\[+" + page.replace(" ", "[_ ]").replace(":", "\:[_ ]{0,1}") + "[_ ]{0,1}(?=[\]\|#])", re.I) # This covers most wikilinks
        
        # Build the replace string
        replace = "[[" + newpage
        
        # Save to dictionary
        regexdict.update({regex:replace})
    except KeyError:
        print("'" + page + "' to " newpage + "':" + result['error']['info'])

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
    apicall = session.get(url=url, params=params_linkshere)
    result = apicall.json()
    try:
        linkshere = result['query']['pages']["-1"]['linkshere'] # -1 will be provided as a placeholder for the page id for any missing page
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
    
    apicall = session.get(url, params= params_listentry)
    result = apicall.json()
    # Make replacements
    pagetext = result['parse']['wikitext']['*']
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
    
    apicall = session.post(url, data= params_editpage)
    result = apicall.json()
    try:
        status = result['edit']['result']
        if status == 'Success':
            print("Links on '" + title + "' updated.")
        else:
            raise KeyError
    except KeyError:
        print("WARNING: Success message not received for '" + title + "'!")
        
# Logout
session.post(url, data= {'action':"logout"})
