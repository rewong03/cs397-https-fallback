
WEBSITE_LIST := simple_list.txt

run: stop
	./loss.sh $(WEBSITE_LIST)

stop: stop.c
	$(CC) $< -o $@

