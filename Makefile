.PHONY: run view-logs

run:
	poetry run python ghost_tail/main.py

logs:
	journalctl -xe --follow SYSLOG_IDENTIFIER="Ghost Tail" | sed 's/.*\]: //'
