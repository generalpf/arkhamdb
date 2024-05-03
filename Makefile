db:
	rm -f arkhamdb.sqlite3
	sqlite3 arkhamdb.sqlite3 < scripts/0_ddl.sql
	sqlite3 arkhamdb.sqlite3 < scripts/1_base.sql
	sqlite3 arkhamdb.sqlite3 < scripts/2_dunwich-horror.sql
	sqlite3 arkhamdb.sqlite3 < scripts/3_black-goat-of-the-woods.sql
	sqlite3 arkhamdb.sqlite3 < scripts/4_innsmouth-horror.sql
	sqlite3 arkhamdb.sqlite3 < scripts/5_lurker-at-the-threshold.sql
	sqlite3 arkhamdb.sqlite3 < scripts/6_kingsport-horror.sql
	sqlite3 arkhamdb.sqlite3 < scripts/7_curse-of-the-dark-pharaoh.sql
	sqlite3 arkhamdb.sqlite3 < scripts/8_king-in-yellow.sql
	sqlite3 arkhamdb.sqlite3 < scripts/9_miskatonic-horror.sql
	sqlite3 arkhamdb.sqlite3 < scripts/10_migrate-to-sessions.sql
	sqlite3 arkhamdb.sqlite3 < scripts/11_expansions.sql
