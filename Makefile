
BFALL := ./bfall.py
NETDEV := wlp1s0
WEBSITE_LIST := small_websites.txt
BROWSER_LIST := browser_cmds.txt
OUTPUT_CSV := data.csv

basic_test:
	$(BFALL) $(NETDEV) $(WEBSITE_LIST) $(BROWSER_LIST) $(OUTPUT_CSV)

