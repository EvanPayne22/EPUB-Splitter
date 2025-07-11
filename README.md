# EPUB-Splitter
Python script to split large EPUB files (consisting of HTML files) into smaller segments.

## epub_splitter
### Description
Splits a large epub file into smaller segments using Beautiful Soup Package (for html parsing). To run the script you must eneter the name/location of the epub file that you want split. This will allow you to choose a set range that you want to split or can split the whole file into segments of desired size. This is beneficial for load times on lower performance devices.
### Tags
#### -splitsize
Sets the size of each partition.
#### -singlerange
Takes two inputs the number of the start chapter and the number of the end chapter which makes one partition from those chapters (use numbers relative to first chapter in epub).
#### -title 
Sets the name of the single range partition.
#### -outdir
Sets the save path for the generated file. Will generate new directories if needed.
