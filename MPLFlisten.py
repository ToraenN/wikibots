"""
    "Moved Page Link Fixer (Auto)": Combs the move log to update links to moved pages.
"""

import re
import requests
from datetime import datetime, date, time
from time import sleep

def inputint(prompt):
    answer = input(prompt)
    try:
        answer = int(answer)
    except:
        pass
    while isinstance(answer, int) == False:
        try:
            answer = int(input('Invalid entry, please enter an integer: '))
        except:
            pass
    return answer

def starttimestamp():
	timestamp = str(datetime.utcnow()).replace("-","").replace(" ","").replace(":","")
	timestamp = (timestamp.split("."))[0]
	return timestamp

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

# Get an edit token
params_edittoken = {
    'action':"query",
    'meta':"tokens",
    'format':"json"
}

apicall = session.post(url, data= params_edittoken)
result = apicall.json()

edittoken = result['query']['tokens']['csrftoken']
#Initial timestamp
boundtime = starttimestamp()
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
		'lelimit':100,
		'ledir':"newer",
		'lestart':boundtime,
		'format':"json"
	}

	apicall = session.get(url=url, params= params_movelog)
	result = apicall.json()
	boundtime = starttimestamp()
	entrylist = result['query']['logevents']
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
		
		apicall = session.get(url=url, params= params_exist)
		result = apicall.json()
		
		try:
			result['query']['pages']['-1']
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

		apicall = session.post(url, data=params_linkshere)
		result = apicall.json()
		try:
			pagelist = result['query']['pages']["-1"]['linkshere'] # -1 will be provided as a placeholder for the page id for any missing page
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
		
		apicall = session.get(url=url, params=params_movecheck)
		result = apicall.json()
		
		movedlist = result['query']['logevents']
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
			
			apicall = session.get(url=url, params=params_movecheck)
			result = apicall.json()
			
			appendlist = result['query']['logevents']
			for item in appendlist:
				if not item in movedlist:
					movedlist.append(item)
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
		if len(destinations) > 1:
			destquery = "Found " + str(len(destinations)) + " possible destinations for '" + source + "':"
			for d in destinations:
				destquery += "\n" + str(destinations.index(d)) + ": " + str(d)
			destquery += "\nChoose the number of the destination: "
			try:
				destination = destinations[int(input(destquery))]
			except:
				print("No destination found for '" + source + "'.")
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
		
		apicall = session.post(url, data= params_listentry)
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
	#Wait a bit
	sleep(60)
# Logout
session.post(url, data= {'action':"logout"})
