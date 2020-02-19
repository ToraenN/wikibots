"""
    "AutoToraen": One script to rule them all.
"""

import re
import requests
from getpass import getpass
from datetime import datetime, date, time
from time import sleep

def main():
    # Initial login
    bot = BotSession()
    # Build the job listing
    jobs = []
    jobs.append(("Find and replace.", bot.typo)) # Perform find/replace operations
    jobs.append(("Update links to moved pages.", bot.mplf)) # Link fixing
    jobs.append(("Convert subpage links.", bot.sublinker)) # Change absolute links to subpages into relative links, or vice versa
    jobs.append(("Convert external links to interwiki links.", bot.interwiki)) # Convert external links to interwiki links where possible
    jobs.append(("Swap gw/gww interwiki links.", bot.wikiswap)) # Convert [[gw:]] links to [[gww:]] links or vice versa
    jobs.append(("Check accuracy of ratings.", bot.ratingcheck)) # Check the ratings of a build and update Real-Vetting tag if neccessary
    jobs.append(("Move userspace to new name.", bot.sweep)) # Userspace move
    jobs.append(("Resign user. (requires admin)", bot.resign)) # Userspace delete
    jobs.append(("Reverse deletions. (requires admin)", bot.oops)) # Reverse deletions
    jobs.append(("Change account.", bot.relog)) # Change to a different account
    jobs.append(("Logout.", bot.exit)) # Exit script
    message = "\nWhat would you like to do?"
    for job in jobs:
        jobmessage = job[0]
        message += "\n" + str(jobs.index(job)) + ": " + jobmessage
    message += "\nChoose the number of your job: "
    # Prompt user for selection, loop so that we can do multiple things without having to re-launch
    while True:
        if bot.loggedin != "Success": # If we selected to change account or previous login failed, bring up login prompt again
            bot = BotSession()
        jobid = inputint(message, len(jobs))
        ((jobs[jobid])[1])() # Run the selected job.

def statuscheck(apicall):
    '''Checks for an HTTP error response.'''
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
    '''Used for any prompt that has you pick from a list.'''
    answer = input(prompt)
    try:
        answer = int(answer)
    except:
        pass
    while (isinstance(answer, int) == False) or (int(answer) not in range(limit)):
        try:
            answer = int(input('Invalid entry, please enter an integer within range: '))
        except ValueError:
            pass
    return answer

def regexbuild(source, destination):
    '''Build the regexes for finding links/templates to update.'''
    regexsource =  "\[+" + source.replace("'", "(%27|')").replace(":", "(%3A|:)").replace(" ", "[_ ]").replace(":", "\:[_ ]{0,1}") + "[_ ]{0,1}(?=[\]\|#])"
    regexsource2 = "\{+" + source.replace("'", "(%27|')").replace(":", "\|").replace(" ", "[_ ]").replace(":", "\:[_ ]{0,1}") + "[_ ]{0,1}\}+"
    regex1 = re.compile(regexsource, re.I) # This covers most wikilinks
    regex2 = re.compile(regexsource2, re.I) # This one is for the {{Build}} template used for the admin noticeboard/user talks
    # Build the replace strings
    replace1 = "[[" + destination
    # If the destination is not another Build: namespace article, the {{Build}} template needs to be replaced with a link
    if re.search("^Build:", destination) != None:
        replace2 = "{{" + destination.replace(":", "|") + "}}"
    else:
        replace2 = "[[" + destination + "]]"
    regexes = {source:[regex1, replace1, regex2, replace2]}
    return regexes

def settimestamp(prompt):
    '''Prompts user for a timestamp, padded for use with mediawiki api.'''
    timestamp = str(inputint('Enter the time (UTC) to start searching the ' + prompt + ' from (YYYYMMDDHHMMSS): ', 100000000000000)).ljust(14, "0")
    return timestamp

def refreshtimestamp():
    '''Returns the current time, padded for use with mediawiki api.'''
    timestamp = str(datetime.utcnow()).replace("-","").replace(" ","").replace(":","")
    timestamp = (timestamp.split("."))[0]
    return timestamp

class BotSession:
    '''All functions that require the session's variables are methods of this class.'''
    def __init__(self, url = "https://gwpvx.gamepedia.com/api.php", login = True, edit = True):
        self.url = url
        self.session = requests.Session()
        if login:
            # Using the main account for login is not supported. Obtain credentials via Special:BotPasswords
            username = input("Bot username: ")
            # Blank username exits script
            if username == "":
                raise SystemExit()
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
            
            self.loggedin = self.apipost(params_login)['login']['result']
            print("Login " + self.loggedin + "!")
            del logintoken, params_login, username, password
            if self.loggedin != 'Success':
                print("Login failed. Please ensure login details are correct.")
            
        # Get an edit token
        if edit:
            params_csrftoken = {
                'action':"query",
                'meta':"tokens",
                'format':"json"
            }
            
            self.csrftoken = self.apipost(params_csrftoken)['query']['tokens']['csrftoken']
        else:
            self.csrftoken = ""
    
    def mplf(self):
        '''Update links to moved pages.'''
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
            waittime = inputint("How many minutes would you like to wait between checks? (1-60 minutes): ", 61)
            if waittime < 1:
                waittime = 60
            else:
                waittime *= 60
            print("Press Ctrl+C to stop listening.")
            try:
                while True:
                    sleep(waittime)
                    newtimestamp = refreshtimestamp()
                    moveentries = self.checklog('move', timestamp = timestamp)
                    if len(moveentries) == 0:
                        print("No moves detected since " + timestamp + "!")
                    movelist, titlelist = self.parsemoveentries(moveentries)
                    regexdict = self.finddestinations(movelist, timestamp = timestamp, prompt = False)
                    for title in titlelist:
                        self.updatelinks(title, regexdict)
                    timestamp = newtimestamp
            except KeyboardInterrupt:
                pass

    def oops(self):
        '''Undo deletions.'''
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
        '''Moves all pages in one userspace to another.'''
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
        '''Deletes all pages in a given userspace.'''
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

    def sublinker(self):
        '''Convert subpage links (either direction).'''
        message = "Would you like to:\n0: Convert to relative links?\n1: Convert to absolute links?\nChoose a number: "
        subjobid = inputint(message, 2)
        basepage = input("Base page (including namespace): ")
        if not self.pageexist(basepage):
            print(basepage + " does not exist.")
            return
        pagetext = self.readpage(basepage)
        if subjobid == 0:
            reason = "Converting to relative links."
            linkregex = re.compile("\[+" + basepage + "(?=/)")
            replace = "[["
        if subjobid == 1:
            reason = "Converting to absolute links."
            linkregex = re.compile("\[+/")
            replace = "[[" + basepage + "/"
        newtext = re.sub(linkregex, replace, pagetext)
        if pagetext != newtext:
            success = self.editpage(basepage, newtext, reason)
            if success:
                print("Links on " + basepage + " updated.")
            else:
                print("WARNING: edit to " + basepage + " not successful!")
        else:
            print("No edits to " + basepage + " need to be made.")

    def interwiki(self):
        '''Convert external links to interwiki links.'''
        while True:
            basepage = input("Base page or category: ")
            if basepage == "":
                break
            if not self.pageexist(basepage):
                print(basepage + " does not exist.")
                continue
            if re.match(r'Category:', basepage):
                pagelist = self.getcategory(basepage)
            else:
                pagelist = [basepage]
            for page in pagelist:
                pagetext = self.readpage(page)
                newtext = pagetext
                regex = { # Links to an api.php or index.php using parameters are ignored.
                    'gww:':re.compile('(\[https{0,1}://wiki\.guildwars\.com/wiki/)(?!api\.php)(?!index\.php\?.*?&.*?=).*?( .*?\])'),
                    'gw:':re.compile('(\[https{0,1}://guildwiki\.gamepedia\.com/)(?!api\.php)(?!index\.php\?.*?&.*?=).*?( .*?\])'),
                    '':re.compile('(\[https{0,1}://gwpvx\.gamepedia\.com/)(?!api\.php)(?!index\.php\?.*?&.*?=).*?( .*?\])'),
                    'scw:':re.compile('(\[https{0,1}://wiki\.fbgmguild\.com/)(?!api\.php)(?!index\.php\?.*?&.*?=).*?( .*?\])')
                }
                for a, b in regex.items(): #'a' is the prefix to use for the interwiki link (or blank for internal link), 'b' is the regex that finds the associated external links
                    search = True
                    while search:
                        search = re.search(b, newtext)
                        if search:
                            groupA = "[[" + a
                            groupB = (search[2]).replace(" ", "|", 1).replace("]", "]]", 1)
                            newtext = newtext.replace(search[1], groupA, 1).replace(search[2], groupB, 1)
                if pagetext != newtext:
                    success = self.editpage(page, newtext, "Converting external links to interwiki links.")
                    if success:
                        print("External links on " + page + " updated.")
                    else:
                        print("WARNING: edit to " + page + " not successful!")
                else:
                    print("No edits to " + page + " need to be made.")

    def wikiswap(self):
        '''Convert gww: to gw: or vice versa'''
        message = "\nDo you want to:\n0: Convert Guildwiki links to Guild Wars Wiki links?\n1: Convert Guild Wars Wiki links to Guildwiki links?\nChoose a number: "
        subid = inputint(message, 2)
        if subid == 0:
            source = "Guildwiki"
            target = "Guild Wars Wiki"
            url = "https://wiki.guildwars.com/api.php"
            regexprefix = '\[+[Gg][Ww]:'
            replaceprefix = '[[gww:'
        elif subid == 1:
            source = "Guild Wars Wiki"
            target = "Guildwiki"
            url = "https://guildwiki.gamepedia.com/api.php"
            regexprefix = '\[+[Gg][Ww][Ww]:'
            replaceprefix = '[[gw:'
        message = "\nConvert all possible links?\n0: Yes.\n1: Let me pick for each link.\nChoose a number: "
        manual = inputint(message, 2)
        wikireader = BotSession(url, login = False, edit = False) # Create a secondary read-only session for querying target wiki's api
        existref = dict() # Remember which GW pages have been checked for existence
        while True:
            pagelist = self.makepagelist()
            if len(pagelist) == 0:
                break
            regex = re.compile(regexprefix + '(.*?)\|')
            for page in pagelist:
                pagetext = self.readpage(page)
                newtext = pagetext
                search = re.findall(regex, newtext)
                search = set(search)
                for link in search:
                    try: # Check the dictionary first
                        if existref[link]:
                            linkexist = True
                        else:
                            linkexist = False
                    except KeyError: # Only check target wiki if the page isn't in the dictionary yet
                        if wikireader.pageexist(link):
                            existref.update({link:True})
                            linkexist = True
                        else:
                            existref.update({link:False})
                            linkexist = False
                    if linkexist:
                        if manual:
                            message = "Convert link to " + link + "? (type n to skip link) "
                            if input(message) == "n":
                                continue
                        swap = re.compile(regexprefix + link)
                        newtext = re.sub(swap, replaceprefix + link, newtext)
                    else:
                        print(source + ' page "' + link + '" has no counterpart on ' + target +'.')
                if pagetext != newtext:
                    success = self.editpage(page, newtext, "Swapping " + source + " interwiki links to " + target + ".")
                    if success:
                        print(source + " links on " + page + " changed to " + target + " links.")
                    else:
                        print("WARNING: edit to " + page + " not successful!")
                else:
                    print("No edits to " + page + " need to be made.")

    def typo(self):
        '''Performs find/replace operations on page or category.'''
        summary = input("Edit summary for all changes: ")
        if summary == "":
            summary = "Bot replacement."
        mode = inputint("\n0:Simple\n1:Regular expressions\nChoose a search mode: ",2)
        print("")
        frpairs = dict()
        index = 0
        while True:
            index += 1
            if mode == 0:
                find = input("Wikitext to find " + str(index) + ": ")
            elif mode == 1:
                find = input("Regular expression " + str(index) + ": ")
            if find != "":
                replace = input("Replace with: ")
                frpairs.update({find:replace})
            else:
                break
        print("")
        while True:
            pagelist = self.makepagelist()
            if len(pagelist) == 0:
                break
            for page in pagelist:
                try:
                    oldtext = self.readpage(page)
                    newtext = oldtext
                    for find, replace in frpairs.items():
                        if mode == 0:
                            newtext = newtext.replace(find, replace)
                        elif mode == 1:
                            newtext = re.sub(find, replace, newtext)
                    if oldtext != newtext:
                        success = self.editpage(page, newtext, summary)
                        if success:
                            print(page + " updated.")
                        else:
                            print("WARNING: edit to " + page + " not successful!")
                    else:
                        print("No edits to " + page + " need to be made.")
                except:
                    print("Editing cancelled suddenly. Please verify the bot's edits on the wiki.")

    def ratingcheck(self):
        '''View the rating page of a build and find the overall rating. Then update the displayed rating.'''
        votereader = BotSession("https://gwpvx.gamepedia.com/index.php", login = False, edit = False)
        while True:
            pagelist = self.makepagelist("Page or category: ")
            if not pagelist:
                break
            for page in pagelist:
                wikitext = self.readpage(page)
                newtext = str(wikitext)
                templaterating = False # Fixme: write function for determining rating in template
                templatestatus = False # Fixme: ditto for status
                if templaterating == "trial" or templaterating == "abandoned" or templaterating == "archived":
                    continue # Skip builds that don't need evaluation
                if templaterating == "testing":
                    testingage = False # Fixme: write function for determining age in testing category
                
                params_readratings = {
                    'title':page,
                    'action':"rate"
                }
            
                response = votereader.session.get(url = votereader.url, params = params_readratings)
                ratepage = response.text
                ratefind = re.compile('Rating totals: (\d*?) votes.*?Overall.*?class="tdresult">(\d\.\d\d)<\/td><\/tr>', re.DOTALL)
                ratestring = ratefind.search(ratepage)
                if ratestring:
                    ratecount = int(ratestring.group(1))
                    rating = float(ratestring.group(2))
                else: # No rating found or login is unrecognized.
                    continue
                return # The rest of this is psuedocode/untested and shouldn't run
                
                if rating:
                    print("There are " + str(ratecount) + " votes. The rating of " + page + " is " + str(rating))
                else:
                    print("No rating found for " + page)
                
                if ratecount >= 5: # Handle as fully vetted build
                    newtext = re.sub("\|status=provisional\|", "|", newtext)
                    if rating >= 4.75:
                        newtext = re.sub("\|rating=.?\|", "|rating=great|", newtext)
                    elif rating >= 3.75:
                        newtext = re.sub("\|rating=.?\|", "|rating=good|", newtext)
                    else:
                        if templaterating != "trash":
                            newtext = re.sub("\|date=.*?\|", "|", wikitext)
                            newtext = re.sub("\|rating=.?\|", "|rating=trash|~~~~~", newtext)
                elif ratecount >= 2: # Handle as provisionally vetted build (unless meta)
                    if templaterating == "testing":
                        if testingage < "2 weeks": # Fixme: Relies on yet to be built function
                            continue
                    if not templatestatus: # If either status is defined, we won't overwrite it
                        newtext = re.sub("\{+Real-Vetting\|", "{{Real-Vetting|status=provisional", newtext)
                    if rating >= 4.75:
                        newtext = re.sub("\|rating=.?\|", "|rating=great|", newtext)
                    elif rating >= 3.75:
                        newtext = re.sub("\|rating=.?\|", "|rating=good|", newtext)
                    else:
                        if templaterating != "trash":
                            newtext = re.sub("\|date=.*?\|", "|", wikitext)
                            newtext = re.sub("\|rating=.?\|", "|rating=trash|~~~~~", newtext)
                else: # Revert to testing if rating has been erroneously applied
                    newtext = re.sub("\|rating=.?\|", "|rating=testing|", newtext)
                    newtext = re.sub("\|status=provisional\|", "|", newtext)

    def apiget(self, parameters):
        '''All GET requests go through this method.'''
        while True:
            apicall = self.session.get(url = self.url, params = parameters)
            if statuscheck(apicall):
                break
        result = apicall.json()
        return result

    def apipost(self, parameters):
        '''All POST requests go through this method.'''
        while True:
            apicall = self.session.post(url = self.url, data = parameters)
            if statuscheck(apicall):
                break
        result = apicall.json()
        return result

    def makepagelist(self, prompt = "Base page or category: "):
        '''Interprets user input as either a single page or a category to get pages from.'''
        pagelist = []
        basepage = input(prompt)
        if basepage == "":
            return pagelist
        if not self.pageexist(basepage):
            print(basepage + " does not exist.")
        if re.match(r'Category:', basepage):
            pagelist = self.getcategory(basepage)
        else:
            pagelist.append(basepage)
        return pagelist

    def getcategory(self, category):
        '''Retrieve all members of a category.'''
        params_category = {
            'action':"query",
            'list':"categorymembers",
            'cmlimit':"max",
            'cmtitle':category,
            'format':"json"
        }
        
        pagelist = []
        while True:
            result = self.apiget(params_category)
            catmembers = result['query']['categorymembers']
            for c in catmembers:
                pagelist.append(c['title'])
            try:
                continuestr = result['continue']['cmcontinue']
                params_category = {
                    'action':"query",
                    'list':"categorymembers",
                    'cmlimit':"max",
                    'cmtitle':category,
                    'cmcontinue':continuestr,
                    'format':"json"
                }
            except:
                break
        return pagelist

    def getuserpages(self, username):
        '''Retrieve all userspace subpages'''
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
        '''Read a given log.'''
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
        '''Check if a page exists.'''
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
        '''Check if the supplied page is a redirect.'''
        text = self.readpage(page)
        if re.search("^#REDIRECT \[\[", text, re.I):
            redirect = True
        else:
            redirect = False
        return redirect

    def editpage(self, page, pagetext, reason):
        '''Commit an edit to a page.'''
        params_editpage = {
            'action':"edit",
            'title':page,
            'bot':"true",
            'summary':reason,
            'text':pagetext,
            'token':self.csrftoken,
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
        '''Move a page to a new title.'''
        params_move = {
            'action':"move",
            'from':oldpage,
            'to':newpage,
            'reason':"Username change",
            'noredirect':"yes",
            'format':"json",
            'token':self.csrftoken
        }
        
        moveresult = self.apipost(params_move)
        
        try:
            print("'" + moveresult['move']['from'] + "' moved to '" + moveresult['move']['to'] + "'.")
            regexdict.update(regexbuild(oldpage, newpage))
        except KeyError:
            print("'" + oldpage + "' to '" + newpage + "':" + moveresult['error']['info'])
        return moveresult

    def whatlinkshere(self, page):
        '''Return all pages that link to a given page.'''
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
        '''Update links of moved pages.'''
        pagetext = self.readpage(page)
        newpagetext = pagetext
        for a, b in regexdict.items():
            newpagetext = re.sub(b[0], b[1], newpagetext)
            newpagetext = re.sub(b[2], b[3], newpagetext)
            if page in a:
                sublink = re.sub("^" + page, "", a)
                regexsublink = re.compile("\[+" + sublink.replace("'", "(%27|')").replace(":", "(%3A|:)").replace(" ", "[_ ]").replace(":", "\:[_ ]{0,1}") + "[_ ]{0,1}(?=[\]\|#])", re.I)
                newpagetext = re.sub(regexsublink, b[1] , newpagetext)
        if newpagetext == pagetext:
            print("No changes made to " + page + ". Broken links not identified.") # Caused by templates/link formats the script does not yet account for
            return
        status = self.editpage(page, newpagetext, "Updating links of moved pages")
        if status:
            print("Links on '" + page + "' updated.")
        else:
            print("WARNING: Success message not received for '" + page + "'!")

    def readpage(self, page):
        '''Get page wikitext.'''
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
        '''Delete a page (all revisions).'''
        params_delete = {
            'action':"delete",
            'title':page,
            'reason':reason,
            'format':"json",
            'token':self.csrftoken
        }
        
        result = self.apipost(params_delete)
        try:
            result['delete']
            print("'" + page + "' deleted.")
        except KeyError:
            print("Could not delete '" + page + "'. Error code: " + result['error']['code'])
        return result

    def restorepage(self, page, reason):
        '''Restore a deleted page (all revisions).'''
        params_restore = {
            'action':"undelete",
            'title':title,
            'reason':reason,
            'token':self.csrftoken,
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
        '''Determine which move entries require links to be updated.'''
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
        '''Determine the new destinations for links to be updated.'''
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
                if self.pageexist(movetarget) and not self.isredirect(movetarget):
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
            regexdict.update(regexbuild(source, destination))
        return regexdict

    def logout(self):
        '''End the session.'''
        params_logout = {
            'action':"logout",
            'token':self.csrftoken,
            'format':"json"
        }
        
        self.apipost(params_logout)
        print("Logged out.")

    def relog(self):
        self.logout()
        self.loggedin = False

    def exit(self):
        self.logout()
        raise SystemExit()

if __name__ == "__main__":
    main()