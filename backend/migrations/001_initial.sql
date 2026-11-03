-- AI Company OS: initial SQLite schema, version 1.
BEGIN;

CREATE TABLE campaigns (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	subject VARCHAR NOT NULL, 
	body TEXT NOT NULL, 
	status VARCHAR NOT NULL, 
	scheduled VARCHAR NOT NULL, 
	daily_limit INTEGER NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE contacts (
	id INTEGER NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	email VARCHAR(320) NOT NULL, 
	country VARCHAR NOT NULL, 
	industry VARCHAR NOT NULL, 
	consent BOOLEAN NOT NULL, 
	consent_evidence TEXT NOT NULL, 
	unsubscribed BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
)

;

CREATE TABLE deliveries (
	id INTEGER NOT NULL, 
	campaign_id INTEGER NOT NULL, 
	contact_id INTEGER NOT NULL, 
	status VARCHAR NOT NULL, 
	timestamp VARCHAR NOT NULL, 
	error VARCHAR NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE jobs (
	id INTEGER NOT NULL, 
	department VARCHAR NOT NULL, 
	objective TEXT NOT NULL, 
	status VARCHAR NOT NULL, 
	progress INTEGER NOT NULL, 
	result TEXT NOT NULL, 
	options TEXT NOT NULL, 
	created VARCHAR NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE records (
	id INTEGER NOT NULL, 
	kind VARCHAR(40) NOT NULL, 
	payload TEXT NOT NULL, 
	created VARCHAR NOT NULL, 
	PRIMARY KEY (id)
)

;
CREATE INDEX ix_records_kind ON records (kind);

CREATE TABLE schema_migrations (
	version INTEGER NOT NULL, 
	PRIMARY KEY (version)
)

;
INSERT INTO schema_migrations (version) VALUES (1);
COMMIT;
