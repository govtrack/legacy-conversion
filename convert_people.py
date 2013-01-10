#!/usr/bin/env python

# python convert_people.py congress-legislators-path legacy-people.xml new-people.xml [0|1]
# 0 to output all people, 1 to output just people serving in the 113th Congress.

import sys
import os.path
from datetime import datetime
from lxml import etree
import yaml

# XXX: Stolen from congress-legislators/scripts/utils.py
def yaml_load(path):
	# Loading YAML is ridiculously slow, so cache the YAML data
	# in a pickled file which loads much faster.

	# Check if the .pickle file exists and a hash stored inside it
	# matches the hash of the YAML file, and if so unpickle it.
	import cPickle as pickle, os.path, hashlib
	h = hashlib.sha1(open(path).read()).hexdigest()
	if os.path.exists(path + ".pickle"):
		store = pickle.load(open(path + ".pickle"))
		if store["hash"] == h:
			return store["data"]

	# No cached pickled data exists, so load the YAML file.
	data = yaml.load(open(path))

	# Store in a pickled file for fast access later.
	pickle.dump({ "hash": h, "data": data }, open(path+".pickle", "w"))

	return data

def get_party_abbreviation( party ):
	party_map = {
		"Conservative": "C",
		"Democrat": "D",
		"Democrat Farmer Labor": "DFL",
		"Democrat-turned-Republican": "XXX",
		"Democrat/Independent": "XXX",
		"Democrat/Republican": "XXX",
		"Democratic": "D",
		"Democratic Republican": "DR",
		"Democratic-Republican": "DR",
		"Farmer-Labor": "FL",
		"Federalist": "F",
		"Ind. Democrat": "ID",
		"Ind. Republican": "IR",
		"Ind. Republican-Democrat": "XXX",
		"Ind. Whig": "IW",
		"Independent": "I",
		"Independent Democrat": "ID",
		"Independent/Republican": "XXX",
		"Jackson": "J",
		"Republican": "R",
		"Unconditional Unionist": "UU",
		"Unionist": "U",
		"Whig": "W",
	}

	return party_map[party]

###

LEGISLATORS_PATH = sys.argv[1]
ORIGINAL_PEOPLE_FILE = sys.argv[2]
NEW_PEOPLE_FILE = sys.argv[3]
CURRENT_ONLY = (sys.argv[4] == "1")

###

now = datetime.now()

print "Determing original order of people..."

govtrack_order = []

old_people = etree.parse( ORIGINAL_PEOPLE_FILE )

for e in old_people.findall( "/person" ):
	govtrack_order.append( e.get( "id" ) )

persons = {}
new_person_order = []
id_map = { }

print "Loading historical legislators..."

for person in yaml_load( LEGISLATORS_PATH + "legislators-historical.yaml" ):
	govtrack_id = str( person["id"]["govtrack"] )
	persons[govtrack_id] = person
	persons[govtrack_id]["social"] = {}
	if govtrack_id not in govtrack_order: new_person_order.append(govtrack_id)

print "Loading current legislators..."

for person in yaml_load( LEGISLATORS_PATH + "legislators-current.yaml" ):
	govtrack_id = str( person["id"]["govtrack"] )
	persons[govtrack_id] = person
	persons[govtrack_id]["social"] = {}
	if govtrack_id not in govtrack_order: new_person_order.append(govtrack_id)
	for k, v in person["id"].items(): id_map[(k, str(v))] = govtrack_id # map other IDs e.g. ('thomas', '00123') tuples, to govtrack IDs; use str(v) because some values are lists which can't be put into a dict as a key

print "Loading legislator social media data..."

for person_social in yaml_load( LEGISLATORS_PATH + "legislators-social-media.yaml" ):
	# search for a govtrack ID
	govtrack_id = None
	for k, v in person_social["id"].items():
		if (k, v) in id_map: # kv is e.g. ('thomas', '00123') or even ('govtrack', '412345')
			govtrack_id = id_map[(k, str(v))]
	if govtrack_id not in persons:
		continue
		#persons[govtrack_id] = person_social
	else:
		persons[govtrack_id]["social"] = person_social["social"]

print "Loading executives..."

for person in yaml_load( LEGISLATORS_PATH + "executive.yaml" ):
	govtrack_id = str( person["id"]["govtrack"] )
	if govtrack_id not in persons:
		persons[govtrack_id] = person
		persons[govtrack_id]["social"] = {}
		if govtrack_id not in govtrack_order: new_person_order.append(govtrack_id)
	else:
		# Extend the terms, then re-sort to ensure the roles come out in chronological order.
		persons[govtrack_id]["terms"].extend( person["terms"] )
		persons[govtrack_id]["terms"].sort(key = lambda n : n["start"]) # sort by term start date

print "Generating XML..."

new_people = etree.Element( "people" )
if CURRENT_ONLY:
	new_people.set( "session", "113" ) # this is the last Congress we'll be using this script anyway

new_people.text = "\n\t"

for govtrack_id in govtrack_order + new_person_order:
	if govtrack_id not in persons:
		continue

	person = etree.Element( "person" )

	person.set( "id", str( persons[govtrack_id]["id"]["govtrack"] ) )
	person.set( "lastname", persons[govtrack_id]["name"]["last"] )
	person.set( "firstname", persons[govtrack_id]["name"]["first"] )

	if "middle" in persons[govtrack_id]["name"]:
		person.set( "middlename", persons[govtrack_id]["name"]["middle"] )

	if "suffix" in persons[govtrack_id]["name"]:
		person.set( "namemod", persons[govtrack_id]["name"]["suffix"] )

	if "nickname" in persons[govtrack_id]["name"]:
		person.set( "nickname", persons[govtrack_id]["name"]["nickname"] )

	if "bio" in persons[govtrack_id]:
		if "birthday" in persons[govtrack_id]["bio"]:
			person.set( "birthday", str( persons[govtrack_id]["bio"]["birthday"] ) )

		if "gender" in persons[govtrack_id]["bio"]:
			person.set( "gender", persons[govtrack_id]["bio"]["gender"] )

		if "religion" in persons[govtrack_id]["bio"]:
			person.set( "religion", persons[govtrack_id]["bio"]["religion"] )

	if "votesmart" in persons[govtrack_id]["id"]:
		person.set( "pvsid", str( persons[govtrack_id]["id"]["votesmart"] ) )

	if "opensecrets" in persons[govtrack_id]["id"]:
		person.set( "osid", str( persons[govtrack_id]["id"]["opensecrets"] ) )

	if "bioguide" in persons[govtrack_id]["id"]:
		person.set( "bioguideid", str( persons[govtrack_id]["id"]["bioguide"] ) )

	if "metavid" in persons[govtrack_id]["social"]:
		person.set( "metavidid", str( persons[govtrack_id]["social"]["metavid"] ) )

	if "youtube" in persons[govtrack_id]["social"]:
		person.set( "youtubeid", str( persons[govtrack_id]["social"]["youtube"] ) )

	if "twitter" in persons[govtrack_id]["social"]:
		person.set( "twitterid", str( persons[govtrack_id]["social"]["twitter"] ) )

	if "icpsr" in persons[govtrack_id]["id"]:
		person.set( "icpsrid", str( persons[govtrack_id]["id"]["icpsr"] ) )

	if "facebook_graph" in persons[govtrack_id]["social"]:
		person.set( "facebookgraphid", str( persons[govtrack_id]["social"]["facebook_graph"] ) )

	if "thomas" in persons[govtrack_id]["id"]:
		person.set( "thomasid", str( persons[govtrack_id]["id"]["thomas"] ) )

	if "lis" in persons[govtrack_id]["id"]:
		person.set( "lismemberid", str( persons[govtrack_id]["id"]["lis"] ) )

	if "official_full" not in persons[govtrack_id]["name"]:
		if "nickname" in persons[govtrack_id]["name"]:
			full_name = persons[govtrack_id]["name"]["nickname"]
		else:
			if persons[govtrack_id]["name"]["first"].endswith( "." ) and ( "middle" in persons[govtrack_id]["name"] ):
				full_name = persons[govtrack_id]["name"]["middle"]
			else:
				full_name = persons[govtrack_id]["name"]["first"]

#				if "middle" in persons[govtrack_id]["name"]:
#					full_name += " " + persons[govtrack_id]["name"]["middle"]

		full_name += " " + persons[govtrack_id]["name"]["last"]

#		if "suffix" in persons[govtrack_id]["name"]:
#			full_name += ", " + persons[govtrack_id]["name"]["suffix"]
	else:
		full_name = persons[govtrack_id]["name"]["official_full"]

	person.set( "name", full_name )

	person.text = "\n\t\t"
	
	is_current = False

	for term in persons[govtrack_id]["terms"]:
		role = etree.Element( "role" )

		role.set( "type", term["type"] )
		role.set( "startdate", str( term["start"] ) )
		role.set( "enddate", str( term["end"] ) )

		if "party" in term:
			role.set( "party", term["party"] )

		if "state" in term:
			role.set( "state", term["state"] )

		if "district" in term:
			role.set( "district", str( term["district"] ) )

		if "class" in term:
			role.set( "class", str( term["class"] ) )

		if "url" in term:
			role.set( "url", str( term["url"] ) )

		if "address" in term:
			role.set( "address", str( term["address"] ) )

#		if "office" in term:
#			role.set( "office", str( term["office"] ) )
#
#		if "phone" in term:
#			role.set( "phone", str( term["phone"] ) )
#
#		if "fax" in term:
#			role.set( "fax", str( term["fax"] ) )
#
#		if "contact_form" in term:
#			role.set( "contactform", str( term["contact_form"] ) )

		if ( datetime.strptime( str( term["end"] ), "%Y-%m-%d" ) > now ) and ( datetime.strptime( str( term["start"] ), "%Y-%m-%d" ) <= now ):
			
			role.set( "current", "1" )

			if term["type"] == "prez":
				name_prefix = "Pres."
				name_suffix = None
			elif term["type"] == "sen":
				name_prefix = "Sen."
				name_suffix = "[" + get_party_abbreviation( term["party"] ) + ", " + term["state"] + "]"
			else:
				if term["state"] == "PR":
					name_prefix = "Res.Comm."
				elif term["state"] in [ "DC", "GU", "VI", "AS", "MP" ]:
					name_prefix = "Del."
				else:
					name_prefix = "Rep."

				name_suffix = "[" + get_party_abbreviation( term["party"] ) + ", " + term["state"] + "-" + str( term["district"] ) + "]"

			if name_prefix is not None:
				full_name = name_prefix + " " + full_name

			if name_suffix is not None:
				full_name = full_name + " " + name_suffix

			person.set( "name", full_name )
			person.set( "title", name_prefix )

			if "state" in term:
				person.set( "state", term["state"] )

			if "district" in term:
				person.set( "district", str( term["district"] ) )

		role.tail = "\n\t\t"

		# For the Congress-specific XML, only output roles that intersect with the 113th Congress,
		# and only output people with such roles.
		if not CURRENT_ONLY or term["end"] >= "2013-01-04":
			is_current = True
			person.append( role )

	if not CURRENT_ONLY or is_current:
		person[-1].tail = "\n\t"
		person.tail = "\n\t"
		new_people.append( person )

new_people[-1].tail = "\n"

print "Writing XML to file..."

etree.ElementTree( new_people ).write( NEW_PEOPLE_FILE, encoding="utf-8" )

print "Done."


