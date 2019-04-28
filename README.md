# wikibots
Here be my scripts for fixing the endless tide of maintenance issues on PvXwiki. Probably adaptable to other wikis, but most of them probably didn't let things get so bad in the first place.

# MPLF: Moved Page Link Fixer
Given a page name, tries to find the name it was moved to and fixes all links to point to the new name. Comes in three flavors:
* MPLF: Manually enter pages
* MPLFauto: Crawl the move log from a specific time to the present
* MPLFlisten: Query the API every minute and act on any moves that occur.

# SWEEP: Userspace Sweeper
Moves all of a userspaces subpages to a new name and updates links to them. Ignores the root pages since they were auto-moved when the username changed during database migration.

# RESIGN: Resign bot
Nukes a userspace as per a PvX:RESIGN request (leaving PvXwiki permanently, removing personal info)

# Oops: Restore bot
Crawls the delete log for a given username and prompts the script user to undelete pages.
