This is the script that powers AutoToraen. To use this, you need to set up a bot password via https://gwpvx.gamepedia.com/Special:BotPasswords (using the main credentials of the account is not supported and probably will not work). Make sure to give it the necessary grants to perform page edits, moves and/or deletions depending on what you're going to do, and make sure to check "High Volume Editing". To keep from crowding out Recent Changes, you should only use this script on a bot account. In order to delete/restore your bot account must be flagged as an administrator; you can't give that to yourself just by checking the box in the BotPasswords grant list. 

So far, it can do the following things:

# Find and replace
Does what it says. Accepts simple string substitutions or regular expression matching and can operate on individual pages or categories. It is recommended to test your replacements on a single page before using it on an entire category. You can also have it work from "Special:WhatLinksHere/Pagename".

# Fix links of moved & deleted pages
Given a page name, the script tries to find the name it was moved to (following move chains as needed) and fixes all links to point to the new name. If a destination cannot be found, any links will be converted to a {{LogLink}} template.

Comes in three flavors:
* Manually enter pages
* Crawl the move & deletion logs from a specific time to the present
* Check the move & deletion logs periodically and act on any moves and deletions that occur.

# Convert subpage links
Converts all links to subpages on a given page to relative links or to absolute links.

# Convert external links to interwiki
For links to Guildwiki, Guild Wars Wiki and Speed Clear Wiki (as well as any 'external' links to other PvXwiki pages).

# Convert interwiki links between Guildwiki and Guild Wars Wiki:
Checks that page exists on GWW or GW before converting the link. You can choose either direction to convert and either all possible links or select whether each unique link is converted.

# Update build ratings
Check a build (or category of builds) to ensure its Real-Vetting template matches the real rating, and update the template if necessary.

# Collect build ratings
Outputs overall ratings and vote counts of the selected builds. Gives option to create a text file. Each line will be in the format "build name,rating,vote count"

# Userspace moves
Moves all of a userspaces subpages to a new name and updates links to them.

# RESIGN
Nukes a userspace as per a PvX:RESIGN request (leaving PvXwiki permanently, removing personal info). Requires admin to work.

# Reverse accidental deletions
Crawls the delete log from a specific time to the present (and optionally restricted to a specific user's deletions) and prompts the script user to undelete pages. Requires admin to work.