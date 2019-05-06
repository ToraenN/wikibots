"""
    "AutoToraen": One script to rule them all.
"""

import re
import requests
from getpass import getpass
from datetime import datetime, date, time
from time import sleep

def main():
    bot = BotSession()
    while True:
        message = "\nWhat are you doing today?\n0: Updating links to moved pages.\n1: Reversing deletions.\n2: Moving userspace to new name.\n3: Resigning user.\n4: Updating subpage links.\n5: Loading file.\n6: Change account.\n7: Logout\nChoose the number of your job: "
        jobid = inputint(message, 8)
        if jobid == 0:
            # Link fixing
            bot.mplf()
        elif jobid == 1:
            # Reverse deletions
            bot.oops()
        elif jobid == 2:
            # Userspace move
            bot.sweep()
        elif jobid == 3:
            # Userspace delete
            bot.resign()
        elif jobid == 4:
            # Change absolute links to subpages into relative links
            print("Not yet implemented.")
        elif jobid == 5:
            # Load files to execute a job
            print("Not yet implemented.")
        elif jobid == 6:
            # Change to a different account
            bot.logout()
            bot = BotSession()
        elif jobid == 7:
            # Exit
            bot.logout()
            raise SystemExit()

def statuscheck(apicall):
    if apicall.status_code == requests.codes.ok:
        return True
    else:
        print("Call to api failed: " + str(apicall.status_code) + "\nAttempted url: " + str(apicall.url))
        answer = input("Reattempt (y/n)? ")
        if "y" in answer:
            return False
        else:
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

class BotSession:
    def __init__(self):
        self.url = "https://gwpvx.gamepedia.com/api.php"
        self.session = requests.Session()
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
        
        logintoken = self.apiget(params_tokens)['query']['tokens']['logintoken']
        
        # Then we can login
        params_login = {
            'action':"login",
            'lgname':username,
            'lgpassword':password,
            'lgtoken':logintoken,
            'format':"json"
        }
        
        loggedin = self.apipost(params_login)['login']['result']
        print("Login " + loggedin + "!")
        del logintoken, params_login, username, password
        if loggedin != 'Success':
            raise SystemExit()
        
        # Get an edit token
        params_edittoken = {
            'action':"query",
            'meta':"tokens",
            'format':"json"
        }
        
        self.edittoken = self.apipost(params_edittoken)['query']['tokens']['csrftoken']
    
    def mplf(self):
        message = "Would you like to:\n0: Enter moves manually?\n1: Check the move log?\n2: Listen for moves?\nChoose a number: "
        subjobid = inputint(message, 3)
        if subjobid == 0:
            # Manual entry
            moveentries = []
            index = 0
            while True:
                index += 1
                # Prompt user for the old name of the page
                source = input(str(index) + ":Old name: ")
                # Break loop, and thus move to processing, if source is blank.
                if source == "":
                    break
                else:
                    moveentries.append({'title':source})
            movelist, titlelist = self.parsemoveentries(moveentries)
            regexdict = self.finddestinations(movelist)
            for title in titlelist:
                self.updatelinks(title, regexdict)
        if subjobid == 1:
            # Check move log from specific date forward
            timestamp = settimestamp('move log')
            username = input('Limit to user: ')
            moveentries = self.checklog('move', username = username, timestamp = timestamp)
            movelist, titlelist = self.parsemoveentries(moveentries)
            regexdict = self.finddestinations(movelist, timestamp = timestamp)
            for title in titlelist:
                self.updatelinks(title, regexdict)
        if subjobid == 2:
            # Check the move log for new moves periodically
            timestamp = refreshtimestamp()
            while True:
                moveentries = self.checklog('move', timestamp = timestamp)
                if len(moveentries) == 0:
                    print("No moves detected since " + timestamp + "!")
                timestamp = refreshtimestamp()
                movelist, titlelist = self.parsemoveentries(moveentries)
                regexdict = self.finddestinations(movelist, timestamp = timestamp, prompt = False)
                for title in titlelist:
                    self.updatelinks(title, regexdict)
                sleep(60)

    def oops(self):
        timestamp = settimestamp('delete log')
        username = input('Limit to user: ')
        deletelog = self.checklog('delete', username = username, timestamp = timestamp)
        print("For each entry, enter one of the following:\n'y': restore the page.\n'd': end the script.\nLeave blank to ignore the page.")
        for entry in deletelog:
            title = entry['title']
            # Skip recreated pages and restore entries
            if entry['action'] != 'delete':
                continue
            if self.pageexist(title):
                continue
            response = input("Restore '" + title + "'? ")
            # Restore the page
            if response == 'y':
                self.restorepage(title, "Reverting accidental deletion.")
            # Break the loop -> quit the script
            elif response == 'd':
                break

    def sweep(self):
        regexdict = dict()
        fixlist = set()
        # Prompt user for the old & new usernames
        oldusername = input("\nOld username: ")
        newusername = input("\nNew username: ")
        if oldusername == "" or newusername == "":
            return
        pagelist = self.getuserpages(oldusername)
        # Move pages
        for page in pagelist:
            newpage = re.sub(r'^User:' + oldusername, 'User:' + newusername, page)
            newpage = re.sub(r'^User talk:' + oldusername, 'User talk:' + newusername, newpage)
            self.movepage(page, newpage, regexdict)
        # Get list of pages with links to fix
        for page in pagelist:
            brokenlinkpages = self.whatlinkshere(page)
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
            self.updatelinks(page, regexdict)

    def resign(self):
        username = input("User to RESIGN: ")
        pagelist = self.getuserpages(username)
        # Confirm the pages to be deleted
        response = input(str(len(pagelist)) + ' pages to be deleted. Continue? (y/n) ')
        if response != 'y':
            return
        # Save list of pages, in case mass undelete is needed
        with open("RESIGN-" + username + ".txt", "a") as savelist:
            for p in pagelist:
                line = p + "\n"
                savelist.write(line)
        for page in pagelist:
            self.deletepage(page, "[[PvX:RESIGN]]")

    def apiget(self, parameters):
        while True:
            apicall = self.session.get(url = self.url, params = parameters)
            if statuscheck(apicall):
                break
        result = apicall.json()
        return result

    def apipost(self, parameters):
        while True:
            apicall = self.session.post(url = self.url, data = parameters)
            if statuscheck(apicall):
                break
        result = apicall.json()
        return result

    def getuserpages(self, username):
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

        userpages = self.apiget(params_userpages)['query']['allpages']
        usertalks = self.apiget(params_usertalks)['query']['allpages']
        pagelist = set()
        for page in userpages:
            if re.search("User:" + username + "(/|$)", page['title']) != None:
                pagelist.add(page['title'])
        for page in usertalks:
            if re.search("User talk:" + username + "(/|$)", page['title']) != None:
                pagelist.add(page['title'])
        return pagelist

    def checklog(self, action, title = None, username = None, timestamp = None):
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
        loglist = self.apiget(params_logcheck)
        loglist = loglist['query']['logevents']
        return loglist

    def pageexist(self, page):
        params_existcheck = {
            'action':"query",
            'titles':page,
            'format':"json"
        }
        
        result = self.apiget(params_existcheck)
        try:
            result['query']['pages']['-1']
            return False #Page does not exist
        except KeyError:
            return True #Page exists

    def isredirect(self, page):
        # Check if the supplied page is a redirect
        text = self.readpage(page)
        if re.search("^#REDIRECT \[\[", text, re.I):
            redirect = True
        else:
            redirect = False
        return redirect

    def editpage(self, page, pagetext, reason):
        params_editpage = {
            'action':"edit",
            'title':page,
            'bot':"true",
            'summary':reason,
            'text':pagetext,
            'token':self.edittoken,
            'format':"json"
        }
        
        editcommit = self.apipost(params_editpage)
        try:
            status = editcommit['edit']['result']
            if status == 'Success':
                return True
            else:
                raise KeyError
        except KeyError:
            return False

    def movepage(self, oldpage, newpage, regexdict):
        params_move = {
            'action':"move",
            'from':oldpage,
            'to':newpage,
            'reason':"Username change",
            'noredirect':"yes",
            'format':"json",
            'token':self.edittoken
        }
        
        moveresult = self.apipost(params_move)
        
        try:
            print("'" + moveresult['move']['from'] + "' moved to '" + moveresult['move']['to'] + "'.")
            # Build the regex for finding links
            regex = re.compile("\[+" + oldpage.replace(" ", "[_ ]").replace(":", "\:[_ ]{0,1}") + "[_ ]{0,1}(?=[\]\|#])", re.I) # This covers most wikilinks
            
            # Build the replace string
            replace = "[[" + newpage
            
            # Save to dictionary
            regexdict.update({regex:replace})
        except KeyError:
            print("'" + oldpage + "' to '" + newpage + "':" + moveresult['error']['info'])
        return moveresult

    def whatlinkshere(self, page):
        linkpages = set()
        params_linkshere = {
            'action':"query",
            'prop':"linkshere",
            'titles':page,
            'lhlimit':"max",
            'format':"json"
        }
        
        try:
            pageid = self.apiget(params_linkshere)['query']['pages']
            for id, data in pageid.items():
                linkshere = data['linkshere']
        except KeyError:
            linkshere = [] #No links found
        for p in linkshere:
            linkpages.add(p['title'])
        return linkpages

    def updatelinks(self, page, regexdict):
        # Make replacements
        pagetext = self.readpage(page)
        newpagetext = pagetext
        for a, b in regexdict.items():
            newpagetext = re.sub(a, b, newpagetext)
        if newpagetext == pagetext:
            print("No changes made to " + page + ". Broken links not identified.") # Caused by templates/link formats the script does not yet account for
            return
        status = self.editpage(page, newpagetext, "Updating links of moved pages")
        if status:
            print("Links on '" + page + "' updated.")
        else:
            print("WARNING: Success message not received for '" + page + "'!")

    def readpage(self, page):
        # Get page wikitext
        params_readpage = {
            'action':"parse",
            'prop':"wikitext",
            'page':page,
            'format':"json"
        }
        
        try:
            pagetext = self.apiget(params_readpage)['parse']['wikitext']['*']
        except KeyError:
            pagetext = ""
        return pagetext

    def deletepage(self, page, reason):
        params_delete = {
            'action':"delete",
            'title':page,
            'reason':reason,
            'format':"json",
            'token':self.edittoken
        }
        
        result = self.apipost(params_delete)
        try:
            result['delete']
            print("'" + page + "' deleted.")
        except KeyError:
            print("Could not delete '" + page + "'. Error code: " + result['error']['code'])
        return result

    def restorepage(self, page, reason):
        params_restore = {
            'action':"undelete",
            'title':title,
            'reason':reason,
            'token':self.edittoken,
            'format':"json"
        }
        
        result = self.apipost(params_restore)
        try:
            result['undelete']
            print("'" + title + "' restored.")
        except KeyError:
            print("Could not restore '" + title + "'. Error code: " + result['error']['code'])
        return result

    def parsemoveentries(self, moveentries):
        movelist = []
        titlelist = set()
        for entry in moveentries:
            title = entry['title']
            # Check if the page exists (so we can ignore recreated pages)
            if self.pageexist(title) and not self.isredirect(title):
                print("Skipped " + title + ". Page exists.")
                continue
            # Check if anything still links to title in the move log entry
            brokenlinkpages = self.whatlinkshere(title)
            if len(brokenlinkpages) == 0:
                print("Skipped " + title + ". No links found.")
                continue
            # Compile pages to be fixed
            for p in brokenlinkpages:
                titlelist.add(p)
            movelist.append(title)
            linknumber = str(len(brokenlinkpages))
            message = "Found " + linknumber + " page"
            if linknumber != "1":
                message += "s"
            message += " with links to " + title + "."
            print(message)
        return movelist, titlelist

    def finddestinations(self, movelist, username = None, timestamp = None, prompt = True):
        regexdict = dict()
        for source in movelist:
            # Check move log for destination
            movedlist = self.checklog('move', title = source, username = username, timestamp = timestamp)
            destinations = set()
            # Check if each destination exists
            for event in movedlist:
                movetarget = event['params']['target_title']
                # Maybe possibly will work and not cause infinite recursion - should allow script to follow multiple moves
                appendlist = self.checklog('move', title = movetarget, username = username, timestamp = timestamp)
                for item in appendlist:
                    if not item in movedlist:
                        movedlist.append(item)
                if self.pageexist(movetarget):
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
                continue
            elif len(destinations) == 1:
                destination = destinations[0]
                print("Destination for '" + source + "' found: " + destination)
            else:
                print("No destination found for '" + source + "'.")
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

    def logout(self):
        self.apipost({'action':"logout",'format':"json"})
        print("Logged out.")

if __name__ == "__main__":
    main()