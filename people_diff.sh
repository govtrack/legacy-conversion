cat people$1.xml | sed -e "s/ >/>/g" | sed -e "s/ \\/>/\\/>/g" | sed -e "s/ /\n/g" | sed -e "s/'/\"/g" | egrep -v "metavidid|birthday" > p1.txt
cat people_new$1.xml | sed -e "s/ /\n/g" | grep -v birthday > p2.txt
diff -u p1.txt p2.txt | less
