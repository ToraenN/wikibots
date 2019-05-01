"""
    "AutoToraen": One script to rule them all.
"""

import re
import requests
from getpass import getpass
from datetime import datetime, date, time
from time import sleep

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

def readmovelog(url, time, session):
    params_movelog = {
        'action':"query",
        'list':"logevents",
        'leprop':"type|title|details",
        'letype':"move",
        'lelimit':"max",
        'ledir':"newer",
        'lestart':time,
        'format':"json"
    }
    
    entrylist = apiget(url, params_movelog, session)['query']['logevents']
    return entrylist

def filtermovelist(entrylist, url, session):
    for rawentry in entrylist:
        moveentry = rawentry['title']
        # Check if the page exists (so we can ignore redirects/recreated pages)
        sourceexist = pageexist(moveentry, url, session)
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
        answer = input("Add " + moveentry + " to list of links to update? ")
        if "y" in answer:
            for p in pagelist:
                titlelist.add(p['title'])
            movelist.append(moveentry)
    return movelist

def getuserpages(username, url, session):
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
    return pagelist

def checklog(action, url, session, username = None, timestamp = None):
    params_logcheck = {
        'action':"query",
        'list':"logevents",
        'leprop':"type|title|details|user",
        'letype':action,
        'lelimit':"max",
        'ledir':"newer",
        'format':"json"
    }
    if username != None:
        params_logcheck.update({'leuser':username})
    if timestamp != None:
        params_logcheck.update({'lestart':timestamp})
    loglist = apiget(url, params_logcheck, session)
    return loglist

def pageexist(page, url, session):
    params_existcheck = {
        'action':"query",
        'titles':page,
        'format':"json"
    }
    
    result = apiget(url, params_existcheck, session)
    return result

def editpage(page, pagetext, reason, edittoken, url, session):
    params_editpage = {
        'action':"edit",
        'title':page,
        'bot':"true",
        'summary':reason,
        'text':pagetext,
        'token':edittoken,
        'format':"json"
    }
    
    editcommit = apipost(url, params_editpage, session)
    try:
        status = editcommit['edit']['result']
        if status == 'Success':
            return True
        else:
            raise KeyError
    except KeyError:
        return False

def movepage(oldpage, newpage, regexdict, edittoken, url, session):
    params_move = {
        'action':"move",
        'from':oldpage,
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
        print("'" + page + "' to '" + newpage + "':" + moveresult['error']['info'])
    return moveresult

def checkbrokenlinks(page, url, session):
    brokenlinkpages = set()
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
            brokenlinkpages.add(p['title'])
    except KeyError:
        pass # Page still exists, so don't change any links to it
    return brokenlinkpages

def updatelinks(page, regexdict, edittoken, url, session):
    # Get page wikitext
    params_listentry = {
        'action':"parse",
        'prop':"wikitext",
        'page':page,
        'format':"json"
    }
    
    # Make replacements
    pagetext = apiget(url, params_listentry, session)['parse']['wikitext']['*']
    for a, b in regexdict.items():
        pagetext = re.sub(a, b, pagetext)
    status = editpage(page, pagetext, "Updating links of moved pages", edittoken, url, session)
    if status:
        print("Links on '" + page + "' updated.")
    else:
        print("WARNING: Success message not received for '" + page + "'!")

def deletepage(page, reason, edittoken, url, session):
    params_delete = {
        'action':"delete",
        'title':page,
        'reason':reason,
        'format':"json",
        'token':edittoken
    }
    
    result = apipost(url, params_delete, session)
    try:
        result['delete']
        print("'" + page + "' deleted.")
    except KeyError:
        print("Could not delete '" + page + "'. Error code: " + result['error']['code'])
    return result

def restorepage(page, reason, edittoken, url, session):
    params_restore = {
        'action':"undelete",
        'title':title,
        'reason':reason,
        'token':edittoken,
        'format':"json"
    }
    
    restore = apipost(url, params_restore, session)
    return restore

def logout(url, session):
    apipost(url, {'action':"logout",'format':"json"}, session)
    print("Logged out.")
    raise SystemExit()

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

def settimestamp(prompt):
    timestamp = str(inputint('Enter the time (UTC) to start searching the ' + prompt + ' from (YYYYMMDDHHMMSS): ', 100000000000000)).ljust(14, "0")
    return timestamp

def refreshtimestamp():
    timestamp = str(datetime.utcnow()).replace("-","").replace(" ","").replace(":","")
    timestamp = (timestamp.split("."))[0]
    return timestamp

url = "https://gwpvx.gamepedia.com/api.php"
session = requests.Session()
edittoken = startup(url, session)
message = "What are you doing today?\n0: Updating links to moved pages.\n1: Reversing deletions.\n2: Moving userspace to new name.\n3: Resigning user.\n4: Update subpage links.\n5: Continue from crash.\nChoose the number of your job: "
jobid = inputint(message, 6)

if jobid == 0:
    # Link fixing
    message = "Would you like to:\n0: Enter moves manually?\n1: Check the move log?\n2: Listen for moves?\nChoose a number: "
    subjobid = inputint(message, 3)
    if subjobid == 0:
        pass
    if subjobid == 1:
        settime = settimestamp('move log')
    if subjobid == 2:
        pass
elif jobid == 1:
    # Reverse deletions
    settime = settimestamp('delete log')
    username = input('Limit to user: ')
    if settime == "00000000000000":
        settime = None
    if username == "":
        username = None
    deletelog = checklog('delete', url, session, username = username, timestamp = settime)['query']['logevents']
    print("For each entry, enter one of the following:\n'y': restore the page.\n'd': end the script.\nLeave blank to ignore the page.")
    for entry in deletelog:
        title = entry['title']
        # Skip recreated pages and restore entries
        if entry['action'] != 'delete':
            continue
        try:
            pageexist(title, url, session)['query']['pages']['-1']
        except KeyError:
            continue
        response = input("Restore '" + title + "'? ")
        # Restore the page
        if response == 'y':
            result = restorepage(title, "Reverting accidental deletion.", edittoken, url, session)
            try:
                result['undelete']
                print("'" + title + "' restored.")
            except KeyError:
                print("Could not restore '" + title + "'. Error code: " + result['error']['code'])
        # Break the loop -> quit the script
        elif response == 'd':
            break
elif jobid == 2:
    # Userspace move
    regexdict = dict()
    fixlist = set()
    # Prompt user for the old & new usernames
    oldusername = input("\nOld username: ")
    newusername = input("\nNew username: ")
    if oldusername == "" or newusername == "":
        logout(url, session)
    pagelist = getuserpages(oldusername, url, session)
    # Move pages
    for page in pagelist:
        newpage = re.sub(r'^User:' + oldusername, 'User:' + newusername, page)
        newpage = re.sub(r'^User talk:' + oldusername, 'User talk:' + newusername, newpage)
        result = movepage(page, newpage, regexdict, edittoken, url, session)
    # Get list of pages with links to fix
    for page in pagelist:
        brokenlinkpages = checkbrokenlinks(page, url, session)
        for b in brokenlinkpages:
            fixlist.add(b)
    # Save a copy of the link fix list and the regex dictionary, in case the script crashes
    with open(oldusername + "-" + newusername + "-fixlist.txt", "a") as savelist:
        for f in fixlist:
            line = f + "\n"
            savelist.write(line)
    with open(oldusername + "-" + newusername + "-regex.txt", "a") as savedict:
        for r in regexdict:
            line = str(r) + " : " + regexdict[r] + "\n"
            savedict.write(line)
    # Fix links
    for page in fixlist:
        updatelinks(page, regexdict, edittoken, url, session)
elif jobid == 3:
    # Userspace delete
    username = input("User to RESIGN: ")
    pagelist = getuserpages(username, url, session)
    # Confirm the pages to be deleted
    response = input(str(len(pagelist)) + ' pages to be deleted. Continue? (y/n) ')
    if response != 'y':
        logout(url, session)
    # Save list of pages, in case mass undelete is needed
    with open("RESIGN-" + username + ".txt", "a") as savelist:
        for p in pagelist:
            line = p + "\n"
            savelist.write(line)
    for page in pagelist:
        deletepage(page, "[[PvX:RESIGN]]", edittoken, url, session)
elif jobid == 4:
    # Change absolute links to subpages into relative links
    pass
elif jobid == 5:
    # Load files to continue from script crash
    pass
logout(url, session)