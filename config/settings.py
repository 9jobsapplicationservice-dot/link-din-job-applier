'''
Author:     Mayank Sodhi
LinkedIn:   https://www.linkedin.com/in/mayank-sodhi-84924a223/

Copyright (C) Mayank Sodhi

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

Support me: https://github.com/sponsors/GodsScion

version:    26.01.20.5.08
'''


###################################################### CONFIGURE YOUR BOT HERE ######################################################

# >>>>>>>>>>> LinkedIn Settings <<<<<<<<<<<

# Keep the External Application tabs open?
close_tabs = False                  # True or False, Note: True or False are case-sensitive
'''
Note: RECOMMENDED TO LEAVE IT AS `True`, if you set it `False`, be sure to CLOSE ALL TABS BEFORE CLOSING THE BROWSER!!!
'''

# Follow easy applied companies
follow_companies = False            # True or False, Note: True or False are case-sensitive

# Send connection requests to HR profiles after successful application logging.
connect_hr = True                   # True or False, Note: True or False are case-sensitive

# Optional note for connection request. Empty means send without note.
connect_request_message = ""

# Follow recruiter profile on LinkedIn after HR profile is opened.
follow_hr = True                    # True or False, Note: True or False are case-sensitive

# Soft cap for recruiter action attempts per run to avoid invite-limit pressure.
max_hr_connect_attempts_per_run = 40   # Integer >= 1

# Retry passes for connect action on recruiter profile (1-3 recommended).
retry_hr_connect_passes = 2         # Integer in [1, 2, 3]

# Do you want the program to run continuously until you stop it? (Beta)
run_non_stop = False                # True or False, Note: True or False are case-sensitive
'''
Note: Will be treated as False if `run_in_background = True`
'''
alternate_sortby = True             # True or False, Note: True or False are case-sensitive
cycle_date_posted = True            # True or False, Note: True or False are case-sensitive
stop_date_cycle_at_24hr = True      # True or False, Note: True or False are case-sensitive

# >>>>>>>>>>> External Portal Apply Automation <<<<<<<<<<<

# Enable external portal adapter flow (Workday, Greenhouse, Lever)
enable_external_apply_ai = False      # True or False, Note: True or False are case-sensitive

# Pause before final submit on external portals for manual review
external_apply_pause_before_submit = True      # True or False, Note: True or False are case-sensitive

# Supported external portal adapters
external_apply_portals = ["workday", "greenhouse", "lever"]      # list of strings

# If True, attempt generic autofill on unsupported portals instead of only saving link
external_apply_generic_fallback = True      # True or False, Note: True or False are case-sensitive

# Authentication handling for external portals
external_auth_mode = "manual_first_login"       # "manual_first_login", "auto_login", "skip_auth_required"





# >>>>>>>>>>> RESUME GENERATOR (Experimental & In Development) <<<<<<<<<<<

# Give the path to the folder where all the generated resumes are to be stored
generated_resume_path = "all resumes/" # (In Development)





# >>>>>>>>>>> Global Settings <<<<<<<<<<<

# Directory and name of the files where history of applied jobs is saved (Sentence after the last "/" will be considered as the file name).
file_name = "all excels/all_applied_applications_history.csv"
failed_file_name = "all excels/all_failed_applications_history.csv"
logs_folder_path = "logs/"

# Set the maximum amount of time allowed to wait between each click in secs
click_gap = 3                       # Enter max allowed secs to wait approximately. (Only Non Negative Integers Eg: 0,1,2,3,....)

# If you want to see Chrome running then set run_in_background as False (May reduce performance). 
run_in_background = False           # True or False, Note: True or False are case-sensitive ,   If True, this will make pause_at_failed_question, pause_before_submit and run_in_background as False

# If you want to disable extensions then set disable_extensions as True (Better for performance)
disable_extensions = False          # True or False, Note: True or False are case-sensitive

# Run in safe mode. Set this true if chrome is taking too long to open or if you have multiple profiles in browser. This will open chrome in guest profile!
safe_mode = True                    # True or False, Note: True or False are case-sensitive

# Do you want scrolling to be smooth or instantaneous? (Can reduce performance if True)
smooth_scroll = False               # True or False, Note: True or False are case-sensitive

# If enabled (True), the program would keep your screen active and prevent PC from sleeping. Instead you could disable this feature (set it to false) and adjust your PC sleep settings to Never Sleep or a preferred time. 
keep_screen_awake = True            # True or False, Note: True or False are case-sensitive (Note: Will temporarily deactivate when any application dialog boxes are present (Eg: Pause before submit, Help needed for a question..))

# Run in undetected mode to bypass anti-bot protections (Preview Feature, UNSTABLE. Recommended to leave it as False)
stealth_mode = False                # True or False, Note: True or False are case-sensitive

# Do you want to get alerts on errors related to AI API connection?
showAiErrorAlerts = False            # True or False, Note: True or False are case-sensitive

# Use ChatGPT for resume building (Experimental Feature can break the application. Recommended to leave it as False) 
# use_resume_generator = False       # True or False, Note: True or False are case-sensitive ,   This feature may only work with 'stealth_mode = False'. As ChatGPT website is hosted by CloudFlare which is protected by Anti-bot protections!











############################################################################################################
'''
THANK YOU for using my tool ??! Wishing you the best in your job hunt ????!

Sharing is caring! If you found this tool helpful, please share it with your peers ??. Your support keeps this project alive.

Support my work on <PATREON_LINK>. Together, we can help more job seekers.

As an independent developer, I pour my heart and soul into creating tools like this, driven by the genuine desire to make a positive impact.

Your support, whether through donations big or small or simply spreading the word, means the world to me and helps keep this project alive and thriving.

Gratefully yours ????,
Mayank Sodhi
'''
############################################################################################################

