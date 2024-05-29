
MEASURE := ./bfall/bfall_measure.py
ANALYSIS := ./bfall/bfall_analysis.py
NETDEV := wlp1s0
WEBSITE_LIST := small_websites.txt
BROWSER_LIST := browser_cmds.txt
OUTPUT_DIR := ./data
OUTPUT_CSV := data.csv

default:
	@

$(OUTPUT_DIR): FORCE
	mkdir -p $@

measure: $(OUTPUT_DIR) FORCE
	$(MEASURE) $(NETDEV) $(WEBSITE_LIST) $(BROWSER_LIST) $(OUTPUT_CSV) $(OUTPUT_DIR) -v

analysis: FORCE
	$(ANALYSIS) $(OUTPUT_CSV) -v

default: measure

FORCE:

