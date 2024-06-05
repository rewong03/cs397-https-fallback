
MEASURE := ./bfall/bfall_measure.py
ANALYSIS := ./bfall/bfall_analysis.py
GRAPH := ./bfall/bfall_graph.py
NETDEV := wlp1s0
WEBSITE_LIST := small_websites.txt
BROWSER_LIST := browser_cmds.txt
OUTPUT_DIR := ./data
OUTPUT_CSV := data.csv
ANALYSIS_CSV := analysis.csv

default:
	@

$(OUTPUT_DIR): FORCE
	mkdir -p $@

measure: $(OUTPUT_DIR) FORCE
	$(MEASURE) $(NETDEV) $(WEBSITE_LIST) $(BROWSER_LIST) $(OUTPUT_CSV) $(OUTPUT_DIR) -v

analysis: FORCE
	$(ANALYSIS) $(OUTPUT_CSV) $(ANALYSIS_CSV) -v

graph: FORCE
	$(GRAPH) $(OUTPUT_CSV) $(ANALYSIS_CSV) TIMES -v

default: measure

FORCE:

