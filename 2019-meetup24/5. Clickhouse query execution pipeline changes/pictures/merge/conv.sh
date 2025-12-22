for filename in `find . -regex ".*.svg"`; 
do
  inkscape $filename --export-png=$filename.png ; 
done