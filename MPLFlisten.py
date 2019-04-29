"""
    "Moved Page Link Fixer (Listen)": Waits for new entries to the move log and updates links accordingly.
"""

import re
import requests
from getpass import getpass
from datetime import datetime, date, time
from time import sleep

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

def starttimestamp():
    timestamp = str(datetime.utcnow()).replace("-","").replace(" ","").replace(":","")
    timestamp = (timestamp.split("."))[0]
    return timestamp

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

def pageexist(page, url, session):
    params_existcheck = {
        'action':"query",
        'titles':page,
        'format':"json"
    }
    
    result = apiget(url, params_existcheck, session)
    return result

url = "https://gwpvx.gamepedia.com/api.php"
session = requests.Session()
edittoken = startup(url, session)

#Initial timestamp
boundtime = starttimestamp()
try:
    while True:
        #Check the move log
        regexdict = dict()
        titlelist = set()
        movelist = []
        params_movelog = {
            'action':"query",
            'list':"logevents",
            'leprop':"type|title|details",
            'letype':"move",
            'lelimit':"max",
            'ledir':"newer",
            'lestart':boundtime,
            'format':"json"
        }
        
        entrylist = apiget(url, params_movelog, session)['query']['logevents']
        boundtime = starttimestamp()
        if len(entrylist) == 0:
            print("No moves detected since " + boundtime + "!")
        for rawentry in entrylist:
            moveentry = rawentry['title']
            # Check if the page exists (so we can ignore redirects/recreated pages)
            params_exist = {
                'action':"query",
                'titles':moveentry,
                'format':"json"
            }
            
            sourceexist = apiget(url, params_exist, session)
            
            try:
                sourceexist['query']['pages']['-1']
            except KeyError:
                print("Skipped " + moveentry + ". Page exists.")
                continue
            # Check if anything still links to title in the move log entry
            params_linkshere = {
                'action':"query",
                'prop':"linkshere",
                'titles':moveentry,
                'lhlimit':"max",
                'format':"json"
            }
            
            linkshere = apiget(url, params_linkshere, session)
            try:
                pagelist = linkshere['query']['pages']["-1"]['linkshere'] # -1 will be provided as a placeholder for the page id for any missing page
            except KeyError:
                print("Skipped " + moveentry + ". No links found.")
                continue
            for p in pagelist:
                titlelist.add(p['title'])
            movelist.append(moveentry)

        for source in movelist:
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
                # Maybe possibly will work and not cause infinite recursion - should allow script to follow multiple moves
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
                destexist = pageexist(movetarget, url, session)
                try:
                    destexist['query']['pages']['-1']
                except KeyError:
                    destinations.add(movetarget)
            destinations = list(destinations)
            # Only display the existing destinations
            if len(destinations) > 1:
                destquery = "Found " + str(len(destinations)) + " possible destinations for '" + source + "':"
                for d in destinations:
                    destquery += "\n" + str(destinations.index(d)) + ": " + str(d)
                destquery += "\nChoose the number of the destination: "
                destination = destinations[inputint(destquery, len(destinations))]
            elif len(destinations) == 1:
                destination = destinations[0]
                print("Destination for '" + source + "' found: " + destination)
            else:
                print("No destination found for '" + source + "'.")
                destination = ""
            # Return to source input if destination is blank or doesn't exist
            if destination == "":
                    continue
            destexist = pageexist(destination, url, session)
            try:
                destexist['query']['pages']['-1']
                print("That destination does not exist!")
                continue
            except KeyError:
                pass

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
        #Wait a bit
        sleep(60)
except KeyboardInterrupt:
    logout(url, session)
