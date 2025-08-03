# photochomper

PhotoChomper is a Python-based tool designed to help users manage and organize their photo collections by identifying and removing duplicate images. It features a terminal user interface (TUI) for setup and configuration, and it can be scheduled to run periodically to keep your photo library clean.

## Table of Contents
1. [Platform & Performance](#1-platform--performance)
2. [Duplicate Detection Features](#2-duplicate-detection-features)
3. [Duplicate Handling & Actions](#3-duplicate-handling--actions)   
   1. [Options for Duplicate Handling](#options-for-duplicate-handling)
   2. [Reporting and Exporting](#reporting-and-exporting)
   3. [Custom Reports and Alerts](#custom-reports-and-alerts)
   4. [Notifications](#notifications)
   5. [User Interface](#user-interface)
   6. [Configuration](#configuration)
   7. [Scheduling](#scheduling)
   8. [Setup](#setup)
   9. [Help](#help)
   10. [Contributing](#contributing)
   11. [License](#license)
   12. [Contact](#contact)
   13. [Changelog](#changelog)
   14. [Known Issues](#known-issues)
   15. [Future Plans](#future-plans)
   16. [Testing](#testing)
   17. [Debugging](#debugging)
   18. [Performance](#performance)
   19. [Security](#security)
   20. [Dependencies](#dependencies)
   21. [Installation](#installation)
   22. [Usage](#usage)
   23. [Development](#development)
   24. [Code of Conduct](#code-of-conduct)
   25. [FAQ](#faq)
   26. [Support](#support)
   27. [Resources](#resources)
   28. [Community](#community)
   29. [Feedback](#feedback)
   30. [Updates](#updates)
   31. [Release Notes](#release-notes)
   32. [Credits](#credits)
   33. [Attribution](#attribution)
   34. [Privacy Policy](#privacy-policy)
   35. [Terms of Service](#terms-of-service)
   36. [Disclaimer](#disclaimer)
   37. [Legal](#legal)
   38. [Accessibility](#accessibility)
4.  

    [Troubleshooting](#troubleshooting)
5. [Acknowledgements](#acknowledgements)
6. [Versioning](#versioning)

If the program ran without error but produced no output, it likely means you did not specify any command-line arguments (--setup, --search, or --schedule).
The program only performs actions if you provide these flags.

How to use:

To set up configuration interactively:
To run a duplicate search (after setup):
To schedule repeated searches:
(Runs every 1 hour)
If you want the program to show a message when no arguments are provided, add this to your main() function:

Now, running without arguments will show usage instructions.