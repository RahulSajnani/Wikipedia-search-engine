import re, os, linecache, gc
import heapq
import math


categories = sorted(["references", "body", "infobox", "title", "category", "links"])
merge_characters_length = 1 #3
alphabet_file_mapping = {}

for i in range(97, 123):
    alphabet_file_mapping[chr(i)] = int((i - 97) / merge_characters_length) + 1

for i in range(10):
    alphabet_file_mapping[str(i)] = 0

max_division = 0
for key in alphabet_file_mapping:
    if alphabet_file_mapping[key] > max_division:
        max_division = alphabet_file_mapping[key]
max_division += 1

if __name__== "__main__":
    
    print(max_division)