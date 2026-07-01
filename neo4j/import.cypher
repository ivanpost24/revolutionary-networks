// =============================================================================
// Neo4j Import Script: Rotunda Revolutionary Correspondence, 1771–1783
// =============================================================================
// INSTRUCTIONS:
// 1. Set the CSV_URL variable below to the raw URL of your CSV file.
//    If using GitHub: https://raw.githubusercontent.com/<user>/<repo>/main/data/Rotunda_1771-1783_enriched.csv
// 2. Run each section in order in the Neo4j Browser or via cypher-shell.
// 3. Sections are separated by comments. Run them one at a time (especially
//    the LOAD CSV blocks) so you can monitor progress.
// =============================================================================

// ---------------------------------------------------------------------------
// 0. SET YOUR CSV URL
//    Replace this with your actual raw CSV URL.
//    Neo4j Aura requires an HTTP(S) URL — file:/// will not work.
// ---------------------------------------------------------------------------
:param csvUrl => 'https://raw.githubusercontent.com/rotunda-uvap/revolutionary-networks/refs/heads/main/rotunda_data_1771-1783_full.csv'

// People lookup (gender + biographical labels), one row per personId.
:param peopleUrl => 'https://raw.githubusercontent.com/rotunda-uvap/revolutionary-networks/refs/heads/main/neo4j/people_lookup.csv'


// ---------------------------------------------------------------------------
// 1. CONSTRAINTS (uniqueness + existence, also creates indexes)
// ---------------------------------------------------------------------------

CREATE CONSTRAINT person_id IF NOT EXISTS
FOR (p:Person) REQUIRE p.personId IS UNIQUE;

CREATE CONSTRAINT document_id IF NOT EXISTS
FOR (d:Document) REQUIRE d.documentId IS UNIQUE;

CREATE CONSTRAINT publication_code IF NOT EXISTS
FOR (pub:Publication) REQUIRE pub.code IS UNIQUE;

CREATE CONSTRAINT place_geonameid IF NOT EXISTS
FOR (pl:Place) REQUIRE pl.geonameId IS UNIQUE;

CREATE CONSTRAINT country_name IF NOT EXISTS
FOR (c:Country) REQUIRE c.name IS UNIQUE;

// Admin1 names are unique within the dataset (confirmed: no admin1 spans multiple countries)
CREATE CONSTRAINT admin1_name IF NOT EXISTS
FOR (a:Admin1) REQUIRE a.name IS UNIQUE;

// Admin2 names are NOT unique (e.g. "Richmond County" in VA and NY).
// We use a composite key: "admin2Name|admin1Name"
CREATE CONSTRAINT admin2_key IF NOT EXISTS
FOR (a:Admin2) REQUIRE a.key IS UNIQUE;

CREATE CONSTRAINT year_value IF NOT EXISTS
FOR (y:Year) REQUIRE y.year IS UNIQUE;

CREATE CONSTRAINT month_key IF NOT EXISTS
FOR (m:Month) REQUIRE m.key IS UNIQUE;


// ---------------------------------------------------------------------------
// 2. ADDITIONAL INDEXES for query performance
// ---------------------------------------------------------------------------

CREATE INDEX document_date IF NOT EXISTS
FOR (d:Document) ON (d.date);

CREATE INDEX document_year IF NOT EXISTS
FOR (d:Document) ON (d.year);

CREATE INDEX person_name IF NOT EXISTS
FOR (p:Person) ON (p.name);

CREATE INDEX place_name IF NOT EXISTS
FOR (pl:Place) ON (pl.name);

// Supports filtering people (and their documents) by gender.
CREATE INDEX person_gender IF NOT EXISTS
FOR (p:Person) ON (p.gender);


// ---------------------------------------------------------------------------
// 3. CREATE YEAR AND MONTH NODES (small fixed set, no CSV needed)
// ---------------------------------------------------------------------------

UNWIND range(1771, 1783) AS y
MERGE (yr:Year {year: y});

UNWIND range(1771, 1783) AS y
UNWIND range(1, 12) AS m
WITH y, m, y + '-' + CASE WHEN m < 10 THEN '0' + toString(m) ELSE toString(m) END AS key,
     CASE m
       WHEN 1 THEN 'January' WHEN 2 THEN 'February' WHEN 3 THEN 'March'
       WHEN 4 THEN 'April'   WHEN 5 THEN 'May'       WHEN 6 THEN 'June'
       WHEN 7 THEN 'July'    WHEN 8 THEN 'August'     WHEN 9 THEN 'September'
       WHEN 10 THEN 'October' WHEN 11 THEN 'November' WHEN 12 THEN 'December'
     END AS monthName
MERGE (mo:Month {key: key})
  ON CREATE SET mo.month = m, mo.year = y, mo.name = monthName + ' ' + toString(y)
WITH mo, y
MATCH (yr:Year {year: y})
MERGE (mo)-[:IN_YEAR]->(yr);


// ---------------------------------------------------------------------------
// 4. CREATE PUBLICATION NODES
// ---------------------------------------------------------------------------

LOAD CSV WITH HEADERS FROM $csvUrl AS row
WITH DISTINCT row.Publication AS code
WHERE code IS NOT NULL AND code <> ''
MERGE (:Publication {code: code});


// ---------------------------------------------------------------------------
// 5. CREATE COUNTRY NODES
// ---------------------------------------------------------------------------

LOAD CSV WITH HEADERS FROM $csvUrl AS row
WITH DISTINCT row.country_name AS name, row.country_code AS code
WHERE name IS NOT NULL AND name <> ''
MERGE (c:Country {name: name})
  ON CREATE SET c.countryCode = code;


// ---------------------------------------------------------------------------
// 6. CREATE ADMIN1 NODES + link to Country
// ---------------------------------------------------------------------------

LOAD CSV WITH HEADERS FROM $csvUrl AS row
WITH DISTINCT row.admin1 AS a1Name, row.country_name AS countryName
WHERE a1Name IS NOT NULL AND a1Name <> ''
  AND countryName IS NOT NULL AND countryName <> ''
MERGE (a1:Admin1 {name: a1Name})
WITH a1, countryName
MATCH (c:Country {name: countryName})
MERGE (a1)-[:IN_COUNTRY]->(c);


// ---------------------------------------------------------------------------
// 7. CREATE ADMIN2 NODES + link to Admin1
//    Uses composite key "admin2|admin1" to handle duplicate county names
// ---------------------------------------------------------------------------

LOAD CSV WITH HEADERS FROM $csvUrl AS row
WITH DISTINCT row.admin2 AS a2Name, row.admin1 AS a1Name
WHERE a2Name IS NOT NULL AND a2Name <> ''
  AND a1Name IS NOT NULL AND a1Name <> ''
WITH a2Name, a1Name, a2Name + '|' + a1Name AS compositeKey
MERGE (a2:Admin2 {key: compositeKey})
  ON CREATE SET a2.name = a2Name
WITH a2, a1Name
MATCH (a1:Admin1 {name: a1Name})
MERGE (a2)-[:IN_ADMIN1]->(a1);


// ---------------------------------------------------------------------------
// 8. CREATE PLACE NODES + link to geographic hierarchy
// ---------------------------------------------------------------------------

LOAD CSV WITH HEADERS FROM $csvUrl AS row
WITH DISTINCT row.geonameId AS gid,
     row.Location AS loc,
     row.revised_location AS revisedLoc,
     toFloat(row.latitude) AS lat,
     toFloat(row.longitude) AS lon,
     row.admin2 AS a2Name,
     row.admin1 AS a1Name,
     row.country_name AS countryName
WHERE gid IS NOT NULL AND gid <> ''
MERGE (pl:Place {geonameId: gid})
  ON CREATE SET
    pl.name = CASE WHEN revisedLoc IS NOT NULL AND revisedLoc <> '' THEN revisedLoc ELSE loc END,
    pl.latitude = lat,
    pl.longitude = lon,
    pl.point = point({latitude: lat, longitude: lon})
WITH pl, a2Name, a1Name, countryName
// Link to Admin2 if available
CALL (pl, a2Name, a1Name) {
  WITH pl, a2Name, a1Name
  WHERE a2Name IS NOT NULL AND a2Name <> ''
    AND a1Name IS NOT NULL AND a1Name <> ''
  MATCH (a2:Admin2 {key: a2Name + '|' + a1Name})
  MERGE (pl)-[:IN_ADMIN2]->(a2)
}
// Link directly to Admin1 if no Admin2
CALL (pl, a2Name, a1Name) {
  WITH pl, a2Name, a1Name
  WHERE (a2Name IS NULL OR a2Name = '')
    AND a1Name IS NOT NULL AND a1Name <> ''
  MATCH (a1:Admin1 {name: a1Name})
  MERGE (pl)-[:IN_ADMIN1]->(a1)
}
// Link directly to Country if no Admin1 and no Admin2
CALL (pl, a2Name, a1Name, countryName) {
  WITH pl, a2Name, a1Name, countryName
  WHERE (a1Name IS NULL OR a1Name = '')
    AND (a2Name IS NULL OR a2Name = '')
    AND countryName IS NOT NULL AND countryName <> ''
  MATCH (c:Country {name: countryName})
  MERGE (pl)-[:IN_COUNTRY]->(c)
};


// ---------------------------------------------------------------------------
// 9a. CREATE DOCUMENT NODES (batched, 500 rows per transaction)
// ---------------------------------------------------------------------------

:auto LOAD CSV WITH HEADERS FROM $csvUrl AS row
WITH row
WHERE row.DocumentID IS NOT NULL AND row.DocumentID <> ''
CALL {
  WITH row
  MERGE (d:Document {documentId: row.DocumentID})
    ON CREATE SET
      d.title = row.Title,
      d.date = CASE WHEN row.Date IS NOT NULL AND row.Date <> '' THEN date(row.Date) ELSE null END,
      d.year = CASE WHEN row.Date IS NOT NULL AND row.Date <> '' THEN toInteger(substring(row.Date, 0, 4)) ELSE null END,
      d.authorName = row.Author,
      d.recipientName = row.Recipient,
      d.origDateline = row.OrigDateline,
      d.foundersOnlineUrl = row.`Founders Online`,
      d.rotundaUrl = row.Rotunda
} IN TRANSACTIONS OF 500 ROWS;


// ---------------------------------------------------------------------------
// 9b. LINK DOCUMENTS TO PUBLICATIONS (batched)
// ---------------------------------------------------------------------------

:auto LOAD CSV WITH HEADERS FROM $csvUrl AS row
WITH row
WHERE row.DocumentID IS NOT NULL AND row.DocumentID <> ''
  AND row.Publication IS NOT NULL AND row.Publication <> ''
CALL {
  WITH row
  MATCH (d:Document {documentId: row.DocumentID})
  MATCH (pub:Publication {code: row.Publication})
  MERGE (d)-[:PUBLISHED_IN]->(pub)
} IN TRANSACTIONS OF 500 ROWS;


// ---------------------------------------------------------------------------
// 9c. LINK DOCUMENTS TO PLACES (batched)
// ---------------------------------------------------------------------------

:auto LOAD CSV WITH HEADERS FROM $csvUrl AS row
WITH row
WHERE row.DocumentID IS NOT NULL AND row.DocumentID <> ''
  AND row.geonameId IS NOT NULL AND row.geonameId <> ''
CALL {
  WITH row
  MATCH (d:Document {documentId: row.DocumentID})
  MATCH (pl:Place {geonameId: row.geonameId})
  MERGE (d)-[:SENT_FROM]->(pl)
} IN TRANSACTIONS OF 500 ROWS;


// ---------------------------------------------------------------------------
// 9d. LINK DOCUMENTS TO MONTHS (batched)
// ---------------------------------------------------------------------------

:auto LOAD CSV WITH HEADERS FROM $csvUrl AS row
WITH row
WHERE row.DocumentID IS NOT NULL AND row.DocumentID <> ''
  AND row.Date IS NOT NULL AND row.Date <> ''
WITH row, substring(row.Date, 0, 7) AS monthKey
CALL {
  WITH row, monthKey
  MATCH (d:Document {documentId: row.DocumentID})
  MATCH (mo:Month {key: monthKey})
  MERGE (d)-[:IN_MONTH]->(mo)
} IN TRANSACTIONS OF 500 ROWS;


// ---------------------------------------------------------------------------
// 10. CREATE PERSON NODES from authors (batched)
//     Splits semicolon-delimited authorIDs and Author fields positionally
// ---------------------------------------------------------------------------

:auto LOAD CSV WITH HEADERS FROM $csvUrl AS row
WITH row
WHERE row.authorIDs IS NOT NULL AND row.authorIDs <> ''
WITH row, split(row.authorIDs, ';') AS ids, split(row.Author, ';') AS names
UNWIND range(0, size(ids) - 1) AS i
WITH trim(ids[i]) AS pid, trim(names[i]) AS pname
WHERE pid IS NOT NULL AND pid <> ''
CALL {
  WITH pid, pname
  MERGE (p:Person {personId: pid})
    ON CREATE SET
      p.name = pname,
      p.uri = 'https://rotunda.upress.virginia.edu/person/' + pid
} IN TRANSACTIONS OF 500 ROWS;


// ---------------------------------------------------------------------------
// 11. CREATE PERSON NODES from recipients (batched)
// ---------------------------------------------------------------------------

:auto LOAD CSV WITH HEADERS FROM $csvUrl AS row
WITH row
WHERE row.recipientIDs IS NOT NULL AND row.recipientIDs <> ''
WITH row, split(row.recipientIDs, ';') AS ids, split(row.Recipient, ';') AS names
UNWIND range(0, size(ids) - 1) AS i
WITH trim(ids[i]) AS pid, trim(names[i]) AS pname
WHERE pid IS NOT NULL AND pid <> ''
CALL {
  WITH pid, pname
  MERGE (p:Person {personId: pid})
    ON CREATE SET
      p.name = pname,
      p.uri = 'https://rotunda.upress.virginia.edu/person/' + pid
} IN TRANSACTIONS OF 500 ROWS;


// ---------------------------------------------------------------------------
// 11b. ENRICH PERSON NODES WITH GENDER (from people_lookup.csv)
//      Runs after Persons exist (sections 10-11). MATCH-only: enriches people
//      who actually appear in the correspondence; never creates new nodes.
//      Blank gender -> NULL so it doesn't masquerade as a value when filtering.
// ---------------------------------------------------------------------------

LOAD CSV WITH HEADERS FROM $peopleUrl AS row
WITH row WHERE row.personID IS NOT NULL AND row.personID <> ''
MATCH (p:Person {personId: row.personID})
SET p.gender = CASE
                 WHEN row.gender IS NULL OR trim(row.gender) = '' THEN NULL
                 ELSE trim(row.gender)
               END;


// ---------------------------------------------------------------------------
// 12. CREATE AUTHORED RELATIONSHIPS (batched)
// ---------------------------------------------------------------------------

:auto LOAD CSV WITH HEADERS FROM $csvUrl AS row
WITH row
WHERE row.authorIDs IS NOT NULL AND row.authorIDs <> ''
WITH row, split(row.authorIDs, ';') AS ids
UNWIND ids AS rawId
WITH trim(rawId) AS pid, row
WHERE pid IS NOT NULL AND pid <> ''
CALL {
  WITH pid, row
  MATCH (p:Person {personId: pid})
  MATCH (d:Document {documentId: row.DocumentID})
  MERGE (p)-[:AUTHORED]->(d)
} IN TRANSACTIONS OF 500 ROWS;


// ---------------------------------------------------------------------------
// 13. CREATE RECEIVED RELATIONSHIPS (batched)
// ---------------------------------------------------------------------------

:auto LOAD CSV WITH HEADERS FROM $csvUrl AS row
WITH row
WHERE row.recipientIDs IS NOT NULL AND row.recipientIDs <> ''
WITH row, split(row.recipientIDs, ';') AS ids
UNWIND ids AS rawId
WITH trim(rawId) AS pid, row
WHERE pid IS NOT NULL AND pid <> ''
CALL {
  WITH pid, row
  MATCH (p:Person {personId: pid})
  MATCH (d:Document {documentId: row.DocumentID})
  MERGE (p)-[:RECEIVED]->(d)
} IN TRANSACTIONS OF 500 ROWS;


// =============================================================================
// DONE. Verify with:
// =============================================================================
// MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC;
// MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS count ORDER BY count DESC;
