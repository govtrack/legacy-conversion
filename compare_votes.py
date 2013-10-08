import lxml.etree, glob, re, os.path, sys

old_path, new_path = sys.argv[1:3]

def compare_dicts(a, b, comp_type, context):
	for k in a:
		if k == "updated": continue

		if k in ("present", "nv") and a[k] == "" and b[k] == "0": continue # this counts as OK

		if not k in b:
			print (context, "Missing %s:" % comp_type, k, a[k])
		elif b[k] != a[k]:
			print (context, "Changed %s: %s '%s'=>'%s'" % (comp_type, k, a[k], b[k]))
	for k in b:
		if k == "category": continue
		if not k in a:
			print (context, "Added %s:" % comp_type, k, b[k])

for congress in range(1, 102):

	seen = set()

	for fn1 in glob.glob(old_path + "/%d/rolls/*" % congress):
		m = re.match(".*/([hs])([0-9A-Z]|\d+)-(\d+)\.xml", fn1)
		if not m: raise ValueError(fn1)
		chamber, session, number = m.groups()
		seen.add( (chamber, session, number) )

		fn2 = new_path + "/%d/votes/%s/%s%s/data.xml" % (congress, session, chamber, number)
		if not os.path.exists(fn2):
			print ("Missing in new data:", congress, chamber, session, number)
			continue
		
		dom1 = lxml.etree.parse(open(fn1)).getroot()
		dom2 = lxml.etree.parse(open(fn2)).getroot()

		ctx = "%d-%s-%s-%s\t" % (congress, session, chamber, number)

		# compare top-level attributes
		compare_dicts(dict(dom1.items()), dict(dom2.items()), "attribute", ctx)

		# compare top-level elements
		compare_dicts({ n.tag: True for n in dom1 }, { n.tag: True for n in dom2 }, "node", ctx)

		# compare voters
		def make_voter_dict(dom):
			return { n.get("id"): n.get("vote") for n in dom.xpath("voter") }
		compare_dicts(make_voter_dict(dom1), make_voter_dict(dom2), "vote", ctx)

	# Check no spurrious new files.
	for fn2 in glob.glob(new_path + "/%d/votes/*/*" % congress):
		m = re.match(".*/([0-9A-Z]|\d+)/([hs])(\d+)$", fn2)
		if not m: raise ValueError(fn2)
		session, chamber, number = m.groups()
		if (chamber, session, number) not in seen:
			print("Extra file in new data:", fn2)
