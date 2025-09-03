* Add better status outputs on the --search TUI that shows progress thrugh various phases and stages of the searching process and presents elapsed time for each step.
* Attempt to estimate the time needed to complete the search, and update as more information come back to help refine the estimate
* Find a way to multi-thread the search if it is not already
* Set chunking with a configurable factor, Presented through recommendations in the --setup TUI, based on available memory
* Allow user to skip the SHA256 identical matching step