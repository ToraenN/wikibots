"""
    "Moved Page Link Fixer": Updates all redlinks to a user-provided old page to point to a new page.
"""

import re
import requests

# Either hardcode the credentials here, or use the input boxes. 
# Using the main account for login is not supported. Obtain credentials via Special:BotPasswords
# The only permissions you need to give to the bot password are 'high volume editing' and 'edit existing pages'.
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

# Loop script until user is done inputting jobs
while loggedin == 'Success':
    # Prompt user for the old name of the page
    source = input("\nOld name: ")
    # Break loop, and thus logout, if source is blank.
    if source == "":
        break
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
    
    apicall = session.get(url=url, params=params_movecheck)
    result = apicall.json()
    
    movedlist = result['query']['logevents']
    destinations = set()
    # Check if each destination exists
    for event in movedlist:
        movetarget = event['params']['target_title']
        params_existcheck = {
            'action':"query",
            'titles':movetarget,
            'format':"json"
        }
        
        apicall = session.get(url=url, params=params_existcheck)
        result = apicall.json()
        
        try:
            result['query']['pages']['-1']
        except KeyError:
            destinations.add(movetarget)
    destinations = list(destinations)
    # Only display the existing destinations
    if len(destinations) > 0:
        destquery = "Found " + str(len(destinations)) + " possible destinations:"
        for d in destinations:
            destquery += "\n" + str(destinations.index(d)) + ": " + str(d)
        destquery += "\nChoose the number of the destination: "
        try:
            destination = destinations[int(input(destquery))]
    # If all else fails, let the user input the destination
        except:
            destination = input("Invalid entry. Please type the new name: ")
    else:
        destination = input("New name: ")
    # Return to source input if destination is blank or doesn't exist
    params_existcheck = {
        'action':"query",
        'titles':destination,
        'format':"json"
    }
    
    apicall = session.get(url=url, params=params_existcheck)
    result = apicall.json()
    try:
        result['query']['pages']['-1']
        print("That destination does not exist!")
        continue
    except KeyError:
        if destination == "":
            continue
    
    # Build the regexes for finding links
    regex1 = re.compile("\[+" + source.replace(" ", "[_ ]").replace(":", "\:[_ ]{0,1}") + "[_ ]{0,1}(?=[\]\|#])", re.I) # This covers most wikilinks
    regex2 = re.compile("\{+" + source.replace(" ", "[_ ]").replace(":", "\|[_ ]{0,1}") + "[_ ]{0,1}\}+", re.I) # This one is for the {{Build}} template used for the admin noticeboard/user talks

    # Build the replace strings
    replace1 = "[[" + destination
    # If the destination is not another Build: namespace article, the {{Build}} template needs to be replaced with a link
    if re.search("^Build:", destination) != None:
        replace2 = "{{" + destination.replace(":", "|") + "}}"
    else:
        replace2 = "[[" + destination + "]]"

    # Get page list
    params_linkshere = {
        'action':"query",
        'prop':"linkshere",
        'titles':source,
        'lhlimit':"max",
        'format':"json"
    }

    apicall = session.post(url, data=params_linkshere)
    result = apicall.json()
    try:
        pagelist = result['query']['pages']["-1"]['linkshere'] # -1 will be provided as a placeholder for the page id for any missing page
    except KeyError:
        print("'" + source + "' is not a valid old page.")
        continue
    titlelist = []
    for p in pagelist:
        titlelist.append(p['title'])

    # Loop through page list, making replacements
    for title in titlelist:
        # Get page wikitext
        params_listentry = {
            'action':"parse",
            'prop':"wikitext",
            'page':title,
            'format':"json"
        }
        
        apicall = session.post(url, data= params_listentry)
        result = apicall.json()
        # Make replacements
        pagetext = result['parse']['wikitext']['*']
        pagetext = re.sub(regex1, replace1, pagetext)
        pagetext = re.sub(regex2, replace2, pagetext)
        # Get an edit token
        params_edittoken = {
            'action':"query",
            'meta':"tokens",
            'titles':title,
            'format':"json"
        }
        
        apicall = session.post(url, data= params_edittoken)
        result = apicall.json()
        
        edittoken = result['query']['tokens']['csrftoken']
        # Commit the edit
        params_editpage = {
            'action':"edit",
            'title':title,
            'bot':"true",
            'summary':"Updating links to [[" + str(destination) + "]]",
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
