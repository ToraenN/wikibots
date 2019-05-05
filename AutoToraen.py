"""
    "AutoToraen": One script to rule them all.
"""

import re
import requests
from getpass import getpass
from datetime import datetime, date, time
from time import sleep

def main():
    url = "https://gwpvx.gamepedia.com/api.php"
    session = requests.Session()
    edittoken = startup(url, session)

    message = "What are you doing today?\n0: Updating links to moved pages.\n1: Reversing deletions.\n2: Moving userspace to new name.\n3: Resigning user.\n4: Update subpage links.\n5: Continue from crash.\nChoose the number of your job: "
    jobid = inputint(message, 6)

    if jobid == 0:
        # Link fixing
        mplf(url, edittoken, session)
    elif jobid == 1:
        # Reverse deletions
        oops(url, edittoken, session)
    elif jobid == 2:
        # Userspace move
        sweep(url, edittoken, session)
    elif jobid == 3:
        # Userspace delete
        resign(url, edittoken, session)
    elif jobid == 4:
        # Change absolute links to subpages into relative links
        pass
    elif jobid == 5:
        # Load files to continue from script crash
        pass
    logout(url, session)

def mplf(url, edittoken, session):
    message = "Would you like to:\n0: Enter moves manually?\n1: Check the move log?\n2: Listen for moves?\nChoose a number: "
    subjobid = inputint(message, 3)
    if subjobid == 0:
        # Manual entry
        movelist = set()
        fixlist = set()
        while True:
            # Prompt user for the old name of the page
            source = input("\nOld name: ")
            # Break loop, and thus move to processing, if source is blank.
            if source == "":
                break
            else:
                if pageexist(source, url, session) and not isredirect(source, url, session):
                    print(source + " still exists.")
                    continue
                brokenlinkpages = whatlinkshere(source, url, session)
                if len(brokenlinkpages) > 0:
                    for b in brokenlinkpages:
                        fixlist.add(b)
                    movelist.add(source)
                else:
                    print("'" + source + "' is not linked to.")
                print(len(fixlist), " pages currently to be updated.")

        regexdict = finddestinations(movelist, url, session)
        for f in fixlist:
            updatelinks(f, regexdict, edittoken, url, session)
    if subjobid == 1:
        # Check move log from specific date forward
        timestamp = settimestamp('move log')
        username = input('Limit to user: ')
        moveentries = checklog('move', url, session, username = username, timestamp = timestamp)
        movelist, titlelist = parsemoveentries(moveentries, url, session)
        regexdict = finddestinations(movelist, url, session, timestamp = timestamp)
        for title in titlelist:
            updatelinks(title, regexdict, edittoken, url, session)
    if subjobid == 2:
        # Check the move log for new moves periodically
        timestamp = refreshtimestamp()
        while True:
            moveentries = checklog('move', url, session, timestamp = timestamp)
            if len(moveentries) == 0:
                print("No moves detected since " + timestamp + "!")
            timestamp = refreshtimestamp()
            movelist, titlelist = parsemoveentries(moveentries, url, session)
            regexdict = finddestinations(movelist, url, session, timestamp = timestamp, prompt = False)
            for title in titlelist:
                updatelinks(title, regexdict, edittoken, url, session)
            sleep(60)

def oops(url, edittoken, session):
    timestamp = settimestamp('delete log')
    username = input('Limit to user: ')
    deletelog = checklog('delete', url, session, username = username, timestamp = timestamp)
    print("For each entry, enter one of the following:\n'y': restore the page.\n'd': end the script.\nLeave blank to ignore the page.")
    for entry in deletelog:
        title = entry['title']
        # Skip recreated pages and restore entries
        if entry['action'] != 'delete':
            continue
        if pageexist(title, url, session):
            continue
        response = input("Restore '" + title + "'? ")
        # Restore the page
        if response == 'y':
            restorepage(title, "Reverting accidental deletion.", edittoken, url, session)
        # Break the loop -> quit the script
        elif response == 'd':
            break

def sweep(url, edittoken, session):
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
        movepage(page, newpage, regexdict, edittoken, url, session)
    # Get list of pages with links to fix
    for page in pagelist:
        brokenlinkpages = whatlinkshere(page, url, session)
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

def resign(url, edittoken, session):
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

def checklog(action, url, session, title = None, username = None, timestamp = None):
    params_logcheck = {
        'action':"query",
        'list':"logevents",
        'leprop':"type|title|details|user",
        'letype':action,
        'lelimit':"max",
        'ledir':"newer",
        'format':"json"
    }
    if timestamp == "00000000000000": # Considered an invalid time by the API
        timestamp = None
    if username == "": # Blank username would return an API error message
        username = None
    if username != None:
        params_logcheck.update({'leuser':username})
    if timestamp != None:
        params_logcheck.update({'lestart':timestamp})
    if title != None:
        params_logcheck.update({'letitle':title})
    loglist = apiget(url, params_logcheck, session)
    loglist = loglist['query']['logevents']
    return loglist

def pageexist(page, url, session):
    params_existcheck = {
        'action':"query",
        'titles':page,
        'format':"json"
    }
    
    result = apiget(url, params_existcheck, session)
    try:
        result['query']['pages']['-1']
        return False #Page does not exist
    except KeyError:
        return True #Page exists

def isredirect(page, url, session):
    # Check if the supplied page is a redirect
    text = readpage(page, url, session)
    if re.search("^#REDIRECT \[\[", text, re.I):
        redirect = True
    else:
        redirect = False
    return redirect

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

def whatlinkshere(page, url, session):
    linkpages = set()
    params_linkshere = {
        'action':"query",
        'prop':"linkshere",
        'titles':page,
        'lhlimit':"max",
        'format':"json"
    }
    
    try:
        pageid = apiget(url, params_linkshere, session)['query']['pages']
        for id, data in pageid.items():
            linkshere = data['linkshere']
    except KeyError:
        linkshere = [] #No links found
    for p in linkshere:
        linkpages.add(p['title'])
    return linkpages

def updatelinks(page, regexdict, edittoken, url, session):
    # Make replacements
    pagetext = readpage(page, url, session)
    for a, b in regexdict.items():
        pagetext = re.sub(a, b, pagetext)
    status = editpage(page, pagetext, "Updating links of moved pages", edittoken, url, session)
    if status:
        print("Links on '" + page + "' updated.")
    else:
        print("WARNING: Success message not received for '" + page + "'!")

def readpage(page, url, session):
    # Get page wikitext
    params_readpage = {
        'action':"parse",
        'prop':"wikitext",
        'page':page,
        'format':"json"
    }
    
    try:
        pagetext = apiget(url, params_readpage, session)['parse']['wikitext']['*']
    except KeyError:
        pagetext = ""
    return pagetext

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
    
    result = apipost(url, params_restore, session)
    try:
        result['undelete']
        print("'" + title + "' restored.")
    except KeyError:
        print("Could not restore '" + title + "'. Error code: " + result['error']['code'])
    return result

def parsemoveentries(moveentries, url, session):
    movelist = []
    titlelist = set()
    for entry in moveentries:
        title = entry['title']
        # Check if the page exists (so we can ignore recreated pages)
        if pageexist(title, url, session) and not isredirect(title, url, session):
            print("Skipped " + title + ". Page exists.")
            continue
        # Check if anything still links to title in the move log entry
        brokenlinkpages = whatlinkshere(title, url, session)
        if len(brokenlinkpages) == 0:
            print("Skipped " + title + ". No links found.")
            continue
        for p in brokenlinkpages:
            titlelist.add(p)
        movelist.append(title)
    return movelist, titlelist

def finddestinations(movelist, url, session, username = None, timestamp = None, prompt = True):
    regexdict = dict()
    for source in movelist:
        # Check move log for destination
        movedlist = checklog('move', url, session, title = source, username = username, timestamp = timestamp)
        destinations = set()
        # Check if each destination exists
        for event in movedlist:
            movetarget = event['params']['target_title']
            # Maybe possibly will work and not cause infinite recursion - should allow script to follow multiple moves
            appendlist = checklog('move', url, session, title = movetarget, username = username, timestamp = timestamp)
            for item in appendlist:
                if not item in movedlist:
                    movedlist.append(item)
            
            destexist = pageexist(movetarget, url, session)
            if destexist:
                destinations.add(movetarget)
        destinations = list(destinations)
        # Only display the existing destinations
        if (len(destinations) > 1) and (prompt == True):
            destquery = "Found " + str(len(destinations)) + " possible destinations for '" + source + "':"
            for d in destinations:
                destquery += "\n" + str(destinations.index(d)) + ": " + str(d)
            destquery += "\nChoose the number of the destination: "
            destination = destinations[inputint(destquery, len(destinations))]
        elif (len(destinations) > 1) and (prompt == False):
            print("Multiple destinations found for " + source + ". Skipping (use other mode).")
            destination = ""
        elif len(destinations) == 1:
            destination = destinations[0]
            print("Destination for '" + source + "' found: " + destination)
        else:
            print("No destination found for '" + source + "'.")
            destination = ""
        # Return to source input if destination is blank or doesn't exist
        if destination == "":
                continue
        if not pageexist(destination, url, session):
            print("That destination does not exist!")
            continue

        # Build the regexes for finding links
        regex1 = re.compile("\[+" + source.replace("'", "(%27|')").replace(":", "(%3A|:)").replace(" ", "[_ ]").replace(":", "\:[_ ]{0,1}") + "[_ ]{0,1}(?=[\]\|#])", re.I) # This covers most wikilinks
        regex2 = re.compile("\{+" + source.replace("'", "(%27|')").replace(":", "(%3A|:)").replace(" ", "[_ ]").replace(":", "\|[_ ]{0,1}") + "[_ ]{0,1}\}+", re.I) # This one is for the {{Build}} template used for the admin noticeboard/user talks

        # Build the replace strings
        replace1 = "[[" + destination
        # If the destination is not another Build: namespace article, the {{Build}} template needs to be replaced with a link
        if re.search("^Build:", destination) != None:
            replace2 = "{{" + destination.replace(":", "|") + "}}"
        else:
            replace2 = "[[" + destination + "]]"
        regexdict.update({regex1:replace1, regex2:replace2})
    return regexdict

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

def logout(url, session):
    apipost(url, {'action':"logout",'format':"json"}, session)
    print("Logged out.")
    raise SystemExit()

if __name__ == "__main__":
    main()