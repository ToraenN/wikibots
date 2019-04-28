"""
    "Moved Page Link Fixer": Updates all redlinks to user-provided old pages to point to their new pages.
"""

import re
import requests
from getpass import getpass

def inputint(prompt, limit):
    answer = input(prompt)
    try:
        answer = int(answer)
    except:
        pass
    while (isinstance(answer, int) == False) or (int(answer) not in range(limit)):
        try:
            answer = int(input('Invalid entry, please enter an integer within range: '))
        except:
            pass
    return answer

def apiget(url, parameters, session):
    apicall = session.get(url=url, params=parameters)
    result = apicall.json()
    return result

def apipost(url, parameters, session):
    apicall = session.post(url=url, data=parameters)
    result = apicall.json()
    return result

# Using the main account for login is not supported. Obtain credentials via Special:BotPasswords
# The only permissions you need to give to the bot password are 'high volume editing' and 'edit existing pages'.
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
regexdict = dict()
titlelist = set()

# Get an edit token
params_edittoken = {
    'action':"query",
    'meta':"tokens",
    'format':"json"
}

edittoken = apipost(url, params_edittoken, session)['query']['tokens']['csrftoken']

# Loop until user is done inputting jobs
while loggedin == 'Success':
    # Prompt user for the old name of the page
    source = input("\nOld name: ")
    # Break loop, and thus move to processing, if source is blank.
    if source == "":
        break
    # Get page list, check that something actually links to the source page
    params_linkshere = {
        'action':"query",
        'prop':"linkshere",
        'titles':source,
        'lhlimit':"max",
        'format':"json"
    }

    linkshere = apiget(url, params_linkshere, session)
    try:
        pagelist = linkshere['query']['pages']["-1"]['linkshere'] # -1 will be provided as a placeholder for the page id for any missing page

    except KeyError:
        print("'" + source + "' is not linked to.")
        continue
    # Check move log for destination
    params_movecheck = {
        'action':"query",
        'list':"logevents",
        'leprop':"type|title|details",
        'letype':"move",
        'lelimit':"max",
        'letitle':source,
        'format':"json"
    }
    
    movedlist = apiget(url, params_movecheck, session)['query']['logevents']
    destinations = set()
    # Check if each destination exists
    for event in movedlist:
        movetarget = event['params']['target_title']
        # Chain across multiple moves
        params_movecheck = {
            'action':"query",
            'list':"logevents",
            'leprop':"type|title|details",
            'letype':"move",
            'lelimit':"max",
            'letitle':movetarget,
            'format':"json"
        }
        
        appendlist = apiget(url, params_movecheck, session)['query']['logevents']
        for item in appendlist:
            if not item in movedlist:
                movedlist.append(item)
        # Check the current move event
        params_existcheck = {
            'action':"query",
            'titles':movetarget,
            'format':"json"
        }
        
        destexist = apiget(url, params_existcheck, session)
        try:
            destexist['query']['pages']['-1']
        except KeyError:
            destinations.add(movetarget)
    destinations = list(destinations)
    destination = ""
    # Only display the existing destinations
    if len(destinations) > 0:
        destquery = "Found " + str(len(destinations)) + " possible destinations:"
        for d in destinations:
            destquery += "\n" + str(destinations.index(d)) + ": " + str(d)
        destquery += "\nChoose the number of the destination: "
        destination = destinations[inputint(destquery, len(destinations))]
    else:
        print("No destinations found for '" + source + "'.")
    # Return to source input if destination is blank
    if destination == "":
            continue

    # Build the regexes for finding links
    regex1 = re.compile("\[+" + source.replace("'", "(%27|')").replace(" ", "[_ ]").replace(":", "\:[_ ]{0,1}") + "[_ ]{0,1}(?=[\]\|#])", re.I) # This covers most wikilinks
    regex2 = re.compile("\{+" + source.replace("'", "(%27|')").replace(" ", "[_ ]").replace(":", "\|[_ ]{0,1}") + "[_ ]{0,1}\}+", re.I) # This one is for the {{Build}} template used for the admin noticeboard/user talks

    # Build the replace strings
    replace1 = "[[" + destination
    # If the destination is not another Build: namespace article, the {{Build}} template needs to be replaced with a link
    if re.search("^Build:", destination) != None:
        replace2 = "{{" + destination.replace(":", "|") + "}}"
    else:
        replace2 = "[[" + destination + "]]"
    regexdict.update({regex1:replace1, regex2:replace2})

    # Finally, add the pages that link to the source to the main list
    for p in pagelist:
        titlelist.add(p['title'])
    print(len(titlelist), "pages currently to be updated.")

# Loop through page list, making replacements
for title in titlelist:
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
# Logout
apipost(url, {'action':"logout",'format':"json"}, session)
print("Logged out.")
