import xml.etree.ElementTree as etree
import sys
import helper_functions
import re
import Stemmer
import os
import linecache
import heapq
import readline
from datetime import datetime
from operator import itemgetter

'''
Author: Rahul Sajnani
'''
        
class Engine:
    '''
    Search engine class
    
    '''

    def __init__(self, index_path):
        super().__init__()

        self.index_path = index_path
        self.categories = sorted(["references", "body", "infobox", "title", "category", "links"])
        self.query_categories = {"c:": "category", "b:": "body", "t:": "title", "i:": "infobox", "r:": "references", "e:": "links"}
        self.tokens_dict = self.get_tokens()
        self.stemmer = Stemmer.Stemmer("english")
        
    def get_tokens(self):
        '''
        Reads the tokens file with line numbers
        '''
        tokens_dict = {}
        with open(os.path.join(self.index_path, "tokens.txt"), "r") as fp:
            for line in fp:
                words = line.split()
                if tokens_dict.get(words[0]) is None:
                    tokens_dict[words[0]] = []
                for i in range(1, len(words)):
                    tokens_dict[words[0]].append(words[i])

        return tokens_dict

    def decode_line(self, line):
        '''
        Decode line from the file containing posting's list
        '''
        
        line_dict = {}
        line = line.split()
        
        # line_dict["size"] = int(line[0])
        line_dict["postings_list"] = []
        
        for i in range(0, len(line), 2):
            line_dict["postings_list"].append((int(line[i]), float(line[i + 1])))
        
        line_dict["size"] = len(line_dict["postings_list"])

        return line_dict


    def get_postings_list(self, query_dict):
        '''
        Get the index files
        '''
        
        postings_list = {}
        for category in query_dict:
            filename = "index_%s.txt" % str(category)
            filename = os.path.join(self.index_path, filename)
            
            for token in query_dict[category]:
                # print(token)
                found = False
                # If token in dictionary
                if (self.tokens_dict.get(token) is not None):
                    # If token is present in the respective category
                    if self.tokens_dict[token][self.categories.index(category)] != "0": 
                        # Get line :)
                        postings_list_dict = self.decode_line(linecache.getline(filename, int(self.tokens_dict[token][self.categories.index(category)])))
                        found = True
                        if postings_list.get(category) is None:
                            postings_list[category] = {}
                        postings_list[category][token] = postings_list_dict
                        # print(line, category)
                if not found:
                    if postings_list.get(category) is None:
                            postings_list[category] = {}
                    postings_list[category][token] = {"size": 0, "postings_list": []}
        

        # print(postings_list)
        return postings_list

    def merge_postings_list(self, postings_list_1, postings_list_2):
        '''
        Merge two posting's list 
        '''

        ptr_1 = 0
        ptr_2 = 0

        doc_id_list = []

        while ((ptr_1 < len(postings_list_1)) and (ptr_2 < len(postings_list_2))):
            

            if postings_list_1[ptr_1][0] > postings_list_2[ptr_2][0]:
                ptr_2 += 1

            elif postings_list_1[ptr_1][0] < postings_list_2[ptr_2][0]:
                ptr_1 += 1

            else:
                # Doc ids are same 
                avg_doc_count = (postings_list_1[ptr_1][1] + postings_list_2[ptr_2][1])
                doc_id_list.append((postings_list_1[ptr_1][0], avg_doc_count))

                ptr_1 += 1
                ptr_2 += 1

        return doc_id_list

    def merge_postings_list_dict(self, posting_list_dict):
        '''
        Merges dictionary of postings list for a query
        '''

        # Doc ids of intersection of postings list
        search_doc_id = []
        postings_dict_size_heap = []
        # print(posting_list_dict)
        for category in posting_list_dict:
            for token in posting_list_dict[category]:
                postings_dict_size_heap.append((posting_list_dict[category][token]["size"], category, token))
        
        # print(postings_dict_size_heap)
        # If only one token
        if len(postings_dict_size_heap) == 1:

            return posting_list_dict[category][token]["postings_list"]


        heapq.heapify(postings_dict_size_heap)
        first_merge = True

        while postings_dict_size_heap:
            
            if len(postings_dict_size_heap) > 1 and first_merge:
                posting_tuple_1 = heapq.heappop(postings_dict_size_heap)
                posting_tuple_2 = heapq.heappop(postings_dict_size_heap)
                search_doc_id = self.merge_postings_list(posting_list_dict[posting_tuple_1[1]][posting_tuple_1[2]]["postings_list"], posting_list_dict[posting_tuple_2[1]][posting_tuple_2[2]]["postings_list"])
                first_merge = False
            else:
                posting_tuple_1 = heapq.heappop(postings_dict_size_heap)
                search_doc_id = self.merge_postings_list(search_doc_id, posting_list_dict[posting_tuple_1[1]][posting_tuple_1[2]]["postings_list"])
        
        return search_doc_id

    def search(self, query):
        '''
        Perform a search
        '''

        start_time = datetime.now()
        query_dict = {}
        query = query.lower()
        # query_split = query.split()
        
        query_separate = query.split(",")
        
        k = -1
        if len(query_separate) == 2:
            k = int(query_separate[0])
            query = query_separate[1]
        else:
            query = query_separate[0]

        query_split = query.split(":")
        
        if len(query_split) == 1:
            # not a field query
            # Search in page body as it contains all the content
            category = "b:"
            for token in query_split[0].split():

                if query_dict.get(self.query_categories[category]) is None:
                    query_dict[self.query_categories[category]] = []    
                query_dict[self.query_categories[category]].append(self.stemmer.stemWord(token)) 
    
        else:
            # Field queries !!!!

            words = query.split()
            category_loop = "b:"
            first_token = True
            for token in words:
                for category in self.query_categories:        
                    if token is not None:    
                        if token.startswith(category):
                            category_loop = category
                            if query_dict.get(self.query_categories[category_loop]) is None:
                                query_dict[self.query_categories[category_loop]] = []    
                            if len(token) > 2:
                                token = token[2:]
                            else:
                                token = None
                                # first_token = True
                                # query_dict[self.query_categories[category_loop]].append(self.stemmer.stemWord(token[2:]))
                if token is not None:
                    if query_dict.get(self.query_categories[category_loop]) is None:
                        query_dict[self.query_categories[category_loop]] = []
                    query_dict[self.query_categories[category_loop]].append(self.stemmer.stemWord(token))

        # print(query_dict)

        postings_list_dict = self.get_postings_list(query_dict)
     
        query_result = self.merge_postings_list_dict(postings_list_dict)
        end_time = datetime.now()
        if k > 0:
            query_result = heapq.nlargest(k, query_result, key=itemgetter(1))
        
        print("Posting's list:", query_result, "\n", len(query_result), " Search results in ", str(end_time - start_time), " for query ", query)

        return query_result

    def search_from_file(self, filename):
        '''
        Search from file 
        '''
        with open(filename) as fp:
            lines = fp.readlines()
        
        print(lines)
        
        for line in lines:
            self.search(line.split('\n')[0])
        

    def run(self):
        '''
        Run the search engine
        '''
        # print(self.tokens_dict)

        while True:
            
            query = input("\n$>")
            search_result = self.search(query)
            # print(search_result, "\n", len(search_result), "Search results")

            
if __name__ == "__main__":

    index_path = sys.argv[1]
    query_file = sys.argv[2]

    # Search engine class
    search_engine = Engine(index_path)
    # Run the search engine
    # search_engine.run()
    if os.path.exists(query_file):
        # Search from file
        search_engine.search_from_file(query_file)
    else:
        # Search from query 
        search_engine.search(query_file)