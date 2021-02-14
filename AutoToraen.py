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
    jobs.append(("Update links to moved/deleted pages.", bot.mplf)) # Link fixing
    jobs.append(("Convert subpage links.", bot.sublinker)) # Change absolute links to subpages into relative links, or vice versa
    jobs.append(("Convert external links to interwiki links.", bot.interwiki)) # Convert external links to interwiki links where possible
    jobs.append(("Swap gw/gww interwiki links.", bot.wikiswap)) # Convert [[gw:]] links to [[gww:]] links or vice versa
    jobs.append(("Check accuracy of ratings.", bot.ratingcheck)) # Check the ratings of a build and update Real-Vetting tag if neccessary
    jobs.append(("Collect rating data.", bot.ratingcollect)) # Gather overall ratings of selected builds and output them to file
    jobs.append(("Move userspace to new name.", bot.sweep)) # Userspace move
    jobs.append(("Build cleanup list.", bot.cleanuplist)) # Creates a list of pages to be deleted (for mass cleanups)
    jobs.append(("Execute cleanup.", bot.cleanuppurge)) # Mass deletes pages. Uses a list from the 'Build cleanup list' job
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
            continue
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
    parsedsource = source.replace("\\","\\\\").replace("(","\(").replace(")","\)").replace(" ", "[_ ]").replace(":", "(?:%3A|:)[_ ]{0,1}").replace("'", "(?:%27|')") # People sure are creative in linking in weird ways
    templatesource = source.replace("\\","\\\\").replace("(","\(").replace(")","\)").replace(":", "\|").replace("'", "(%27|')").replace(" ", "[_ ]") # For {{Build}}
    if destination:
        regexsource = "\[\[[_ ]{0,}" + parsedsource + "[_ ]{0,}[^ -~]{0,}(?=[\]\|#])"
        regexsource2 = "\{\{" + templatesource + "[_ ]{0,1}[^ -~]{0,}\}\}"
        regex1 = re.compile(regexsource) # This covers most wikilinks
        regex2 = re.compile(regexsource2) # This one is for the {{Build}} template used for the admin noticeboard/user talks
        # Build the replace strings
        replace1 = "[[" + destination
        # If the destination is not another Build: namespace article, the {{Build}} template needs to be replaced with a link
        if re.search("^Build:", destination) != None:
            replace2 = "{{" + destination.replace(":", "|") + "}}"
        else:
            replace2 = "[[" + destination + "]]"
    else:
        regexsource = "\[\[[_ ]{0,}" + parsedsource + "[_ ]{0,1}[^ -~]{0,}(?:#.*?){0,1}(\|.*?){0,1}\]\]"
        regexsource2 = "\{\{" + templatesource + "[_ ]{0,1}[^ -~]{0,}\}\}"
        regex1 = re.compile(regexsource) # This covers most wikilinks
        regex2 = re.compile(regexsource2) # This one is for the {{Build}} template used for the admin noticeboard/user talks
        # Build the replace strings
        replace1 = "{{LogLink|" + source + "{pipedtext}}}"
        replace2 = "{{LogLink|" + source + "}}"
    srpairs = [regex1, replace1, regex2, replace2]
    regexes = {source:srpairs}
    return regexes

def regexbuildrewrite(source, destination): # FIXME
    '''Build the regexes for finding links/templates to update.'''
    parsedsource = source.replace("\\","\\\\").replace("(","\(").replace(")","\)").replace(" ", "[_ ]").replace(":", "(?:%3A|:)[_ ]{0,1}").replace("'", "(?:%27|')") # People sure are creative in linking in weird ways
    templatesource = source.replace("\\","\\\\").replace("(","\(").replace(")","\)").replace(":", "\|").replace("'", "(%27|')").replace(" ", "[_ ]") # For {{Build}}
    # FIXME: remove re.I, replace with specific case insensitive positions in regex (start of namespace & start of title)
    regexsource1 = "\[\[" + parsedsource + "[_ ]{0,1}[^ -~]{0,}(#.*?){0,1}(\|.*?){0,1}\]\]"
    regex1 = re.compile(regexsource1) # This covers most wikilinks
    regexsource2 = "\{\{" + templatesource + "[_ ]{0,1}[^ -~]{0,}\}\}"
    regex2 = re.compile(regexsource2) # This one is for the {{Build}} template used for the admin noticeboard/user talks

    if destination:
        # Build the replace strings
        replace1 = "[[" + destination + "{sectiontext}" + "{pipedtext}" + "]]"
        # If the destination is not another Build: namespace article, the {{Build}} template needs to be replaced with a link
        if re.search("^Build:", destination) != None:
            replace2 = "{{" + destination.replace(":", "|") + "}}"
        else:
            replace2 = "[[" + destination + "]]"
    else:
        # Build the replace strings
        replace1 = "{{LogLink|" + source + "{pipedtext}}}"
        replace2 = "{{LogLink|" + source + "}}"
    srpairs = [(regex1, replace1), (regex2, replace2)]
    regexes = {source:srpairs}
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
                'format':"json",
                'assert':"bot"
            }
            
            self.csrftoken = self.apipost(params_csrftoken)['query']['tokens']['csrftoken']
        else:
            self.csrftoken = ""
    
    def mplf(self):
        '''Update links to moved/deleted pages.'''
        message = "Would you like to:\n0: Enter moves/deletions manually?\n1: Check the logs?\n2: Listen for moves/deletions?\nChoose a number: "
        subjobid = inputint(message, 3)
        if subjobid == 0:
            # Manual entry
            while True:
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
                # If nothing was entered, return to job listing
                if len(moveentries) == 0:
                    break
                movelist, titlelist = self.parselogentries(moveentries)
                regexdict = self.finddestinations(movelist)
                for title in titlelist:
                    self.updatelinks(title, regexdict)
        if subjobid == 1:
            # Check move log from specific date forward
            timestamp = settimestamp('move log')
            username = input('Limit to user: ')
            moveentries = self.checklog('move', username = username, timestamp = timestamp)
            deleteentries = self.checklog('delete', username = username, timestamp = timestamp)
            logentries = moveentries + deleteentries
            movelist, titlelist = self.parselogentries(logentries)
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
                    deleteentries = self.checklog('delete', timestamp = timestamp)
                    logentries = moveentries + deleteentries
                    if len(logentries) == 0:
                        print("No moves or deletions detected since " + timestamp + "!")
                    movelist, titlelist = self.parselogentries(logentries)
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

    def sweep(self): # FIXME: Hits rate limits for moving pages
        '''Moves all pages in one userspace to another.'''
        regexdict = dict()
        fixlist = set()
        # Prompt user for the old & new usernames
        oldusername = input("\nOld username: ")
        newusername = input("New username: ")
        if oldusername == "" or newusername == "":
            print("Aborting.")
            return
        if oldusername == newusername:
            print("Those are the same user.")
            return
        pagelist = self.getuserpages(oldusername)
        # Move pages
        for page in pagelist:
            newpage = re.sub(r'^User:' + oldusername, 'User:' + newusername, page)
            newpage = re.sub(r'^User talk:' + oldusername, 'User talk:' + newusername, newpage)
            status = self.movepage(page, newpage, regexdict)
            sleep(5)
        # Get list of pages with links to fix
        # for page in pagelist:
            # brokenlinkpages = self.whatlinkshere(page)
            # for b in brokenlinkpages:
                # fixlist.add(b)
        # Fix links
        # for page in fixlist:
            # self.updatelinks(page, regexdict)

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
        # Links to an api.php or index.php using parameters are ignored.
        leading = '(\[https{0,1}://'
        trailing = '/)(?!api\.php)(?!index\.php\?.*?&.*?=).*?( .*?\])'
        regex = {
            'gww:':re.compile(leading + 'wiki\.guildwars\.com/wiki' + trailing),
            'gw:':re.compile(leading + 'guildwiki\.gamepedia\.com' + trailing),
            '':re.compile(leading + 'gwpvx\.gamepedia\.com' + trailing),
            'scw:':re.compile(leading + 'wiki\.fbgmguild\.com' + trailing)
        }
        while True:
            pagelist = self.makepagelist()
            if pagelist == None:
                break
            for page in pagelist:
                pagetext = self.readpage(page)
                newtext = pagetext
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
            if pagelist == None:
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
                if find != "":
                    replace = input("Replace with: ")
                    frpairs.update({find:replace})
                else:
                    break
            elif mode == 1:
                find = input("Regular expression " + str(index) + ": ")
                if find != "":
                    try:
                        find = re.compile(find)
                    except:
                        print("Invalid regular expression.")
                        index -= 1
                        continue
                    replace = input("Replace with: ")
                    frpairs.update({find:replace})
                else:
                    break
        
        while True:
            pagelist = self.makepagelist()
            if pagelist == None:
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
        templateratefind = re.compile('{{Real-Vetting\|.*?rating=(\w*)')
        templatestatusfind = re.compile('{{Real-Vetting\|.*?status=(\w*)')
        ratefind = re.compile('Rating totals: (\d*?) votes.*?Overall.*?(\d\.\d\d)', re.DOTALL)
        goodthreshold = 3.75
        greatthreshold = 4.75
        votesrequired = 5
        provisrequired = 2
        while True:
            pagelist = self.makepagelist()
            if pagelist == None:
                break
            for page in pagelist:
                wikitext = self.readpage(page)
                newtext = str(wikitext)
                templaterating = templateratefind.search(wikitext)
                templatestatus = templatestatusfind.search(wikitext)
                if not templaterating:
                    templaterating = "undefined"
                else:
                    templaterating = templaterating.group(1)
                    templaterating = templaterating.casefold()
                
                if not templatestatus:
                    templatestatus = "undefined"
                else:
                    templatestatus = templatestatus.group(1)
                    templatestatus = templatestatus.casefold()
                
                if templaterating == "undefined" or templaterating == "trial" or templaterating == "abandoned" or templaterating == "archived":
                    print(page + ": page is not eligible for rating.")
                    continue # Skip pages that don't need evaluation
                elif templaterating == "testing":
                    testingage = False # Fixme: write function for determining age in testing category
                
                params_readratings = {
                    'title':page,
                    'action':"rate"
                }
            
                response = votereader.session.get(url = votereader.url, params = params_readratings)
                ratepage = response.text
                ratestring = ratefind.search(ratepage)
                if ratestring:
                    ratecount = int(ratestring.group(1))
                    rating = float(ratestring.group(2))
                else: # No rating found.
                    ratecount = 0
                    rating = 0.0
                print(page + ": " + str(ratecount) + " ratings. Overall: " + str(rating) + ". Template rating: " + templaterating + ". Status: " + templatestatus + ".")
                
                if ratecount >= votesrequired: # Handle as fully vetted build
                    newtext = re.sub("\|status=provisional\|", "|", newtext)
                    if rating >= greatthreshold and templaterating != "great":
                        newtext = re.sub("\|date=.*?\|", "|", newtext)
                        newtext = re.sub("\|rating=.*?\|", "|rating=great|", newtext)
                    elif rating >= goodthreshold and rating < greatthreshold and templaterating != "good":
                        newtext = re.sub("\|date=.*?\|", "|", newtext)
                        newtext = re.sub("\|rating=.*?\|", "|rating=good|", newtext)
                    elif rating < goodthreshold and templaterating != "trash":
                        newtext = re.sub("\|date=.*?\|", "|", newtext)
                        newtext = re.sub("\|rating=.*?\|", "|rating=trash|date=~~~~~|", newtext)
                elif ratecount >= provisrequired: # Handle as provisionally vetted build (unless meta)
                    # if templaterating == "testing":
                        # if testingage < "2 weeks": # Fixme: Relies on yet to be built function
                            # continue
                    if templatestatus != "meta" and templatestatus != "provisional": # If status is validly defined, we won't overwrite/duplicate it
                        newtext = re.sub("\|status=.*?\|", "|", newtext) # Remove any invalid status if present
                        newtext = re.sub("\{\{Real-Vetting\|", "{{Real-Vetting|status=provisional|", newtext)
                    if rating >= greatthreshold and templaterating != "great":
                        newtext = re.sub("\|date=.*?\|", "|", newtext)
                        newtext = re.sub("\|rating=.*?\|", "|rating=great|", newtext)
                    elif rating >= goodthreshold and rating < greatthreshold and templaterating != "good":
                        newtext = re.sub("\|date=.*?\|", "|", newtext)
                        newtext = re.sub("\|rating=.*?\|", "|rating=good|", newtext)
                    elif rating < goodthreshold and templaterating != "trash":
                        newtext = re.sub("\|date=.*?\|", "|", newtext)
                        newtext = re.sub("\|status=.*?\|", "|", newtext)
                        newtext = re.sub("\|rating=.*?\|", "|rating=trash|date=~~~~~|", newtext)
                else: # Revert to testing if rating has been erroneously applied
                    newtext = re.sub("\|date=.*?\|", "|", newtext)
                    newtext = re.sub("\|status=provisional\|", "|", newtext)
                    newtext = re.sub("\|rating=.*?\|", "|rating=testing|", newtext)
                if wikitext != newtext:
                    success = self.editpage(page, newtext, "Updating to verified rating.")
                    if success:
                        print("Rating of " + page + " has been updated.")
                    else:
                        print("WARNING: Attempt to update rating of " + page + " has failed.")
                else:
                    print("Rating of " + page + " is correct.")

    def ratingcollect(self):
        '''Collect overall rating data. Then output to file.'''
        votereader = BotSession("https://gwpvx.gamepedia.com/index.php", login = False, edit = False)
        ratefind = re.compile('Rating totals: (\d*?) votes.*?Overall.*?(\d\.\d\d)', re.DOTALL)
        file = inputint("Write to file?\n0: Yes\n1: No\nAnswer: ", 2)
        while True:
            pagelist = self.makepagelist()
            if pagelist == None:
                break
            for page in pagelist:
                
                params_readratings = {
                    'title':page,
                    'action':"rate"
                }
            
                response = votereader.session.get(url = votereader.url, params = params_readratings)
                ratepage = response.text
                ratestring = ratefind.search(ratepage)
                if ratestring:
                    ratecount = int(ratestring.group(1))
                    rating = float(ratestring.group(2))
                else: # No rating found.
                    ratecount = 0
                    rating = 0.0
                print(page, "| Rating:", rating, "Votes:", ratecount)
                if not file:
                    with open("Build Ratings.txt", "a") as outfile:
                        outfile.write(page + "," + str(rating) + "," + str(ratecount) + "\n")

    def cleanuplist(self):
        # Check for existing exclusion list (text file containing regex strings)
        #   Allow entry for new exclusion list if none found
        # Query for settings (namespace, link tolerance maybe)
        # Get namespace pagelist
        # For each page:
        #   Check against exclusion list
        #   Check for whatlinkshere/whatembedsthis in:
        #       Other namespaces
        #       The exclusion list
        #   Add to final purge list if all checks come back empty
        #   Add to excluded pages list with reason(s) if checks found something
        pass
    
    def cleanuppurge(self):
        # Check for existing purge list
        #   If no purge list, exit job
        # For each page:
        #   Delete page - default reason: "Mass cleanup" (but user should enter detailed reason linking to project)
        #   Nothing else should be needed, as all pages that would still be linked to should not have been added to the purge list
        pass

    def apiget(self, parameters):
        '''All GET requests go through this method.'''
        while True:
            apicall = self.session.get(url = self.url, params = parameters)
            if statuscheck(apicall):
                try:
                    result = apicall.json()
                    break
                except:
                    input("JSONDecodeError - could not parse response as JSON.\nParamaters: " + str(parameters))            
        return result

    def apipost(self, parameters):
        '''All POST requests go through this method.'''
        while True:
            apicall = self.session.post(url = self.url, data = parameters)
            if statuscheck(apicall):
                try:
                    result = apicall.json()
                    break
                except:
                    input("JSONDecodeError - could not parse response as JSON.\nParamaters: " + str(parameters)) 
        return result

    def makepagelist(self):
        '''Builds the list of pages to be processed by the calling function based on user input.'''
        pagelist = set()
        print("\nPlease enter a:\nPagename - to process a single non-category page\nCategory: - to process all pages in a category\n:Category: - to process a category page\nSpecial:Whatlinkshere/ - to process all pages that link to a title\nLeave last entry blank to start processing.")
        while True:
            basepage = input("Entry: ")
            if basepage == "":
                break
            if re.match(r'Category:', basepage):
                pagelist.update(set(self.getcategory(basepage)))
            elif re.match(r':Category:', basepage):
                categorypage = basepage.lstrip(":")
                if self.pageexist(categorypage):
                    pagelist.add(categorypage)
                else:
                    print("Page for " + categorypage + " has not been created.")
            elif re.match(r'Special:WhatLinksHere\/', basepage):
                page = basepage.replace('Special:WhatLinksHere/','')
                pagelist.update(set(self.whatlinkshere(page)))
            elif self.pageexist(basepage):
                pagelist.add(basepage)
            else:
                print(basepage + " does not exist.")
        if len(pagelist) == 0:
            return None
        else:
            return pagelist

    def getcategory(self, category):
        '''Retrieve all non-category members of a category.'''
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
                if not re.match(r"Category:", c['title']):
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
            'format':"json",
            'assert':"bot"
        }
        
        editcommit = self.apipost(params_editpage)
        try:
            status = editcommit['edit']
            if status['result'] == 'Success':
                return True
            else: # Various error handling as they are identified
                try:
                    if status['phalanx']:
                        spamregex = re.compile("The following link, text or pagename is what triggered our spam filter: <b>(.*?)<\/b>")
                        spamsnip = re.search(spamregex, status['phalanx'])[1]
                        userchoice = input("The following text in the page triggered the spam filter and is preventing the edit:\n" + spamsnip + "\nWould you like to remove this text and complete the edit (y/n)? ")
                        if "y" in userchoice:
                            unspampagetext = pagetext.replace(spamsnip, " (removed due to spam filter)")
                            unspamedit = self.editpage(page, unspampagetext, reason)
                            if unspamedit:
                                return True
                        else:
                            return False # Don't need error printed in this case, user decided not to censor
                    else:
                        raise KeyError
                except:
                    raise KeyError
        except KeyError:
            print(status) # Ugly print all the status information; unknown error type but at least we'll inform the user
            return False

    def movepage(self, oldpage, newpage, regexdict): # FIXME: Adjust to move subpages+talk
        '''Move a page to a new title.'''
        params_move = {
            'action':"move",
            'from':oldpage,
            'to':newpage,
            'reason':"Username change",
            'noredirect':"yes",
            'format':"json",
            'token':self.csrftoken,
            'assert':"bot"
        }
        
        moveresult = self.apipost(params_move)
        
        try:
            print("'" + moveresult['move']['from'] + "' moved to '" + moveresult['move']['to'] + "'.")
            regexdict.update(regexbuild(oldpage, newpage))
            return moveresult
        except KeyError:
            print("'" + oldpage + "' to '" + newpage + "':" + moveresult['error']['info'])
            return False

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
        linkpages.update(self.whatembedsthis(page))
        return linkpages

    def whatembedsthis(self, title):
        '''Return all pages that transclude a given page.'''
        embedpages = set()
        params_embedsthis = {
            'action':"query",
            'format':"json",
            'list':"embeddedin",
            'eititle':title,
            'eilimit':"max"
        }
        
        try:
            response = self.apiget(params_embedsthis)['query']['embeddedin']
            for page in response:
                embedpages.add(page['title'])
        except KeyError:
            pass
        return embedpages

    def updatelinks(self, page, regexdict):
        '''Update links of moved pages.'''
        pagetext = self.readpage(page)
        newpagetext = pagetext
        for a, b in regexdict.items():
            if "{{LogLink" in b[1]:
                while True:
                    breakcounter = 0
                    try:
                        findlink = re.search(b[0], newpagetext)
                        matchlink = findlink[0]
                        try:
                            if findlink[1]:
                                pipedreplace = findlink[1]
                            else:
                                pipedreplace = ""
                        except:
                            pipedreplace = ""
                        replacelink = "{" + (b[1]).format(pipedtext=pipedreplace) + "}"
                        newpagetext = newpagetext.replace(matchlink, replacelink)
                    except:
                        breakcounter += 1
                    try:
                        findtemplate = re.search(b[2], newpagetext)
                        matchtemplate = findtemplate[0]
                        replacetemplate = b[3]
                        newpagetext = newpagetext.replace(matchtemplate, replacetemplate)
                    except:
                        breakcounter += 1
                    if breakcounter == 2:
                        break
            else:
                newpagetext = re.sub(b[0], b[1], newpagetext)
                newpagetext = re.sub(b[2], b[3], newpagetext)
            if page in a:
                sublink = re.sub("^" + page, "", a)
                regexsublink = re.compile("\[+" + sublink.replace(" ", "[_ ]").replace(":", "(%3A|:)[_ ]{0,1}").replace("'", "(%27|')") + "[_ ]{0,1}(?=[\]\|#])", re.I)
                newpagetext = re.sub(regexsublink, b[1] , newpagetext)
        if newpagetext == pagetext:
            print("No changes made to " + page + ". Broken links not identified.") # Caused by templates/link formats the script does not yet account for
            return
        status = self.editpage(page, newpagetext, "Updating links.")
        if status:
            print("Links on '" + page + "' updated.")
        else:
            print("WARNING: Success message not received for '" + page + "'!")

    def updatelinksrewrite(self, page, regexdict):
        '''Update links of moved pages.'''
        pagetext = self.readpage(page)
        newpagetext = pagetext
        for source, srpairs in regexdict.items():
            for pair in srpairs:
                pass # FIXME
            if page in source:
                sublink = re.sub("^" + page, "", source)
                regexsublink = re.compile("\[\[" + sublink.replace(" ", "[_ ]").replace(":", "(?:%3A|:)[_ ]{0,1}").replace("'", "(?:%27|')") + "[_ ]{0,1}(?=[\]\|#])", re.I)
                newpagetext = re.sub(regexsublink, srpairs[1], newpagetext) # FIXME: srpairs is not the correct thing to call here
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
            'token':self.csrftoken,
            'assert':"bot"
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
            'format':"json",
            'assert':"bot"
        }
        
        result = self.apipost(params_restore)
        try:
            result['undelete']
            print("'" + title + "' restored.")
        except KeyError:
            print("Could not restore '" + title + "'. Error code: " + result['error']['code'])
        return result

    def parselogentries(self, logentries):
        '''Determine which move entries require links to be updated.'''
        movelist = []
        titlelist = set()
        for entry in logentries:
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
                destination = None
            regexdict.update(regexbuild(source, destination))
        return regexdict

    def logout(self):
        '''End the session.'''
        params_logout = {
            'action':"logout",
            'token':self.csrftoken,
            'format':"json",
            'assert':"bot"
        }
        
        self.apipost(params_logout)
        print("Logged out.")

    def relog(self):
        self.logout()
        self.__init__()

    def exit(self):
        self.logout()
        raise SystemExit()

if __name__ == "__main__":
    main()