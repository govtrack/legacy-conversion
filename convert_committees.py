#!/usr/bin/env python

import sys
from datetime import datetime
from lxml import etree

###

CONGRESS_PATH = sys.argv[1]
LEGISLATORS_PATH = sys.argv[2]
NEW_COMMITTEE_FILE = sys.argv[3]

###

# XXX: This is ridiculously fragile and totally frowned upon.
import imp
congress = imp.load_source( "congress", CONGRESS_PATH + "/tasks/utils.py" )
legislators = imp.load_source( "legislators", LEGISLATORS_PATH + "/scripts/utils.py" )

govtrack_person_id_map = {}

# XXX: Modified from congress.get_govtrack_person_id() to reap the benefits of having legislators in scope.
def get_govtrack_person_id( source_id_type, source_id ):
	# Load the legislators database to map various IDs to GovTrack IDs.
	# Cache in a pickled file because loading the whole YAML db is super slow.
	global govtrack_person_id_map

	# On the first call to this function...
	if not govtrack_person_id_map:
		govtrack_person_id_map = {}
		for fn in [ "legislators-historical", "legislators-current" ]:
			m = {}
			for moc in legislators.yaml_load( LEGISLATORS_PATH + "/" + fn + ".yaml" ):
				if "govtrack" in moc["id"]:
					for k, v in moc["id"].items():
						if k in [ "bioguide", "lis", "thomas" ]:
							m[( k, v )] = moc["id"]["govtrack"]

			# Combine the mappings from the historical and current files.
			govtrack_person_id_map.update( m )

	# Now do the lookup.
	if (source_id_type, source_id) not in govtrack_person_id_map:
		raise UnmatchedIdentifer()

	return str( govtrack_person_id_map[( source_id_type, source_id )] )

congress.get_govtrack_person_id = get_govtrack_person_id

print "Loading committee data..."

committees = legislators.yaml_load( LEGISLATORS_PATH + "/committees-current.yaml" )

print "Loading committee membership data..."

members = legislators.yaml_load( LEGISLATORS_PATH + "/committee-membership-current.yaml" )

#print committees

print "Generating XML..."

new_committees = etree.Element( "committees" )

new_committees.text = "\n\t"

for committee in committees:
	c = etree.Element( "committee" )

	c.set( "type", committee["type"] )
	c.set( "code", committee["thomas_id"] )
	c.set( "displayname", committee["name"] )

	for member in members[committee["thomas_id"]]:
		m = etree.Element( "member" )

		m.set( "id", congress.get_govtrack_person_id( "bioguide", member["bioguide"] ) )

		if "title" in member:
			m.set( "role", member["title"] )

		m.tail = "\n\t\t"

		c.append( m )

	if "subcommittees" in committee:
		c.text = "\n\t\t"

		for subcommittee in committee["subcommittees"]:
			sc = etree.Element( "subcommittee" )

			sc.set( "code", subcommittee["thomas_id"] )
			sc.set( "displayname", subcommittee["name"] + " Subcommittee" )

			sc.text = "\n\t\t\t"

			for member in members.get(committee["thomas_id"] + subcommittee["thomas_id"], []):
				sm = etree.Element( "member" )

				sm.set( "id", congress.get_govtrack_person_id( "bioguide", member["bioguide"] ) )

				if "title" in member:
					sm.set( "role", member["title"] )

				sm.tail = "\n\t\t\t"

				sc.append( sm )

			if len(sc) > 0: sc[-1].tail = "\n\t\t"

			sc.tail = "\n\t\t"

			c.append( sc )

		c[-1].tail = "\n\t"

	c.tail = "\n\t"

	new_committees.append( c )

new_committees[-1].tail = "\n"

print "Writing XML to file..."

etree.ElementTree( new_committees ).write( NEW_COMMITTEE_FILE, encoding="utf-8" )

print "Done."

