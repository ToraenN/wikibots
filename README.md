# wikibots
This is the script that powers AutoToraen. To use this, you need to set up a bot password via https://gwpvx.gamepedia.com/Special:BotPasswords (using the main credentials of the account is not supported and probably will not work). Make sure to give it the necessary grants to perform page edits, moves and/or deletions depending on what you're going to do, and make sure to check "High Volume Editing". To keep from crowding out Recent Changes, you should only use this script on a bot account. In order to delete/restore your bot account must be flagged as an administrator; you can't give that to yourself just by checking the box in the BotPasswords grant list. 

So far, it can do the following things:

# Fix links of moved pages
Given a page name, the script tries to find the name it was moved to (following move chains as needed) and fixes all links to point to the new name. Comes in three flavors:
* Manually enter pages
* Crawl the move log from a specific time to the present
* Check the move log periodically and act on any moves that occur.

# Reverse accidental deletions
Crawls the delete log from a specific time to the present (and optionally restricted to a specific user's deletions) and prompts the script user to undelete pages.

# Userspace moves
Moves all of a userspaces subpages to a new name and updates links to them.

# RESIGN
Nukes a userspace as per a PvX:RESIGN request (leaving PvXwiki permanently, removing personal info)


