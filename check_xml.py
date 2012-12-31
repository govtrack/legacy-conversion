import os.path
from lxml import etree
from simplediff import diff

# Converts an XML file into a recursive 5-tuple.
def get_children( element ):
	if list(element) == []:
		return []
	else:
		nodes = []

		for child in element.iterchildren():
			nodes.append( ( child.tag, child.attrib, child.text, get_children( child ), child.tail ) )

		if element.getparent() is None:
			return ( element.tag, element.attrib, element.text, nodes, element.tail )
		else:
			return nodes

# Rebuilds an XML file from a recursive 5-tuple.
def build_tree( nodes ):
	root = etree.Element( nodes[0] )

	attribute_names = sorted( nodes[1].keys() )

	for attribute_name in attribute_names:
		root.set( attribute_name, nodes[1][attribute_name] )

	if nodes[2] is not None and nodes[2].strip() != "":
		root.text = nodes[2].strip()
	elif ( root.getparent() is None or nodes[2] is None ) and nodes[3] != []:
		root.text = "\n"

	for element in nodes[3]:
		subtree = build_tree( element )

		subtree.tail = "\n"

		root.append( subtree )

	return root

# Determines whether the result of a diff() call actually contains a difference.
def is_different( diff_list ):
	return ( ( len( diff_list ) > 1 ) or ( ( diff_list != [] ) and ( diff_list[0][0] != "=" ) ) )

CONGRESS = 112
HOUSE_RESERVED = range( 1, 21 )
SENATE_RESERVED = range( 1, 21 )

OLD_PATH = "./%(congress)d/bills/%(old_code)s%(bill)d.xml"
NEW_PATH = "../data/%(congress)d/bills/%(new_code)s/%(new_code)s%(bill)d/data.xml"

old_scraper = {}
new_scraper = {}

for old, new in [ ( "h", "hr" ), ( "hr", "hres" ), ( "hj", "hjres" ), ( "hc", "hconres" ), ( "s", "s" ), ( "sr", "sres" ), ( "sj", "sjres" ), ( "sc", "sconres" ) ]:
	old_scraper[new] = {}
	new_scraper[new] = {}
	bill = 1

	while True:
		path_params = { "congress": CONGRESS, "old_code": old, "new_code": new, "bill": bill }

		old_scraper[new][bill] = {}
		new_scraper[new][bill] = {}

		if not ( os.path.exists( OLD_PATH % path_params ) and os.path.exists( NEW_PATH % path_params ) ):
			if ( ( new == "hr" ) and ( bill in HOUSE_RESERVED ) ) or ( ( new == "sr" ) and ( bill in SENATE_RESERVED ) ):
				print "Skipping reserved bill (%s%d)" % ( new, bill )

				bill += 1

				continue
			else:
				break

		print "Checking %s%d..." % ( new, bill )

		old_scraper[new][bill]["parsed_tree"] = etree.parse( OLD_PATH % path_params )
		new_scraper[new][bill]["parsed_tree"] = etree.parse( NEW_PATH % path_params )

		# Check that the state of the bill has not changed.
		if old_scraper[new][bill]["parsed_tree"].find( "state" ).text != new_scraper[new][bill]["parsed_tree"].find( "state" ).text:
			print old_scraper[new][bill]["parsed_tree"].find( "state" ).text + " => " + new_scraper[new][bill]["parsed_tree"].find( "state" ).text

		for old_element in old_scraper[new][bill]["parsed_tree"].iter():
			old_path = old_scraper[new][bill]["parsed_tree"].getpath( old_element )

			new_element = new_scraper[new][bill]["parsed_tree"].xpath( old_path )

			# Check for a one-to-one path relationship.
			if len( new_element ) != 1:
				# If the list is empty, the element is missing.
				# Otherwise, the path matches more than one element, which means elements have been added.
				if len( new_element ) == 0:
					print "* Element missing:", old_path
				else:
					print old_path, old_element, new_element
			else:
				old_element_keys = sorted( old_element.keys() )
				new_element_keys = sorted( new_element[0].keys() )

				key_diff = diff( old_element_keys, new_element_keys )

				# Check for attribute changes.
				for state, attributes in key_diff:
					if state != '=':
						print "* Element has difference in attributes:", old_path

					# Check for missing or added attributes.
					if state == "-":
						for attribute in attributes:
							print "** Attribute missing:", attribute + '="' + old_element.attrib[attribute] + '"'
					elif state == "+":
						for attribute in attributes:
							print "** Attribute added:", attribute + '="' + new_element[0].attrib[attribute] + '"'
					else:
						# Check for attribute value changes.
						for attribute in attributes:
							attribute_diff = diff( old_element.attrib[attribute], new_element[0].attrib[attribute] )

							if is_different( attribute_diff ):
								# XXX: Note this currently ignores attributes that contain timestamp data.
								if attribute not in [ "updated", "datetime" ]:# or parameter:
									print "* Attribute has difference in values:", old_path + "@" + attribute
									print "** Old:", '"' + old_element.attrib[attribute] + '"'
									print "** New:", '"' + new_element[0].attrib[attribute] + '"'
									print "** Diff:", attribute_diff

				if ( old_element.text is not None ) and ( new_element[0].text is not None ):
					old_element_text = old_element.text.strip()
					new_element_text = new_element[0].text.strip()

					# XXX: simplediff takes forever on long spans of text; splitting on newline speeds things up, but sacrifices granularity.
					if old_element.tag == "summary":
						text_diff = diff( old_element_text.split( "\n" ), new_element_text.split( "\n" ) )
					else:
						text_diff = diff( old_element_text, new_element_text )

					if is_different( text_diff ):
						print "* Element text differs:", old_path

						# XXX: Don't output text contents of really long elements.
						if old_element.tag in [ "text", "summary" ]:
							print "** (Text contents omitted for brevity.)"
						else:
							print "** Old:", '"' + old_element_text + '"'
							print "** New:", '"' + new_element_text + '"'
							print "** Diff:", text_diff

		print "Done checking %s%d.\n" % ( new, bill )

		bill += 1

## XXX: This code will create re-generated XML files that are easier to diff.
#old_file = etree.parse( "./112/bills/h1000.xml" )
#new_file = etree.parse( "../data/112/bills/hr/hr1000/data.xml" )
#
#old_children = get_children( old_file.getroot() )
#new_children = get_children( new_file.getroot() )
#
#print old_children, new_children
#
#for pair in diff( etree.tostring( build_tree( old_children ) ).split( "\n" ), etree.tostring( build_tree( new_children ) ).split( "\n" ) ):
#	if pair[0] != "=":
#		print "["
#		for line in pair[1]:
#			print pair[0] + " " + line
#		print "]"
#
##etree.ElementTree( build_tree( old_children ) ).write( "./112/diffs/h1000_old.xml" )
##etree.ElementTree( build_tree( new_children ) ).write( "./112/diffs/h1000_new.xml" )
